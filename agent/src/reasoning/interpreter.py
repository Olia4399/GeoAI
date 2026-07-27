"""结果解释模块 — RAG 增强版

使用 LLM + 空间知识库将结构化空间分析结果转换为自然语言决策报告。
"""

import json
import os
import time

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..knowledge.vector_store import kb as knowledge_base

INTERPRETER_SYSTEM_PROMPT = """你是城市空间分析专家，根据空间分析的计算结果生成决策报告。

报告要求:
1. 用简洁的语言概括分析目的和结论
2. 解释关键数据指标的含义
3. 如果提供了知识库参考，必须在报告中引用（标注来源）
4. 给出明确、可操作的决策建议
5. 使用中文输出，使用 Markdown 格式（表格、列表、粗体）
6. 坐标用括号表示如(116.458, 39.908)，店名用中文引号，不要用反引号包裹普通文字
7. 反引号仅用于真正的代码或命令，不能用于店名、地名、坐标

报告结构:
## 分析概述
## 核心发现
## 决策建议
## 风险提示 (如有)"""


class ResultInterpreter:
    """LLM 结果解释器 (RAG 增强)"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            temperature=0.3,
        )

    @staticmethod
    def _build_knowledge_context(intent: dict) -> str:
        """检索相关知识，构建上下文"""
        industry = intent.get("industry", "")
        task = intent.get("task_type", "")
        location = intent.get("location", "")

        queries = []
        if industry:
            queries.append(f"{industry} 选址标准")
        queries.append("选址 分析方法 权重")
        queries.append("商业设施 服务半径")

        seen = set()
        context_parts = []

        for q in queries[:3]:  # 最多 3 个查询
            try:
                items = knowledge_base.search(q, top_k=3)
                for item in items:
                    content = item.get("content", "")
                    if content and content[:40] not in seen:
                        seen.add(content[:40])
                        context_parts.append(content)
            except Exception:
                pass

        if context_parts:
            return "## 参考知识库\n\n" + "\n\n---\n".join(context_parts)
        return ""

    async def generate(
        self,
        intent: dict,
        steps: list[dict],
        results: list[dict],
    ) -> str:
        """生成分析报告 (集成 RAG 知识检索)；打印分阶段耗时便于排查"""
        t0 = time.time()
        kb_context = self._build_knowledge_context(intent)
        rag_s = round(time.time() - t0, 3)
        print(f"[interpreter] RAG 检索耗时 {rag_s}s")

        user_prompt = f"""
分析任务: {json.dumps(intent, ensure_ascii=False, indent=2)}

执行步骤:
{json.dumps(steps, ensure_ascii=False, indent=2)}

计算结果:
{json.dumps(results, ensure_ascii=False, indent=2)}

{ kb_context }

请基于以上信息生成一份简洁的空间分析报告。{ "如果提供了参考知识库，请在报告中引用相关知识来源。" if kb_context else ""}
"""

        if not results:
            return (
                f"## 空间分析报告\n\n"
                f"**分析任务**: {intent.get('task_type', '未知')}\n\n"
                f"**目标区域**: {intent.get('location', '未指定')}\n\n"
                f"当前暂无足够数据生成详细报告。"
            )

        messages = [
            SystemMessage(content=INTERPRETER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        t_llm = time.time()
        response = await self.llm.ainvoke(messages)
        llm_s = round(time.time() - t_llm, 3)
        print(f"[interpreter] LLM 报告生成耗时 {llm_s}s · 合计 {round(time.time() - t0, 3)}s")
        return str(response.content)
