"""空间 Tool 定义 — GIS 工具集

定义对接 spatial 服务的全部 Tool，注册到 ToolRegistry。
每个 Tool 带 Pydantic args_schema 供 LangChain StructuredTool 正确映射参数。
"""

import os
import time
from typing import Literal, Optional

import httpx
from pydantic import BaseModel, Field

from .registry import Tool, tool_registry

SPATIAL_URL = os.getenv("SPATIAL_SERVICE_URL", "http://localhost:8002")

# 类别中文别名 → DB 英文枚举（工具层兜底：意图已归一化时通常不会走到这里）
_CATEGORY_ALIASES = {
    "银行": "bank", "银行网点": "bank", "atm": "bank",
    "餐厅": "restaurant", "餐馆": "restaurant", "饭店": "restaurant",
    "饭馆": "restaurant", "火锅": "restaurant", "美食": "restaurant",
    "咖啡": "cafe", "咖啡店": "cafe", "咖啡馆": "cafe", "咖啡厅": "cafe",
    "医院": "hospital", "诊所": "hospital",
    "学校": "school", "大学": "school", "中学": "school", "小学": "school",
    "药店": "pharmacy", "药房": "pharmacy",
    "地铁站": "subway", "地铁": "subway",
    "商场": "marketplace", "购物中心": "marketplace",
    "超市": "retail", "商店": "retail",
}


def _normalize_category(category: Optional[str]) -> Optional[str]:
    """类别归一化：中文别名/大小写 → DB 英文枚举；未知值原样返回（查询为空可接受）"""
    if not category:
        return None
    key = category.strip()
    return _CATEGORY_ALIASES.get(key.lower(), key.lower())


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
    district: Optional[str] = Field(default=None, description="行政区精确过滤（如 '朝阳区'），按真实区界裁剪而非矩形近似")
    category: Optional[str] = Field(default=None, description="类别过滤（英文枚举，如 bank | restaurant | cafe）")
    limit: int = Field(default=50, ge=1, le=1000, description="最大返回条数")


class NearbyQueryInput(BaseModel):
    center: list[float] | str = Field(
        description="中心点：地名（如 '国贸'、'三里屯'）或坐标 [lon, lat]。地名会走地理编码自动解析",
    )
    radius: float = Field(
        description="查询半径（米）。必须与用户要求的范围一致：用户说'500米内'就用 500，禁止放大或自行猜测",
        gt=0,
    )
    category: Optional[str] = Field(default=None, description="类别过滤（英文值）: bank | restaurant | cafe | hospital | school 等")
    district: Optional[str] = Field(default=None, description="行政区精确过滤（如 '朝阳区'），按真实区界裁剪")
    table: str = Field(default="poi", description="表名: poi（默认）| buildings | roads")
    limit: int = Field(default=100, ge=1, le=1000, description="最大返回条数")


class RouteAnalysisInput(BaseModel):
    origin: list[float] | str = Field(description="起点：地名（如 '国贸'）或坐标 [lon, lat]；地名自动地理编码")
    destination: list[float] | str = Field(description="终点：地名或坐标 [lon, lat]；地名自动地理编码")
    mode: Literal["walk", "drive"] = Field(default="walk", description="出行方式: walk=步行 | drive=驾车")


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
    """地名→WGS84坐标：调 spatial 分级地理编码（区级 → POI 锚点 → 百度）。

    返回 {"geometry", "source", "matched_name"} 或 None（未收录/服务异常）。
    """
    try:
        result = await _post("geocode", {"name": name})
        if result.get("found") and result.get("geometry"):
            return {
                "geometry": result["geometry"],
                "source": result.get("source"),
                "matched_name": result.get("matched_name"),
            }
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

    # 地名 → 坐标（分级地理编码：区级 → POI 锚点 → 百度）
    if not src_geom:
        hit = await _geocode(source)
        src_geom = hit["geometry"] if hit else None
    if not tgt_geom:
        hit = await _geocode(target)
        tgt_geom = hit["geometry"] if hit else None

    if not src_geom or not tgt_geom:
        missing = [n for n, g in ((source, src_geom), (target, tgt_geom)) if not g]
        # 未收录（区级/POI/百度均无）→ 允许 LLM 用知识兜底，但要求标注来源
        return {
            "error": "geocode_failed",
            "message": f"地名未收录（已尝试区级/POI/百度地理编码）: {missing}。可用你的知识给出近似坐标重试，但必须在最终结论中注明该坐标来自模型估算",
            "format_example": "source={\"type\":\"Point\",\"coordinates\":[116.458,39.908]}",
            "hint": "北京常见地标参考: 天安门=[116.397,39.909], 国贸=[116.458,39.908], 朝阳公园=[116.478,39.945], 望京=[116.480,39.998], 三里屯=[116.454,39.932]",
        }

    return await _post("distance", {"source": src_geom, "target": tgt_geom})


