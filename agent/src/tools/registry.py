"""Tool 注册中心 — MCP 风格 Tool 管理

注册、查找、调用 GIS 工具。
"""

from typing import Any, Callable

from pydantic import BaseModel


class Tool:
    """单个 Tool 定义"""

    def __init__(
        self,
        name: str,
        description: str,
        args_schema: type[BaseModel],
        handler: Callable,
    ):
        self.name = name
        self.description = description
        self.args_schema = args_schema  # Pydantic model for argument validation
        self.handler = handler  # async callable

    def to_openai_function(self) -> dict:
        """转为 OpenAI Function Calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": _pydantic_to_json_schema(self.args_schema),
            },
        }

    def to_langchain_tool(self):
        """转为 LangChain StructuredTool"""
        from langchain_core.tools import StructuredTool

        return StructuredTool(
            name=self.name,
            description=self.description,
            args_schema=self.args_schema,
            coroutine=self.handler,
        )


def _pydantic_to_json_schema(model: type[BaseModel]) -> dict:
    """将 Pydantic model 转为 JSON Schema dict (简化版)"""
    schema = model.model_json_schema()
    return {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
    }


class ToolRegistry:
    """Tool 注册中心: 管理所有 GIS Tool"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册一个 Tool"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """按名称获取 Tool"""
        return self._tools.get(name)

    def list_all(self) -> list[Tool]:
        """列出所有注册的 Tool"""
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        """列出所有 Tool 名称"""
        return list(self._tools.keys())

    def to_openai_functions(self) -> list[dict]:
        """转为 OpenAI Function Calling 格式列表"""
        return [t.to_openai_function() for t in self._tools.values()]


# 全局注册中心实例
tool_registry = ToolRegistry()
