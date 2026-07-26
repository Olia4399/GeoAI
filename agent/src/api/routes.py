"""Spatial Agent API 路由"""

import asyncio
import json
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


# ---- 路由 ----

@router.get("/health")
def health_check():
    return {"status": "ok", "service": "geoai-agent", "version": "0.1.0"}


@router.post("/query", response_model=AgentQueryResponse)
async def agent_query(req: AgentQueryRequest):
    """Spatial Agent 核心接口: 自然语言 → 分析结果 + 报告 + 自动保存"""
    try:
        parser = IntentParser()
        intent = await parser.parse(req.query)

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
            )

        planner = SpatialPlanner()
        steps, results = await planner.execute(intent, req.context)

        interpreter = ResultInterpreter()
        report = await interpreter.generate(intent, steps, results)

        # 自动保存到历史
        saved_id = None
        try:
            saved_id = save_analysis(req.query, intent, steps, results, report)
        except Exception:
            pass

        return AgentQueryResponse(
            intent=intent, steps=steps, results=results, report=report, saved_id=saved_id,
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")


@router.post("/query/stream")
async def agent_query_stream(req: AgentQueryRequest):
    """SSE 流式接口: 实时推送分析各阶段结果"""
    async def event_stream():
        try:
            # 1. 意图解析
            yield f"data: {json.dumps({'type':'phase','phase':'intent','status':'running'}, ensure_ascii=False)}\n\n"
            parser = IntentParser()
            intent = await parser.parse(req.query)
            yield f"data: {json.dumps({'type':'phase','phase':'intent','status':'done','data':intent}, ensure_ascii=False)}\n\n"

            # 2. 规划 + 执行
            yield f"data: {json.dumps({'type':'phase','phase':'planning','status':'running'}, ensure_ascii=False)}\n\n"
            planner = SpatialPlanner()
            steps, results = await planner.execute(intent, req.context)
            for i, s in enumerate(steps):
                yield f"data: {json.dumps({'type':'step','index':i+1,'total':len(steps),'data':s}, ensure_ascii=False)}\n\n"

            # 3. 报告
            yield f"data: {json.dumps({'type':'phase','phase':'report','status':'running'}, ensure_ascii=False)}\n\n"
            interpreter = ResultInterpreter()
            report = await interpreter.generate(intent, steps, results)

            # 4. 保存
            saved_id = None
            try:
                saved_id = save_analysis(req.query, intent, steps, results, report)
            except Exception:
                pass

            yield f"data: {json.dumps({'type':'done','intent':intent,'results_count':len(results),'report':report,'saved_id':saved_id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'type':'error','detail':str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
