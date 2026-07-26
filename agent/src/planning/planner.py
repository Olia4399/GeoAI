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

    SYSTEM_PROMPT = """你是空间分析 Agent。用最少的工具调用回答用户问题。

可用工具:
- spatial_query: 查数据库 (buildings/poi/roads)，支持 bbox 和 category 过滤
- buffer_analysis: 计算缓冲区
- distance_analysis: 计算距离
- density_analysis: 核密度热力图
- suitability_analysis: 多因子加权评分
- route_analysis: 路径规划
- overlay_analysis: 空间叠加

高效工作原则:
- 先用 spatial_query 了解区域有什么，再做针对性分析
- 选址类问题走: spatial_query → density_analysis → suitability_analysis，最多 3-4 步
- 简单问题 1 步搞定，不要过度分析
- 地名无法查找坐标时，直接用你的知识估算坐标 (北京地名坐标你大多知道)
- distance_analysis 的 source/target 参数可以是地名或坐标字符串
- spatial_query 的 category 参数可直接过滤"""

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
