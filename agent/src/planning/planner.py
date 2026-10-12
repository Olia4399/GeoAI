"""任务规划模块

使用 LangGraph ReAct Agent 执行空间任务规划与工具调用。
支持逐步流式产出（心流），并为每一步记录 time.time()-start 耗时。
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import AsyncIterator
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from ..llm_config import get_llm_config
from ..tools.registry import tool_registry
from ..tools.spatial_tools import (  # noqa: F401 — 触发 Tool 注册
    register_spatial_tools,
)


def _msg_type(msg: Any) -> str:
    return type(msg).__name__


def _parse_messages(messages: list[Any]) -> tuple[list[dict], list[dict]]:
    """从一段 messages 增量中解析出 steps / results。

    tool_call 步骤携带 tool_call_id；工具返回解析为同 id 的 tool_result 记录，
    由 execute_stream 合并回对应调用步骤——每一步工具对外只展示一条（"调用"即该步）。
    """
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
                        "tool_call_id": tc.get("id"),
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

            feature_count = 0
            if isinstance(result_data, dict):
                feats = result_data.get("features")
                if isinstance(feats, list):
                    feature_count = len(feats)
            # 失败判定：LangGraph 工具异常（status=error）或工具自返回结构化 error（如 geocode_failed）
            failed = getattr(msg, "status", None) == "error" or (
                isinstance(result_data, dict) and bool(result_data.get("error"))
            )
            steps.append({
                "kind": "tool_result",
                "tool": tool_name,
                "tool_call_id": getattr(msg, "tool_call_id", None),
                "failed": failed,
                "feature_count": feature_count,
            })

    return steps, results


def _merge_tool_result(
    steps: list[dict],
    pending: dict[str, int],
    call_times: dict[int, float],
    result: dict,
    now: float,
    t0: float,
    node_name: str,
) -> tuple[int, dict] | None:
    """把工具返回合并进对应的调用步骤（原地更新），返回 (下标, 步骤)。

    匹配优先用 tool_call_id，兜底按工具名找最近未完成的调用；找不到时返回 None
    （调用方退化为独立步骤，保证信息不丢）。
    """
    tcid = result.get("tool_call_id")
    idx = pending.pop(tcid, None) if tcid else None
    if idx is None:
        for i in range(len(steps) - 1, -1, -1):
            s = steps[i]
            if (
                s.get("kind") == "tool_call"
                and s.get("tool") == result.get("tool")
                and not s.get("completed")
            ):
                idx = i
                break
    if idx is None:
        return None

    target = steps[idx]
    target["completed"] = True
    target["failed"] = bool(result.get("failed"))
    if result.get("feature_count"):
        target["feature_count"] = result["feature_count"]
    # 该步时长 = 从调用发出到计算完毕（用户视角的"这一步花了多久"）
    target["step_elapsed_s"] = round(now - call_times.pop(idx, now), 3)
    target["elapsed_s"] = round(now - t0, 3)
    target["node"] = node_name
    return idx, target


class SpatialPlanner:
    """LangGraph ReAct Agent — 空间任务规划器"""

    SYSTEM_PROMPT = """你是空间分析 Agent。用最少的工具调用回答用户问题。

可用工具:
- nearby_query: 查某点半径(N米)内有哪些设施 ——「附近/周边/N米内」类问题首选
- spatial_query: 查数据库 (buildings/poi/roads)，支持 bbox 和 category 过滤
- buffer_analysis: 计算缓冲区
- distance_analysis: 计算距离
- density_analysis: 核密度热力图
- suitability_analysis: 多因子加权评分
- route_analysis: 路径规划
- overlay_analysis: 空间叠加

