"""LLM 配置 — 支持按阶段配置不同模型/供应商（成本分级 + 降级兜底）

优先级：阶段专属变量（如 LLM_MODEL_INTENT） > 全局变量（LLM_MODEL）。
空字符串视作未设置自动回退，便于 docker-compose 透传空值。
"""

import os

from langchain_openai import ChatOpenAI

# 三个阶段：意图解析 / ReAct 规划 / 报告生成
STAGES = ("intent", "plan", "report")


def get_llm_config(stage: str) -> dict:
    """读取指定阶段的 LLM 配置。

    Args:
        stage: intent / plan / report

    Returns:
        {"model": ..., "api_key": ..., "base_url": ...}
    """
    key = stage.upper()
    return {
        "model": os.getenv(f"LLM_MODEL_{key}") or os.getenv("LLM_MODEL", "gpt-4o"),
        "api_key": os.getenv(f"OPENAI_API_KEY_{key}") or os.getenv("OPENAI_API_KEY", ""),
        "base_url": os.getenv(f"OPENAI_BASE_URL_{key}")
        or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    }


def _get_global_config() -> dict:
    """全局（默认）LLM 配置，同时作为阶段模型的降级备胎"""
    return {
        "model": os.getenv("LLM_MODEL", "gpt-4o"),
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    }


def build_llm_pair(stage: str, **kwargs) -> tuple:
    """构建（主模型, 降级备胎）二元组。

    主模型用阶段配置（如智谱免费档）；当阶段配置与全局不同且全局 Key 存在时，
    返回全局配置作为降级备胎——免费模型过载(1305)/限流(1302)/超时/认证失败时
    自动切换，保证可用性。

    调用方用 primary.with_fallbacks([fallback]) 组装；若需 bind 参数
    （如 response_format），先 bind 主模型再包备胎，避免参数误传给备胎。
    """
    primary_cfg = get_llm_config(stage)
    fallback_cfg = _get_global_config()
    primary = ChatOpenAI(**primary_cfg, **kwargs)
    if fallback_cfg["api_key"] and fallback_cfg != primary_cfg:
        return primary, ChatOpenAI(**fallback_cfg, **kwargs)
    return primary, None
