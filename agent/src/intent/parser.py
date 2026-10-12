"""意图解析模块

使用 LLM + JSON 输出将自然语言转换为结构化空间任务。
支持 response_format 的厂商（智谱等）可通过 LLM_INTENT_JSON_MODE 开启 JSON 模式，
失败自动回退 JSON prompt + 手动解析（DeepSeek 不支持 response_format）。
"""

import json
import os
import re
import time

from langchain_core.messages import SystemMessage, HumanMessage

from ..llm_config import build_llm_pair


INTENT_SYSTEM_PROMPT = """你是一个空间分析意图解析器。根据用户的自然语言输入，将需求转换为 JSON 格式。

## 输出格式 (严格 JSON，不要包含 markdown 代码块)

{
  "task_type": "unsupported|buffer_analysis|distance_analysis|route_analysis|site_selection|suitability_evaluation|spatial_query",
  "location": "分析区域/地点的纯名称（如 '国贸'、'三里屯'），不要包含半径等修饰词",
  "radius_m": 500 或 null,
  "category": "bank|restaurant|cafe|hospital|school|pharmacy|subway|marketplace|retail|null",
  "mode": "walk|drive|null",
  "industry": "行业类型 (选址任务时填写，否则为 null)",
  "criteria": ["分析指标列表"],
  "geometry_needed": true
}

## 任务类型

- unsupported: 非空间分析问题（如"GDP最高是哪个区"、"今天天气怎么样"等统计/常识/天气问题）。本平台只能做空间分析（选址、缓冲区、距离、密度、路径规划），不能回答统计数据查询。
- buffer_analysis: 缓冲区分析
- distance_analysis: 距离计算
- route_analysis: 路径规划与出行（"从A到B怎么走/多远/开车去"）
- site_selection: 选址分析
- suitability_evaluation: 适宜性评价
- spatial_query: 查询空间数据库（POI/建筑/道路）

## 重要判断规则

- 半径提取（radius_m）：用户明确给出范围数字时必须提取并换算成米——"500米内"→500、"2公里/2km内"→2000、"1.5千米内"→1500；只说"附近/周边/周围"没有具体数字时为 null
- 类别实体词（category）：用户要找的设施类别，必须从枚举中选英文值——银行/银行网点→bank、餐厅/饭馆/火锅→restaurant、咖啡店/咖啡馆→cafe、医院→hospital、学校/大学→school、药店→pharmacy、地铁站→subway、商场/购物中心→marketplace、超市/商店→retail；未提及类别、或用户说的是品牌/专名（如"星巴克"、"肯德基"是找具体品牌店，不归并到类别）时为 null
- 出行方式（mode）：步行/走路→"walk"，开车/驾车/自驾→"drive"；其他（骑行/公交等平台不支持）或未提及→null
- 路径/出行类问题（"从A到B怎么走/多远/开车去"）task_type 必须设为 route_analysis，不能设为 unsupported
- location 只保留地名本身："国贸周边500米内" → location="国贸"、radius_m=500
- 如果用户问的是统计数据（GDP、人口数量排名、经济指标等）、非空间常识问题、或本平台无法回答的问题，task_type 必须设为 "unsupported"
- 只有当用户明确涉及地理空间计算时（选址、距离、可达性、密度、缓冲区），才标记为空间分析任务
- 只输出 JSON，不要任何解释文字"""


class IntentParser:
    """LLM 意图解析器 (JSON 模式)"""

    def __init__(self):
        # timeout=60s（意图解析是小任务，超时尽快触发降级）+ 1 次自动重试
        # 主模型 = 阶段配置（智谱免费档）；备胎 = 全局配置（DeepSeek），过载/限流/超时自动降级
        self._primary, self._fallback = build_llm_pair(
            "intent", temperature=0, timeout=60, max_retries=1
        )
        # 支持 response_format 的厂商（智谱等）可开 JSON 模式提高结构化输出稳定性；
        # 不支持时会自动回退（见 parse）。切回 DeepSeek 时请把 LLM_INTENT_JSON_MODE 置空
        self._json_mode = os.getenv("LLM_INTENT_JSON_MODE", "").strip().lower() in ("1", "true", "yes")
        self._bind_llm()

    def _bind_llm(self) -> None:
        """按当前 json_mode 重建调用链（response_format 只绑主模型，不传给备胎）"""
        primary = (
            self._primary.bind(response_format={"type": "json_object"})
            if self._json_mode
            else self._primary
        )
        self.llm = primary.with_fallbacks([self._fallback]) if self._fallback else primary

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
        try:
            response = await self.llm.ainvoke(messages)
        except Exception as e:
            if not self._json_mode:
                raise
            # 供应商不支持 response_format 时（如切回 DeepSeek）自动回退普通模式重试一次
            print(f"[parser] JSON 模式失败，回退普通模式: {e}")
            self._json_mode = False
            self._bind_llm()
            response = await self.llm.ainvoke(messages)
        raw = str(response.content).strip()
        print(f"[parser] LLM raw output ({round(time.time()-t0, 3)}s): {raw[:200]}")

        result = self._extract_json(raw)

        # 确保必需字段
        result.setdefault("task_type", "buffer_analysis")
        result.setdefault("location", "未知区域")
        result.setdefault("radius_m", None)
        result.setdefault("category", None)
        result.setdefault("mode", None)
        result.setdefault("industry", None)
        result.setdefault("criteria", [])
        result.setdefault("geometry_needed", True)

        print(f"[parser] parse done total={round(time.time()-t0, 3)}s task={result.get('task_type')}")
        return result
