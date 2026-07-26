"""Spatial Agent API 路由"""

import os
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..intent.parser import IntentParser
from ..planning.planner import SpatialPlanner
from ..reasoning.interpreter import ResultInterpreter

router = APIRouter()


# ---- 请求/响应模型 ----

class AgentQueryRequest(BaseModel):
    query: str = Field(description="用户自然语言空间问题", min_length=1)
    context: dict | None = Field(
        default=None,
        description="地图上下文 (bounds, selected_geometry 等)",
    )


class AgentQueryResponse(BaseModel):
    intent: dict
    steps: list[dict]
    results: list[dict]
    report: str


# ---- 路由 ----

@router.get("/health")
def health_check():
    return {"status": "ok", "service": "geoai-agent", "version": "0.1.0"}


@router.post("/query", response_model=AgentQueryResponse)
async def agent_query(req: AgentQueryRequest):
    """
    Spatial Agent 核心接口: 接收自然语言空间问题，返回分析结果和报告。

    流程: 意图解析 → 任务规划 → 工具调用 → 结果解释
    """
    try:
        # 1. 意图解析: 自然语言 → 结构化空间任务
        parser = IntentParser()
        intent = await parser.parse(req.query)

        # 2. 任务规划 + 执行: ReAct Agent 调用 GIS Tools
        planner = SpatialPlanner()
        steps, results = await planner.execute(intent, req.context)

        # 3. 结果解释: 结构化结果 → 自然语言报告
        interpreter = ResultInterpreter()
        report = await interpreter.generate(intent, steps, results)

        return AgentQueryResponse(
            intent=intent,
            steps=steps,
            results=results,
            report=report,
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")
