"""Tool 注册中心 — MCP 风格 Tool 管理

注册、查找、调用 GIS 工具。
"""

from typing import Any, Callable


class Tool:
    """单个 Tool 定义"""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters  # JSON Schema for parameters
        self.handler = handler  # async callable

    def to_openai_function(self) -> dict:
        """转为 OpenAI Function Calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_langchain_tool(self):
        """转为 LangChain StructuredTool"""
        from langchain.tools import StructuredTool

        return StructuredTool(
            name=self.name,
            description=self.description,
            args_schema=None,  # Phase 1 简单处理
            func=self.handler,
        )


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
