"""空间 Tool 定义 — GIS 工具集

定义对接 spatial 服务的全部 Tool，注册到 ToolRegistry。
每个 Tool 带 Pydantic args_schema 供 LangChain StructuredTool 正确映射参数。
"""

import os
import time
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from .registry import Tool, tool_registry

SPATIAL_URL = os.getenv("SPATIAL_SERVICE_URL", "http://localhost:8002")


# ============================================================
# Pydantic 参数 Schema
# ============================================================

class BufferAnalysisInput(BaseModel):
    geometry: dict = Field(description="GeoJSON 几何对象，如 {'type': 'Point', 'coordinates': [116.4, 39.9]}")
    distance: float = Field(description="缓冲距离，单位米", gt=0)


class DistanceAnalysisInput(BaseModel):
    source: str = Field(description="源地名（如'国贸'）或 GeoJSON 字符串")
    target: str = Field(description="目标地名（如'朝阳公园'）或 GeoJSON 字符串")


class SpatialQueryInput(BaseModel):
    table: str = Field(description="表名: buildings | poi | roads | districts | population_grid")
    bbox: Optional[list[float]] = Field(default=None, description="[minLon, minLat, maxLon, maxLat]")
    category: Optional[str] = Field(default=None, description="类别过滤，如 poi.category='coffee'")


class RouteAnalysisInput(BaseModel):
    origin: list[float] = Field(description="起点 [lon, lat]", min_length=2, max_length=2)
    destination: list[float] = Field(description="终点 [lon, lat]", min_length=2, max_length=2)
    mode: str = Field(default="walk", description="walk | drive")


class OverlayAnalysisInput(BaseModel):
    layer_a: dict = Field(description="GeoJSON FeatureCollection A")
    layer_b: dict = Field(description="GeoJSON FeatureCollection B")
    operation: str = Field(default="intersection", description="intersection | union | difference")


class DensityAnalysisInput(BaseModel):
    points: list[dict] = Field(description="GeoJSON features 点列表")
    bandwidth: float = Field(default=500, description="带宽 (米)", gt=0)


class SuitabilityAnalysisInput(BaseModel):
    layers: list[dict] = Field(description="[{'name': '图层名', 'features': [...]}, ...]")
    weights: dict[str, float] = Field(description="权重 {'layer_name': weight}")


class TemporalAnalysisInput(BaseModel):
    table: str = Field(default="poi", description="表名: poi")
    bbox: Optional[list[float]] = Field(default=None, description="空间范围")
    category: Optional[str] = Field(default=None, description="类别过滤")


class CostDistanceAnalysisInput(BaseModel):
    sources: list[dict] = Field(description="源点 GeoJSON features (Point)")
    cost_features: Optional[list[dict]] = Field(
        default=None,
        description="代价图层 features，properties.cost / friction / impedance",
    )
    resolution: int = Field(default=40, description="栅格分辨率 10-200")
    default_cost: float = Field(default=1.0, description="默认摩擦代价")
    bbox: Optional[list[float]] = Field(default=None, description="[minLon,minLat,maxLon,maxLat]")
    destinations: Optional[list[dict]] = Field(
        default=None,
        description="可选目标点 features，返回最小代价路径",
    )


class VoronoiAnalysisInput(BaseModel):
    points: list[dict] = Field(description="生成点 GeoJSON features，至少 2 个")
    clip_boundary: Optional[dict] = Field(
        default=None,
        description="可选裁剪边界 GeoJSON Polygon/MultiPolygon",
    )
    buffer_ratio: float = Field(default=0.1, description="无边界时外扩比例")


class McdaAnalysisInput(BaseModel):
    alternatives: list[dict] = Field(
        description="候选方案 features，properties 含各准则数值字段",
    )
    criteria: list[dict] = Field(
        description="[{'name':'pop','weight':0.4,'direction':'benefit'}, ...]",
    )
    method: str = Field(
        default="topsis",
        description="weighted_sum | weighted_product | topsis",
    )


# ============================================================
# Tool Handler 实现
# ============================================================

async def _post(endpoint: str, body: dict) -> dict:
    """通用 spatial 服务 POST 请求（带耗时日志）"""
    t0 = time.time()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{SPATIAL_URL}/api/spatial/{endpoint}",
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
    elapsed = round(time.time() - t0, 3)
    feat_n = 0
    if isinstance(data, dict) and isinstance(data.get("features"), list):
        feat_n = len(data["features"])
    print(f"[spatial_tool] POST {endpoint} {elapsed}s" + (f" features={feat_n}" if feat_n else ""))
    return data


