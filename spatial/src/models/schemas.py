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
