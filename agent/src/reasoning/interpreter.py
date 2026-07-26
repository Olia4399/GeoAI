"""结果解释模块

使用 LLM 将结构化空间分析结果转换为自然语言决策报告。
"""

import json
import os

from langchain_openai import ChatOpenAI


INTERPRETER_SYSTEM_PROMPT = """你是一位城市空间分析专家。根据空间分析的计算结果，生成清晰、有洞察力的自然语言报告。

报告要求:
1. 用简洁的语言概括分析目的和结论
2. 解释关键数据指标的含义
3. 如有必要，给出决策建议或风险提示
4. 使用中文输出
5. 保持专业但易懂的语气
"""


class ResultInterpreter:
    """LLM 结果解释器"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            temperature=0.3,  # 略微提高以增强报告多样性
        )

    async def generate(
        self,
        intent: dict,
        steps: list[dict],
        results: list[dict],
    ) -> str:
        """生成分析报告"""
        user_prompt = f"""
分析任务: {json.dumps(intent, ensure_ascii=False, indent=2)}

执行步骤:
{json.dumps(steps, ensure_ascii=False, indent=2)}

计算结果:
{json.dumps(results, ensure_ascii=False, indent=2)}

请基于以上信息生成一份简洁的空间分析报告。
"""

        if not results:
            return (
                f"## 空间分析报告\n\n"
                f"**分析任务**: {intent.get('task_type', '未知')}\n\n"
                f"**目标区域**: {intent.get('location', '未指定')}\n\n"
                f"当前暂无足够数据生成详细报告。请确保 spatial 服务和数据库已正确连接后重试。"
            )

        messages = [
            ("system", INTERPRETER_SYSTEM_PROMPT),
            ("user", user_prompt),
        ]
        response = await self.llm.ainvoke(messages)
        return str(response.content)