async def _buffer_analysis(geometry: dict, distance: float) -> dict:
    return await _post("buffer", {"geometry": geometry, "distance": distance})


async def _geocode(name: str) -> dict | None:
    """地名→坐标：从 POI 表模糊搜索（取最多 50 条）"""
    try:
        result = await _post("query", {"table": "poi", "limit": 50})
        features = result.get("features", [])
        # 精确匹配优先
        for f in features:
            props = f.get("properties", {})
            if props.get("name") and props["name"] == name:
                return {"type": "Point", "coordinates": f["geometry"]["coordinates"]}
        # 模糊匹配
        for f in features:
            props = f.get("properties", {})
            if props.get("name") and name in props["name"]:
                return {"type": "Point", "coordinates": f["geometry"]["coordinates"]}
        return None
    except Exception:
        return None


async def _distance_analysis(source: str, target: str) -> dict:
    # 尝试解析为 dict (已经是 GeoJSON)
    src_geom = None
    tgt_geom = None
    try:
        import json as _json
        parsed = _json.loads(source)
        if isinstance(parsed, dict) and "type" in parsed:
            src_geom = parsed
    except Exception:
        pass
    try:
        parsed = _json.loads(target)
        if isinstance(parsed, dict) and "type" in parsed:
            tgt_geom = parsed
    except Exception:
        pass

    # 地名 → 坐标
    if not src_geom:
        src_geom = await _geocode(source)
    if not tgt_geom:
        tgt_geom = await _geocode(target)

    if not src_geom or not tgt_geom:
        # 缺坐标时返回提示，让 LLM 用自身知识提供坐标
        return {
            "error": "geocode_failed",
            "message": f"无法从数据库找到 '{source}' 或 '{target}' 的坐标。请直接提供坐标，例如 source='{{\"type\":\"Point\",\"coordinates\":[116.4,39.9]}}'",
            "hint": "北京常见地标坐标: 天安门=[116.397,39.909], 国贸=[116.458,39.908], 朝阳公园=[116.478,39.945], 望京=[116.480,39.998], 三里屯=[116.454,39.932]",
        }

    return await _post("distance", {"source": src_geom, "target": tgt_geom})


async def _spatial_query(table: str, bbox=None, category=None) -> dict:
    return await _post("query", {
        "table": table,
        "bbox": bbox,
        "category": category,
        "limit": 50,  # 限制返回量，加速 LLM 处理
    })


async def _route_analysis(origin: list[float], destination: list[float], mode: str = "walk") -> dict:
    return await _post("route", {
        "origin": origin,
        "destination": destination,
        "mode": mode,
    })


async def _overlay_analysis(layer_a: dict, layer_b: dict, operation: str = "intersection") -> dict:
    return await _post("overlay", {
        "layer_a": layer_a,
        "layer_b": layer_b,
        "operation": operation,
    })


async def _density_analysis(points: list[dict], bandwidth: float = 500) -> dict:
    return await _post("density", {
        "points": points,
        "bandwidth": bandwidth,
        "resolution": 50,
    })


async def _suitability_analysis(layers: list[dict], weights: dict[str, float]) -> dict:
    return await _post("suitability", {
        "layers": layers,
        "weights": weights,
    })


async def _temporal_analysis(table: str = "poi", bbox=None, category=None) -> dict:
    return await _post("temporal", {
        "table": table,
        "bbox": bbox,
        "category": category,
    })


async def _cost_distance_analysis(
    sources: list[dict],
    cost_features: Optional[list[dict]] = None,
    resolution: int = 40,
    default_cost: float = 1.0,
    bbox: Optional[list[float]] = None,
    destinations: Optional[list[dict]] = None,
) -> dict:
    return await _post("cost-distance", {
        "sources": sources,
        "cost_features": cost_features,
        "resolution": resolution,
        "default_cost": default_cost,
        "bbox": bbox,
        "destinations": destinations,
    })


async def _voronoi_analysis(
    points: list[dict],
    clip_boundary: Optional[dict] = None,
    buffer_ratio: float = 0.1,
) -> dict:
    return await _post("voronoi", {
        "points": points,
        "clip_boundary": clip_boundary,
        "buffer_ratio": buffer_ratio,
    })


