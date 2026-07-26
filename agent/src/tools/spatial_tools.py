"""空间 Tool 定义

定义对接 spatial 服务的 GIS 工具，注册到 ToolRegistry。
每个 Tool 带 Pydantic args_schema 供 LangChain StructuredTool 正确映射参数。
"""

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .registry import Tool, tool_registry

SPATIAL_URL = os.getenv("SPATIAL_SERVICE_URL", "http://localhost:8002")


# ---- Pydantic 参数 Schema ----

class BufferAnalysisInput(BaseModel):
    geometry: dict = Field(description="GeoJSON 几何对象，如 {'type': 'Point', 'coordinates': [116.4, 39.9]}")
    distance: float = Field(description="缓冲距离，单位米", gt=0)


class DistanceAnalysisInput(BaseModel):
    source: dict = Field(description="源 GeoJSON 几何对象")
    target: dict = Field(description="目标 GeoJSON 几何对象")


# ---- Tool Handler 实现 ----

async def _buffer_analysis(geometry: dict, distance: float) -> dict:
    """调用 spatial 服务的缓冲区分析"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{SPATIAL_URL}/api/spatial/buffer",
            json={"geometry": geometry, "distance": distance},
        )
        resp.raise_for_status()
        return resp.json()


async def _distance_analysis(source: dict, target: dict) -> dict:
    """调用 spatial 服务的距离计算"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{SPATIAL_URL}/api/spatial/distance",
            json={"source": source, "target": target},
        )
        resp.raise_for_status()
        return resp.json()


# ---- Tool 注册 ----

def register_spatial_tools():
    """注册所有空间分析 Tool"""

    tool_registry.register(Tool(
        name="buffer_analysis",
        description="计算空间对象指定距离的缓冲区范围。输入 GeoJSON 几何对象和距离(米)，返回缓冲后的 GeoJSON 多边形。",
        args_schema=BufferAnalysisInput,
        handler=_buffer_analysis,
    ))

    tool_registry.register(Tool(
        name="distance_analysis",
        description="计算两个空间对象之间的距离。输入 source 和 target 两个 GeoJSON 几何对象，返回距离(米)。",
        args_schema=DistanceAnalysisInput,
        handler=_distance_analysis,
    ))

    print(f"[tools] Registered {len(tool_registry.list_names())} spatial tools: {tool_registry.list_names()}")


# 启动时注册
register_spatial_tools()
