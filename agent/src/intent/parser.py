"""意图解析模块

使用 LLM + JSON 输出将自然语言转换为结构化空间任务。
(DeepSeek 不支持 response_format，改用 JSON prompt + 手动解析)
"""

import json
import os
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


INTENT_SYSTEM_PROMPT = """你是一个空间分析意图解析器。根据用户的自然语言输入，将需求转换为 JSON 格式。

## 输出格式 (严格 JSON，不要包含 markdown 代码块)

{
  "task_type": "buffer_analysis|distance_analysis|site_selection|suitability_evaluation",
  "location": "分析区域描述",
  "industry": "行业类型 (选址任务时填写，否则为 null)",
  "criteria": ["分析指标列表"],
  "geometry_needed": true
}

## 任务类型

- buffer_analysis: 缓冲区分析（计算某点/区域周边范围，如"500米缓冲区"）
- distance_analysis: 距离计算（两点/两区域距离）
- site_selection: 选址分析（在哪开店/建站，需要综合考虑多因素）
- suitability_evaluation: 适宜性评价（某区域是否适合某用途）

## 要求

- 只输出 JSON，不要任何解释文字
- criteria 字段列出相关的分析指标 (如 population_density, transport_accessibility, competitor_density)
- geometry_needed 通常为 true"""


class IntentParser:
    """LLM 意图解析器 (JSON 模式)"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            temperature=0,
        )

    @staticmethod
    def _extract_json(text: str) -> dict:
        """从 LLM 输出中提取 JSON 对象"""
        # 尝试直接解析
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 代码块
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 { ... } 最外层
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Failed to parse JSON from LLM output: {text[:300]}")

    async def parse(self, query: str) -> dict:
        """解析用户自然语言为结构化空间意图"""
        messages = [
            SystemMessage(content=INTENT_SYSTEM_PROMPT),
            HumanMessage(content=query),
        ]
        response = await self.llm.ainvoke(messages)
        raw = str(response.content).strip()
        print(f"[parser] LLM raw output: {raw[:200]}")

        result = self._extract_json(raw)

        # 确保必需字段
        result.setdefault("task_type", "buffer_analysis")
        result.setdefault("location", "未知区域")
        result.setdefault("industry", None)
        result.setdefault("criteria", [])
        result.setdefault("geometry_needed", True)

        return result
