"""意图解析模块

使用 LLM + Structured Output 将自然语言转换为结构化空间任务。
"""

import os
from typing import Optional

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class SpatialIntent(BaseModel):
    """空间意图结构化 Schema"""
    task_type: str = Field(
        description="空间任务类型: site_selection, buffer_analysis, distance_analysis, suitability_evaluation",
        examples=["site_selection"],
    )
    location: str = Field(
        description="分析区域描述",
        examples=["北京朝阳区"],
    )
    industry: Optional[str] = Field(
        default=None,
        description="行业类型 (选址任务时)",
        examples=["coffee", "charging_station", "retail"],
    )
    criteria: list[str] = Field(
        description="分析指标列表",
        examples=[["population_density", "transport_accessibility", "competitor_density"]],
    )
    geometry_needed: bool = Field(
        default=True,
        description="是否需要几何空间计算",
    )


INTENT_SYSTEM_PROMPT = """你是一个空间分析意图解析器。根据用户的自然语言输入，提取结构化的空间分析任务。

任务类型说明:
- site_selection: 选址分析（在哪里开咖啡店/超市/充电站等）
- buffer_analysis: 缓冲区分析（计算某点周边范围）
- distance_analysis: 距离计算（计算两点/两区域距离）
- suitability_evaluation: 适宜性评价（某区域是否适合某用途）

请仔细分析用户需求，返回准确的结构化意图。"""


class IntentParser:
    """LLM 意图解析器"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            temperature=0,
        )
        self.structured_llm = self.llm.with_structured_output(SpatialIntent)

    async def parse(self, query: str) -> dict:
        """解析用户自然语言为结构化空间意图"""
        messages = [
            ("system", INTENT_SYSTEM_PROMPT),
            ("user", query),
        ]
        intent: SpatialIntent = await self.structured_llm.ainvoke(messages)
        return intent.model_dump()