async def _mcda_analysis(
    alternatives: list[dict],
    criteria: list[dict],
    method: str = "topsis",
) -> dict:
    return await _post("mcda", {
        "alternatives": alternatives,
        "criteria": criteria,
        "method": method,
    })


# ============================================================
# Tool 注册
# ============================================================

def register_spatial_tools():
    """注册全部空间分析 Tool"""

    tools = [
        Tool(
            name="buffer_analysis",
            description="计算空间对象指定距离的缓冲区范围。输入 GeoJSON 几何对象和距离(米)，返回缓冲后的 GeoJSON 多边形。适用: 服务半径分析、影响范围分析。",
            args_schema=BufferAnalysisInput,
            handler=_buffer_analysis,
        ),
        Tool(
            name="distance_analysis",
            description="计算两个空间对象之间的欧氏/直线距离。输入 source 和 target 两个地名或 GeoJSON，返回距离(米)。适用: 最近设施查询、直线通勤距离。",
            args_schema=DistanceAnalysisInput,
            handler=_distance_analysis,
        ),
        Tool(
            name="spatial_query",
            description="从空间数据库查询矢量数据。可查询 buildings/poi/roads 表，支持 bbox 矩形过滤和类别过滤。返回 GeoJSON FeatureCollection。这是获取研究区域有什么的基础工具。",
            args_schema=SpatialQueryInput,
            handler=_spatial_query,
        ),
        Tool(
            name="route_analysis",
            description="计算两点之间的最短步行/驾车路径。输入起点和终点坐标 [lon,lat]，返回路径 GeoJSON LineString 和距离。适用: 通勤分析、可达性评估。",
            args_schema=RouteAnalysisInput,
            handler=_route_analysis,
        ),
        Tool(
            name="overlay_analysis",
            description="对两个 GeoJSON FeatureCollection 做空间叠加分析（交集/并集/差集）。适用: 多因素空间约束组合，如'地铁800m范围内 AND 不在工业区内'。",
            args_schema=OverlayAnalysisInput,
            handler=_overlay_analysis,
        ),
        Tool(
            name="density_analysis",
            description="对一组点做核密度估计(KDE)，生成密度热力图。输入点集 GeoJSON features 列表和带宽(米)，返回密度网格 GeoJSON。适用: 竞品密度分析、人口热力分析。",
            args_schema=DensityAnalysisInput,
            handler=_density_analysis,
        ),
        Tool(
            name="suitability_analysis",
            description="适宜性评价(Suitability)：多因子空间加权叠加，计算网格综合适宜性评分。输入多个评分图层(带score的FeatureCollection)和权重字典。适用: 连续空间选址热力。",
            args_schema=SuitabilityAnalysisInput,
            handler=_suitability_analysis,
        ),
        Tool(
            name="temporal_analysis",
            description="时空变化分析。对比 POI 数据的空间分布和类别构成，识别热点区域。用于了解某类设施的增长趋势和空间聚集特征。",
            args_schema=TemporalAnalysisInput,
            handler=_temporal_analysis,
        ),
        Tool(
            name="cost_distance_analysis",
            description="成本距离(Cost Distance)：在代价/摩擦栅格上从源点做累积最小代价传播。输入源点、可选代价图层(properties.cost)、可选目标点。返回 cost_distance 表面，若有目标点则含 least-cost paths。适用: 穿越阻力区可达性、消防/救援代价路径。",
            args_schema=CostDistanceAnalysisInput,
            handler=_cost_distance_analysis,
        ),
        Tool(
            name="voronoi_analysis",
            description="Voronoi 泰森多边形：根据生成点划分空间势力范围。输入至少2个点 features，可选裁剪边界。适用: 服务区划分、设施覆盖分区。",
            args_schema=VoronoiAnalysisInput,
            handler=_voronoi_analysis,
        ),
        Tool(
            name="mcda_analysis",
            description="多准则决策分析(MCDA)：对离散候选方案按多准则排序。支持 weighted_sum / weighted_product / topsis。criteria 含 name/weight/direction(benefit|cost)。与 suitability 不同：本工具对方案列表打分排名，不生成栅格。",
            args_schema=McdaAnalysisInput,
            handler=_mcda_analysis,
        ),
    ]

    for t in tools:
        tool_registry.register(t)

    print(f"[tools] Registered {len(tool_registry.list_names())} spatial tools: {tool_registry.list_names()}")


# 启动时注册
register_spatial_tools()
