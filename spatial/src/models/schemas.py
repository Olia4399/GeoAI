"""Pydantic 请求/响应模型"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---- GeoJSON 几何类型 ----

class GeoJSONPoint(BaseModel):
    type: str = "Point"
    coordinates: List[float]  # [lon, lat]


class GeoJSONPolygon(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]]  # [[[lon, lat], ...]]


class GeoJSONLineString(BaseModel):
    type: str = "LineString"
    coordinates: List[List[float]]  # [[lon, lat], ...]


# ---- 空间分析请求/响应 ----

class BufferRequest(BaseModel):
    """缓冲区分析请求"""
    geometry: Dict[str, Any] = Field(
        description="GeoJSON 几何对象: Point, Polygon, LineString",
        examples=[{"type": "Point", "coordinates": [116.4, 39.9]}],
    )
    distance: float = Field(
        description="缓冲距离 (米)",
        gt=0,
        examples=[500],
    )


class BufferResponse(BaseModel):
    """缓冲区分析响应"""
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]]


class DistanceRequest(BaseModel):
    """距离计算请求"""
    source: Dict[str, Any] = Field(
        description="源 GeoJSON 几何对象",
        examples=[{"type": "Point", "coordinates": [116.458, 39.908]}],
    )
    target: Dict[str, Any] = Field(
        description="目标 GeoJSON 几何对象",
        examples=[{"type": "Point", "coordinates": [116.468, 39.906]}],
    )


class DistanceResponse(BaseModel):
    """距离计算响应"""
    distance_meters: float = Field(description="距离 (米)")
    source: Dict[str, Any]
    target: Dict[str, Any]


class SpatialError(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None


# ---- Phase 2 新增 ----

class QueryRequest(BaseModel):
    """空间数据查询请求"""
    table: str = Field(description="表名: buildings | poi | roads")
    bbox: Optional[List[float]] = Field(default=None, description="[minLon, minLat, maxLon, maxLat]")
    category: Optional[str] = Field(default=None, description="类别过滤")
    limit: int = Field(default=200, ge=1, le=1000, description="最大返回条数")


class QueryResponse(BaseModel):
    """空间数据查询响应"""
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]]


class RouteRequest(BaseModel):
    """路径规划请求"""
    origin: List[float] = Field(description="起点 [lon, lat]", min_length=2, max_length=2)
    destination: List[float] = Field(description="终点 [lon, lat]", min_length=2, max_length=2)
    mode: str = Field(default="walk", description="walk | drive")


class OverlayRequest(BaseModel):
    """空间叠加请求"""
    layer_a: Dict[str, Any] = Field(description="GeoJSON FeatureCollection A")
    layer_b: Dict[str, Any] = Field(description="GeoJSON FeatureCollection B")
    operation: str = Field(default="intersection", description="intersection | union | difference")


class DensityRequest(BaseModel):
    """核密度分析请求"""
    points: List[Dict[str, Any]] = Field(description="GeoJSON FeatureCollection 的 features 列表")
    bandwidth: float = Field(default=500, gt=0, description="带宽 (米)")
    resolution: int = Field(default=50, ge=10, le=200, description="网格分辨率")


class SuitabilityLayer(BaseModel):
    """适宜性评价图层"""
    name: str = Field(description="图层名称")
    features: List[Dict[str, Any]] = Field(description="GeoJSON features")


class SuitabilityRequest(BaseModel):
    """适宜性评价请求"""
    layers: List[SuitabilityLayer] = Field(description="多个评分图层")
    weights: Dict[str, float] = Field(description="权重 {layer_name: weight}")
    grid_size: float = Field(default=0.002, description="网格大小 (度)")


class CostDistanceRequest(BaseModel):
    """成本距离请求"""
    sources: List[Dict[str, Any]] = Field(description="源点 GeoJSON features (Point)")
    cost_features: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="代价图层 features，属性 cost/friction/impedance",
    )
    resolution: int = Field(default=40, ge=10, le=200, description="栅格分辨率")
    default_cost: float = Field(default=1.0, gt=0, description="默认摩擦代价")
    bbox: Optional[List[float]] = Field(
        default=None,
        description="[minLon, minLat, maxLon, maxLat]",
    )
    destinations: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="可选目标点 features，用于回溯最小代价路径",
    )


class VoronoiRequest(BaseModel):
    """Voronoi 泰森多边形请求"""
    points: List[Dict[str, Any]] = Field(description="生成点 GeoJSON features")
    clip_boundary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="可选裁剪边界 GeoJSON Polygon/MultiPolygon",
    )
    buffer_ratio: float = Field(
        default=0.1,
        ge=0,
        le=1,
        description="无裁剪边界时对外包矩形的外扩比例",
    )


class McdaCriterion(BaseModel):
    """MCDA 准则"""
    name: str = Field(description="准则字段名，对应 feature.properties 键")
    weight: float = Field(default=1.0, description="权重（会自动归一化）")
    direction: str = Field(
        default="benefit",
        description="benefit=越大越好, cost=越小越好",
    )


class McdaRequest(BaseModel):
    """多准则决策分析请求"""
    alternatives: List[Dict[str, Any]] = Field(
        description="候选方案 GeoJSON features，properties 含各准则数值",
    )
    criteria: List[McdaCriterion] = Field(description="准则定义列表")
    method: str = Field(
        default="topsis",
        description="weighted_sum | weighted_product | topsis",
    )
