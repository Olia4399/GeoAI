"""Spatial Agent API 路由"""

import json
import time
import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..intent.parser import IntentParser
from ..planning.planner import SpatialPlanner
from ..reasoning.interpreter import ResultInterpreter
from ..storage.history import save_analysis

router = APIRouter()


# ---- 请求/响应模型 ----

class AgentQueryRequest(BaseModel):
    query: str = Field(description="用户自然语言空间问题", min_length=1)
    context: dict | None = Field(default=None, description="地图上下文")


class AgentQueryResponse(BaseModel):
    intent: dict
    steps: list[dict]
    results: list[dict]
    report: str
    saved_id: str | None = None
    timings: dict | None = None


# ---- 路由 ----

@router.get("/health")
def health_check():
    return {"status": "ok", "service": "geoai-agent", "version": "0.1.0"}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _classify_error(exc: Exception) -> dict:
    """将异常分类为前端可识别的错误结构（error_type/title/hint），便于统一报错组件展示。"""
    name = type(exc).__name__
    msg = str(exc)
    if "Connect" in name or "connect" in msg.lower():
        return {
            "error_type": "spatial",
            "title": "空间服务连接失败",
            "hint": "确认 spatial 服务 (8002) 已启动且端口正确",
        }
    if "Authentication" in name or "401" in msg or "api key" in msg.lower() or "unauthorized" in msg.lower():
        return {
            "error_type": "llm",
            "title": "大模型认证失败",
            "hint": "检查 agent/.env 的 OPENAI_API_KEY 是否有效",
        }
    if "timeout" in msg.lower() or "Timeout" in name:
        return {
            "error_type": "timeout",
            "title": "大模型请求超时",
            "hint": "LLM 调用超过 120 秒（已自动重试 1 次）仍失败；检查网络或 LLM 服务状态，稍后重试，或更换 agent/.env 中的 LLM_MODEL",
        }
    if "RateLimit" in name or "429" in msg:
        return {
            "error_type": "llm",
            "title": "大模型限流",
            "hint": "请求过于频繁或额度不足，稍后重试",
        }
    return {
        "error_type": "sse",
        "title": "分析执行出错",
        "hint": "查看 agent 服务 (8001) 控制台日志（已打印 traceback）",
    }