高效工作原则:
- 「X米内/周边/附近有哪些Y」→ 直接 nearby_query(center=地名或坐标, radius=X, category=Y) 一步完成；半径必须严格使用 intent.radius_m 中的数值（用户明确要求的，禁止放大或猜测），intent.radius_m 为 null 时才默认 500；category 用 intent.category（已归一化的英文枚举），为 null 时再从用户措辞判断
- 路径类问题（"从A到B怎么走/多远"）→ route_analysis（起终点可直接传地名，自动地理编码）；mode 严格取 intent.mode（walk/drive），intent.mode 为 null 时默认 walk
- 行政区域范围查询（"朝阳区有哪些X/有多少X"）→ spatial_query 或 nearby_query 传 district="朝阳区" 按真实区界精确过滤，禁止心算 bbox 近似区界
- 地名优先让工具解析（nearby_query / distance_analysis 可直接传地名，自动地理编码）；只有工具返回 geocode_failed（未收录）时，才用你的知识估算坐标，并在最终结论中注明"坐标来自模型估算"
- 北京地标兜底参考: 国贸=[116.458,39.908], 三里屯=[116.454,39.932], 望京=[116.480,39.998]
- 先用 spatial_query 了解区域有什么，再做针对性分析
- 选址类问题走: spatial_query → density_analysis → suitability_analysis，最多 3-4 步
- 简单问题 1 步搞定，不要过度分析
- distance_analysis 只回答「两地之间距离是多少」，禁止用它逐个枚举设施来筛选范围
- 设施清单必须来自工具查询结果，禁止凭记忆列举 POI 或为 POI 编造坐标
- spatial_query 的 category 参数可直接过滤（英文值）

输出格式要求:
- 不要在句子中间用反引号包裹普通文本（如店名、坐标、地名）。反引号仅用于代码片段
- 强调用**粗体**，引用店名用"中文引号"
- 坐标用括号表示，如 (116.458, 39.908)，不要加反引号"""

    def __init__(self):
        # timeout=120s + 1 次自动重试：避免默认 600s 超时导致请求长时间挂起
        self.llm = ChatOpenAI(
            **get_llm_config("plan"),
            temperature=0,
            timeout=120,
            max_retries=1,
        )

        # 构建 LangChain Tool 列表
        self.tools = [t.to_langchain_tool() for t in tool_registry.list_all()]

        # 创建 ReAct Agent
        # prompt=SYSTEM_PROMPT：① 修复此前未传入 agent、提示词未生效的问题（效率约束/输出格式）
        # ② system prompt 作为请求的稳定前缀（字节稳定、无动态内容），命中供应商前缀缓存
        if self.tools:
            self.agent = create_react_agent(self.llm, self.tools, prompt=self.SYSTEM_PROMPT)
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
        # 待合并的工具调用：tool_call_id → steps 下标；call_times：下标 → 调用发出时刻
        pending_calls: dict[str, int] = {}
        call_times: dict[int, float] = {}

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
                    if s.get("kind") == "tool_result":
                        # 工具返回：合并进对应调用步骤（原地更新），不再单列"返回"步骤
                        merged = _merge_tool_result(
                            steps, pending_calls, call_times, s, now, t0, node_name
                        )
                        if merged is not None:
                            idx, target = merged
                            print(
                                f"[planner] step#{idx + 1} update tool={target.get('tool')} "
                                f"failed={target.get('failed')} span={target.get('step_elapsed_s')}s"
                            )
                            yield {
                                "event": "step_update",
                                "index": idx + 1,
                                "step": target,
                                "elapsed_s": target["elapsed_s"],
                            }
                            step_mark = now
                            continue

                    # 普通步骤（工具调用 / 推理文本）；合并失败时"返回"退化为独立步骤
                    if s.get("kind") == "tool_result":
                        s["action"] = "tool_result"
                        s["content"] = (
                            f"{s.get('tool', 'tool')} 返回"
                            + (f" · {s['feature_count']} 要素" if s.get("feature_count") else "")
                        )
                    step_elapsed = round(now - step_mark, 3)
                    total_elapsed = round(now - t0, 3)
                    s["elapsed_s"] = total_elapsed
                    s["step_elapsed_s"] = step_elapsed
                    s["node"] = node_name
                    steps.append(s)
                    if s.get("kind") == "tool_call" and s.get("tool_call_id"):
                        pending_calls[s["tool_call_id"]] = len(steps) - 1
                        call_times[len(steps) - 1] = now
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