async def _spatial_query(table: str, bbox=None, district=None, category=None, limit: int = 50) -> dict:
    return await _post("query", {
        "table": table,
        "bbox": bbox,
        "district": district,
        "category": _normalize_category(category),
        "limit": limit,
    })


async def _nearby_query(
    center: list[float] | str,
    radius: float,
    category: Optional[str] = None,
    district: Optional[str] = None,
    table: str = "poi",
    limit: int = 100,
) -> dict:
    # 支持传地名：走分级地理编码解析为坐标
    if isinstance(center, str):
        hit = await _geocode(center)
        if not hit:
            return {
                "error": "geocode_failed",
                "message": f"中心地名 '{center}' 未收录（已尝试区级/POI/百度/高德地理编码）。可改用坐标传入 center，例如 center=[116.458, 39.908]",
                "hint": "北京常见地标参考: 国贸=[116.458,39.908], 三里屯=[116.454,39.932], 望京=[116.480,39.998]",
            }
        center = hit["geometry"]["coordinates"]
    return await _post("nearby", {
        "center": center,
        "radius": radius,
        "category": _normalize_category(category),
        "district": district,
        "table": table,
        "limit": limit,
    })


async def _route_analysis(
    origin: list[float] | str, destination: list[float] | str, mode: str = "walk"
) -> dict:
    # 地名 → 坐标（分级地理编码：区级 → POI 锚点 → 百度/高德）
    if isinstance(origin, str):
        hit = await _geocode(origin)
        if not hit:
            return {
                "error": "geocode_failed",
                "message": f"起点地名 '{origin}' 未收录（已尝试区级/POI/百度/高德地理编码）。可改用坐标传入，例如 origin=[116.458, 39.908]",
                "hint": "北京常见地标参考: 国贸=[116.458,39.908], 三里屯=[116.454,39.932], 望京=[116.480,39.998]",
            }
        origin = hit["geometry"]["coordinates"]
    if isinstance(destination, str):
        hit = await _geocode(destination)
        if not hit:
            return {
                "error": "geocode_failed",
                "message": f"终点地名 '{destination}' 未收录（已尝试区级/POI/百度/高德地理编码）。可改用坐标传入，例如 destination=[116.454, 39.932]",
                "hint": "北京常见地标参考: 国贸=[116.458,39.908], 三里屯=[116.454,39.932], 望京=[116.480,39.998]",
            }
        destination = hit["geometry"]["coordinates"]
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
        "category": _normalize_category(category),
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
            description="从空间数据库查询矢量数据。可查询 buildings/poi/roads 表，支持 bbox 矩形过滤、district 行政区精确过滤（如 '朝阳区'）和类别过滤。返回 GeoJSON FeatureCollection。这是获取研究区域有什么的基础工具。",
            args_schema=SpatialQueryInput,
            handler=_spatial_query,
        ),
        Tool(
            name="nearby_query",
            description="查询某点半径范围内有哪些设施（米制圆域）。适用:『X米内/周边有哪些Y』『附近有什么』类问题。输入中心点（地名或坐标均可，地名自动地理编码）和半径(米)，可选 district 行政区过滤，返回范围内设施及各自距离(properties.distance_m，按距离升序)。请优先使用本工具，不要用 distance_analysis 逐个枚举。",
            args_schema=NearbyQueryInput,
            handler=_nearby_query,
        ),
        Tool(
            name="route_analysis",
            description="计算两点之间的最短步行/驾车路径。输入起点和终点（地名或坐标 [lon,lat] 均可，地名自动地理编码）和出行方式，返回路径 GeoJSON LineString 和距离。适用: 通勤分析、可达性评估、'从A到B怎么走/多远'。",
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
