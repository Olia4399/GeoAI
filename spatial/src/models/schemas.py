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
