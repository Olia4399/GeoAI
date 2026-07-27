"""意图解析模块

使用 LLM + JSON 输出将自然语言转换为结构化空间任务。
(DeepSeek 不支持 response_format，改用 JSON prompt + 手动解析)
"""

import json
import os
import re
import time

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


INTENT_SYSTEM_PROMPT = """你是一个空间分析意图解析器。根据用户的自然语言输入，将需求转换为 JSON 格式。

## 输出格式 (严格 JSON，不要包含 markdown 代码块)

{
  "task_type": "unsupported|buffer_analysis|distance_analysis|site_selection|suitability_evaluation|spatial_query",
  "location": "分析区域描述",
  "industry": "行业类型 (选址任务时填写，否则为 null)",
  "criteria": ["分析指标列表"],
  "geometry_needed": true
}

## 任务类型

- unsupported: 非空间分析问题（如"GDP最高是哪个区"、"今天天气怎么样"等统计/常识/天气问题）。本平台只能做空间分析（选址、缓冲区、距离、密度、路径规划），不能回答统计数据查询。
- buffer_analysis: 缓冲区分析
- distance_analysis: 距离计算
- site_selection: 选址分析
- suitability_evaluation: 适宜性评价
- spatial_query: 查询空间数据库（POI/建筑/道路）

## 重要判断规则

- 如果用户问的是统计数据（GDP、人口数量排名、经济指标等）、非空间常识问题、或本平台无法回答的问题，task_type 必须设为 "unsupported"
- 只有当用户明确涉及地理空间计算时（选址、距离、可达性、密度、缓冲区），才标记为空间分析任务
- 只输出 JSON，不要任何解释文字"""


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
        t0 = time.time()
        messages = [
            SystemMessage(content=INTENT_SYSTEM_PROMPT),
            HumanMessage(content=query),
        ]
        response = await self.llm.ainvoke(messages)
        raw = str(response.content).strip()
        print(f"[parser] LLM raw output ({round(time.time()-t0, 3)}s): {raw[:200]}")

        result = self._extract_json(raw)

        # 确保必需字段
        result.setdefault("task_type", "buffer_analysis")
        result.setdefault("location", "未知区域")
        result.setdefault("industry", None)
        result.setdefault("criteria", [])
        result.setdefault("geometry_needed", True)

        print(f"[parser] parse done total={round(time.time()-t0, 3)}s task={result.get('task_type')}")
        return result
