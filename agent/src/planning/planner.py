"""任务规划模块

使用 LangGraph ReAct Agent 执行空间任务规划与工具调用。
支持逐步流式产出（心流），并为每一步记录 time.time()-start 耗时。
"""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import AsyncIterator
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from ..tools.registry import tool_registry
from ..tools.spatial_tools import (  # noqa: F401 — 触发 Tool 注册
    register_spatial_tools,
)


def _msg_type(msg: Any) -> str:
    return type(msg).__name__


def _parse_messages(messages: list[Any]) -> tuple[list[dict], list[dict]]:
    """从一段 messages 增量中解析出 steps / results。"""
    steps: list[dict] = []
    results: list[dict] = []

    for msg in messages:
        msg_type = _msg_type(msg)

        if msg_type == "AIMessage":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    steps.append({
                        "tool": tc.get("name", "unknown"),
                        "arguments": tc.get("args", {}),
                        "kind": "tool_call",
                    })
            elif msg.content:
                content = str(msg.content)
                # 最终总结与报告正文之间以 --- 分隔：报告 Markdown 不进入步骤内容，
                # 只保留分隔线前的总结（如“分析完成。以下是…报告。”）
                content = re.split(r"\n\s*[-*]{3,}", content)[0].strip()
                steps.append({
                    "action": "reasoning",
                    "content": content[:500],
                    "kind": "reasoning",
                })

        elif msg_type == "ToolMessage":
            tool_name = getattr(msg, "name", None) or "tool"
            try:
                result_data = json.loads(str(msg.content))
            except (json.JSONDecodeError, TypeError):
                result_data = {"raw": str(msg.content)[:500]}
            results.append(result_data)
            # 工具返回也作为一步，便于前端心流展示与耗时排查
            feature_count = 0
            if isinstance(result_data, dict):
                feats = result_data.get("features")
                if isinstance(feats, list):
                    feature_count = len(feats)
            steps.append({
                "action": "tool_result",
                "tool": tool_name,
                "kind": "tool_result",
                "content": f"{tool_name} 返回" + (f" · {feature_count} 要素" if feature_count else ""),
                "feature_count": feature_count,
            })

    return steps, results


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
- spatial_query 的 category 参数可直接过滤

输出格式要求:
- 不要在句子中间用反引号包裹普通文本（如店名、坐标、地名）。反引号仅用于代码片段
- 强调用**粗体**，引用店名用"中文引号"
- 坐标用括号表示，如 (116.458, 39.908)，不要加反引号"""

    def __init__(self):
        # timeout=120s + 1 次自动重试：避免默认 600s 超时导致请求长时间挂起
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            temperature=0,
            timeout=120,
            max_retries=1,
        )

        # 构建 LangChain Tool 列表
        self.tools = [t.to_langchain_tool() for t in tool_registry.list_all()]

        # 创建 ReAct Agent
        if self.tools:
            self.agent = create_react_agent(self.llm, self.tools)
        else:
            self.agent = None

    def _build_user_message(self, intent: dict, context: dict | None) -> str:
        return f"""
用户空间需求: {json.dumps(intent, ensure_ascii=False, indent=2)}

地图上下文: {json.dumps(context, ensure_ascii=False) if context else '无'}

请根据以上信息，规划并执行空间分析任务。使用可用的 GIS 工具完成计算。
"""

    async def execute_stream(
        self, intent: dict, context: dict | None = None
    ) -> AsyncIterator[dict]:
        """
        逐步流式执行，每产出一步立即 yield。

        yield 事件:
          {"event": "step", "step": {...}, "index": N, "elapsed_s": float}
          {"event": "complete", "steps": [...], "results": [...], "elapsed_s": float}
        """
        t0 = time.time()
        steps: list[dict] = []
        results: list[dict] = []
        user_message = self._build_user_message(intent, context)

        if not self.agent:
            step = {
                "action": "info",
                "kind": "info",
                "content": (
                    f"意图已解析: {intent.get('task_type')}, 位置: {intent.get('location')}. "
                    "当前无可用 GIS Tool，请在 spatial 服务就绪后重试。"
                ),
                "elapsed_s": round(time.time() - t0, 3),
                "step_elapsed_s": round(time.time() - t0, 3),
            }
            steps.append(step)
            yield {"event": "step", "step": step, "index": 1, "elapsed_s": step["elapsed_s"]}
            yield {
                "event": "complete",
                "steps": steps,
                "results": results,
                "elapsed_s": round(time.time() - t0, 3),
            }
            return

        agent_input = {"messages": [("user", user_message)]}
        step_mark = t0
        seen_msg_ids: set[str] = set()

        print(f"[planner] execute_stream start @ {t0:.3f}")

        # stream_mode=updates：每个节点完成后推送增量，避免整段 ainvoke 阻塞
        async for chunk in self.agent.astream(agent_input, stream_mode="updates"):
            for node_name, update in chunk.items():
                messages = update.get("messages") if isinstance(update, dict) else None
                if not messages:
                    continue

                # 只处理本轮新增消息，避免 values 模式下重复
                new_msgs = []
                for msg in messages:
                    mid = getattr(msg, "id", None) or id(msg)
                    key = str(mid)
                    if key in seen_msg_ids:
                        continue
                    seen_msg_ids.add(key)
                    new_msgs.append(msg)

                if not new_msgs:
                    continue

                new_steps, new_results = _parse_messages(new_msgs)
                results.extend(new_results)

                now = time.time()
                for s in new_steps:
                    step_elapsed = round(now - step_mark, 3)
                    total_elapsed = round(now - t0, 3)
                    s["elapsed_s"] = total_elapsed
                    s["step_elapsed_s"] = step_elapsed
                    s["node"] = node_name
                    steps.append(s)
                    print(
                        f"[planner] step#{len(steps)} node={node_name} "
                        f"kind={s.get('kind')} tool={s.get('tool')} "
                        f"step={step_elapsed}s total={total_elapsed}s"
                    )
                    yield {
                        "event": "step",
                        "step": s,
                        "index": len(steps),
                        "elapsed_s": total_elapsed,
                    }
                    step_mark = now

        total = round(time.time() - t0, 3)
        print(f"[planner] execute_stream done steps={len(steps)} results={len(results)} total={total}s")
        yield {
            "event": "complete",
            "steps": steps,
            "results": results,
            "elapsed_s": total,
        }

    async def execute(
        self, intent: dict, context: dict | None = None
    ) -> tuple[list[dict], list[dict]]:
        """
        执行空间分析任务（非流式，内部复用 execute_stream）。

        Returns:
            (steps, results): 执行步骤列表和结果列表
        """
        steps: list[dict] = []
        results: list[dict] = []
        async for ev in self.execute_stream(intent, context):
            if ev.get("event") == "complete":
                steps = ev.get("steps") or []
                results = ev.get("results") or []
        return steps, results
