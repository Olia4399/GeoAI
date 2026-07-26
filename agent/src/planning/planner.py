"""任务规划模块

使用 LangGraph ReAct Agent 执行空间任务规划与工具调用。
"""

import json
import os
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from ..tools.registry import tool_registry
from ..tools.spatial_tools import (  # noqa: F401 — 触发 Tool 注册
    register_spatial_tools,
)


class SpatialPlanner:
    """LangGraph ReAct Agent — 空间任务规划器"""

    SYSTEM_PROMPT = """你是一个空间分析智能 Agent，负责规划和执行 GIS 空间分析任务。

你的能力:
1. 理解用户的自然语言空间需求
2. 将需求拆解为可执行的 GIS 分析步骤
3. 调用空间分析工具 (buffer_analysis, distance_analysis 等) 完成计算
4. 汇总分析结果

可用的工具:
- buffer_analysis: 计算空间对象指定距离的缓冲区范围
- distance_analysis: 计算两个空间对象之间的距离

工作原则:
- 根据用户需求制定分析计划，然后逐步调用工具执行
- 每个步骤记录你做了什么、为什么这么做
- 如果用户的 query 涉及缓冲区分析，先提取或构造 geometry，再调用 buffer_analysis
- 如果用户没有明确给出坐标，使用合理的默认值 (例如: 北京国贸 ≈ [116.458, 39.908])
- 所有分析步骤完成后，汇总结果
"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            temperature=0,
        )

        # 构建 LangChain Tool 列表
        self.tools = [t.to_langchain_tool() for t in tool_registry.list_all()]

        # 创建 ReAct Agent
        if self.tools:
            self.agent = create_react_agent(self.llm, self.tools)
        else:
            self.agent = None

    async def execute(
        self, intent: dict, context: dict | None = None
    ) -> tuple[list[dict], list[dict]]:
        """
        执行空间分析任务。

        Args:
            intent: IntentParser 解析出的结构化意图
            context: 地图上下文 (bounds, selected_geometry)

        Returns:
            (steps, results): 执行步骤列表和结果列表
        """
        steps = []
        results = []

        # 构建 Agent 输入
        user_message = f"""
用户空间需求: {json.dumps(intent, ensure_ascii=False, indent=2)}

地图上下文: {json.dumps(context, ensure_ascii=False) if context else '无'}

请根据以上信息，规划并执行空间分析任务。使用可用的 GIS 工具完成计算。
"""

        if self.agent:
            # 调用 LangGraph ReAct Agent
            agent_input = {"messages": [("user", user_message)]}
            agent_result = await self.agent.ainvoke(agent_input)

            # 解析 Agent 消息历史，提取步骤和结果
            for msg in agent_result.get("messages", []):
                msg_type = type(msg).__name__

                if msg_type == "AIMessage":
                    # Tool 调用请求
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            steps.append({
                                "tool": tc.get("name", "unknown"),
                                "arguments": tc.get("args", {}),
                            })
                    # 纯文本回复
                    elif msg.content:
                        steps.append({
                            "action": "reasoning",
                            "content": str(msg.content)[:500],
                        })

                elif msg_type == "ToolMessage":
                    try:
                        result_data = json.loads(str(msg.content))
                    except (json.JSONDecodeError, TypeError):
                        result_data = {"raw": str(msg.content)[:500]}
                    results.append(result_data)

        else:
            # 无工具可用时的退化处理
            steps.append({
                "action": "info",
                "content": f"意图已解析: {intent.get('task_type')}, 位置: {intent.get('location')}. 当前无可用 GIS Tool，请在 spatial 服务就绪后重试。",
            })

        return steps, results
