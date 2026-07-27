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
        try:
            # 1. 意图解析
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
            yield _sse({
                "type": "error",
                "detail": str(e),
                "elapsed_s": round(time.time() - t0, 3),
            })

    return StreamingResponse(event_stream(), media_type="text/event-stream")