@router.post("/query", response_model=AgentQueryResponse)
async def agent_query(req: AgentQueryRequest):
    """Spatial Agent 核心接口: 自然语言 → 分析结果 + 报告 + 自动保存"""
    t0 = time.time()
    timings: dict[str, float] = {}
    try:
        t = time.time()
        parser = IntentParser()
        intent = await parser.parse(req.query)
        timings["intent_s"] = round(time.time() - t, 3)

        # 非空间分析问题 → 直接返回说明
        if intent.get("task_type") == "unsupported":
            return AgentQueryResponse(
                intent=intent,
                steps=[],
                results=[],
                report=(
                    f"## ⚠️ 当前问题超出平台空间分析能力\n\n"
                    f"您的问题「{req.query}」不属于空间分析范畴。\n\n"
                    f"**本平台支持的空间分析类型：**\n"
                    f"- 🏪 **选址分析**：在哪开店/建站最合适\n"
                    f"- 🔵 **缓冲区分析**：计算服务半径和影响范围\n"
                    f"- 📏 **距离计算**：计算两点/区域间的距离\n"
                    f"- 🗺️ **空间查询**：查询区域内的POI/建筑/道路\n"
                    f"- 🔥 **密度分析**：生成竞品或人口密度热力图\n"
                    f"- 🛤️ **路径规划**：计算步行/驾车最短路径\n\n"
                    f"**示例问题：**\n"
                    f"- '朝阳区哪里适合开咖啡店？'\n"
                    f"- '国贸周边500米内有哪些餐厅？'\n"
                    f"- '从A到B的步行距离是多少？'\n"
                    f"- '分析三里屯商圈咖啡店竞争密度'"
                ),
                saved_id=None,
                timings={**timings, "total_s": round(time.time() - t0, 3)},
            )

        t = time.time()
        planner = SpatialPlanner()
        steps, results = await planner.execute(intent, req.context)
        timings["planning_s"] = round(time.time() - t, 3)

        t = time.time()
        interpreter = ResultInterpreter()
        report = await interpreter.generate(intent, steps, results)
        timings["report_s"] = round(time.time() - t, 3)

        # 自动保存到历史
        saved_id = None
        try:
            saved_id = save_analysis(req.query, intent, steps, results, report)
        except Exception:
            pass

        timings["total_s"] = round(time.time() - t0, 3)
        print(f"[query] timings={timings}")

        return AgentQueryResponse(
            intent=intent, steps=steps, results=results, report=report,
            saved_id=saved_id, timings=timings,
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")


@router.post("/query/stream")
async def agent_query_stream(req: AgentQueryRequest):
    """SSE 流式接口: 实时推送分析各阶段结果（步骤前置心流 + 逐步耗时）"""
    async def event_stream():
        t0 = time.time()
        timings: dict[str, float] = {}
        phase = "intent"
        try:
            # 1. 意图解析
            phase = "intent"
            yield _sse({
                "type": "phase", "phase": "intent", "status": "running",
                "elapsed_s": 0,
            })
            t = time.time()
            parser = IntentParser()
            intent = await parser.parse(req.query)
            timings["intent_s"] = round(time.time() - t, 3)
            yield _sse({
                "type": "phase", "phase": "intent", "status": "done",
                "data": intent,
                "elapsed_s": timings["intent_s"],
                "phase_elapsed_s": timings["intent_s"],
            })

            if intent.get("task_type") == "unsupported":
                report = (
                    f"## ⚠️ 当前问题超出平台空间分析能力\n\n"
                    f"您的问题「{req.query}」不属于空间分析范畴。"
                )
                timings["total_s"] = round(time.time() - t0, 3)
                yield _sse({
                    "type": "done",
                    "intent": intent,
                    "results": [],
                    "results_count": 0,
                    "report": report,
                    "saved_id": None,
                    "timings": timings,
                    "elapsed_s": timings["total_s"],
                })
                return

            # 2. 规划 + 执行（逐步推送，报告生成前即可看到心流）
            phase = "planning"
            yield _sse({
                "type": "phase", "phase": "planning", "status": "running",
                "elapsed_s": round(time.time() - t0, 3),
            })
            t_plan = time.time()
            planner = SpatialPlanner()
            steps: list[dict] = []
            results: list[dict] = []

            async for ev in planner.execute_stream(intent, req.context):
                if ev.get("event") == "step":
                    step = ev["step"]
                    yield _sse({
                        "type": "step",
                        "index": ev["index"],
                        "total": ev["index"],  # 流式过程中 total 尚未可知，用当前序号
                        "data": step,
                        "elapsed_s": ev.get("elapsed_s"),
                        "step_elapsed_s": step.get("step_elapsed_s"),
                    })
                elif ev.get("event") == "complete":
                    steps = ev.get("steps") or []
                    results = ev.get("results") or []
                    timings["planning_s"] = round(time.time() - t_plan, 3)

            yield _sse({
                "type": "phase", "phase": "planning", "status": "done",
                "elapsed_s": round(time.time() - t0, 3),
                "phase_elapsed_s": timings.get("planning_s"),
                "steps_count": len(steps),
                "results_count": len(results),
            })

            # 3. 报告（步骤已全部前置推完）
            phase = "report"
            yield _sse({
                "type": "phase", "phase": "report", "status": "running",
                "elapsed_s": round(time.time() - t0, 3),
            })
            t_report = time.time()
            interpreter = ResultInterpreter()
            report = await interpreter.generate(intent, steps, results)
            timings["report_s"] = round(time.time() - t_report, 3)
            yield _sse({
                "type": "phase", "phase": "report", "status": "done",
                "elapsed_s": round(time.time() - t0, 3),
                "phase_elapsed_s": timings["report_s"],
            })

            # 4. 保存
            saved_id = None
            try:
                saved_id = save_analysis(req.query, intent, steps, results, report)
            except Exception:
                pass

            timings["total_s"] = round(time.time() - t0, 3)
            print(f"[query/stream] timings={timings}")

            yield _sse({
                "type": "done",
                "intent": intent,
                "results": results,
                "results_count": len(results),
                "report": report,
                "saved_id": saved_id,
                "timings": timings,
                "elapsed_s": timings["total_s"],
                "steps": steps,
            })

        except Exception as e:
            traceback.print_exc()
            print(f"[query/stream] ERROR phase={phase} exc={type(e).__name__}: {e}")
            yield _sse({
                "type": "error",
                "detail": str(e),
                "phase": phase,
                "elapsed_s": round(time.time() - t0, 3),
                **_classify_error(e),
            })

    return StreamingResponse(event_stream(), media_type="text/event-stream")
