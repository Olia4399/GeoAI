"""距离计算服务

使用 Shapely + PyProj 计算两个空间对象间的距离 (米)。
Phase 1 使用本地几何计算; Phase 2 可切换为 PostGIS ST_Distance。
"""

from typing import Any, Dict

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform


def compute_distance(source: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
    """
    计算两个 GeoJSON 几何对象之间的距离。

    Args:
        source: 源 GeoJSON 几何对象
        target: 目标 GeoJSON 几何对象

    Returns:
        距离结果，含 distance_meters
    """
    # 1. GeoJSON → Shapely
    src_geom = shape(source)
    tgt_geom = shape(target)

    if src_geom.is_empty:
        raise ValueError("Source geometry is empty")
    if tgt_geom.is_empty:
        raise ValueError("Target geometry is empty")

    # 2. 坐标转换 WGS84 → Web Mercator 以计算真实米制距离
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

    src_meters = transform(transformer.transform, src_geom)
    tgt_meters = transform(transformer.transform, tgt_geom)

    # 3. 计算距离
    distance = src_meters.distance(tgt_meters)

    return {
        "distance_meters": round(distance, 2),
        "source": source,
        "target": target,
    }
