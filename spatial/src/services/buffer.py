"""缓冲区分析服务

使用 Shapely 进行几何缓冲区计算。
坐标系: WGS84 (EPSG:4326) 输入 → Web Mercator (EPSG:3857) 计算 → WGS84 输出
"""

import json
from typing import Any, Dict

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform


def compute_buffer(geometry: Dict[str, Any], distance_meters: float) -> Dict[str, Any]:
    """
    计算 GeoJSON 几何对象的缓冲区。

    Args:
        geometry: GeoJSON 几何对象 (Point, Polygon, LineString 等)
        distance_meters: 缓冲距离 (米)

    Returns:
        GeoJSON FeatureCollection，包含缓冲后的多边形
    """
    # 1. GeoJSON → Shapely
    geom = shape(geometry)

    if geom.is_empty:
        raise ValueError("Input geometry is empty")

    # 2. 坐标系转换: WGS84 (4326) → Web Mercator (3857) 以进行米制缓冲
    transformer_to_meters = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    transformer_to_degrees = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    geom_meters = transform(transformer_to_meters.transform, geom)

    # 3. 执行缓冲区计算
    buffer_meters = geom_meters.buffer(distance_meters)

    # 4. 转回 WGS84
    buffer_degrees = transform(transformer_to_degrees.transform, buffer_meters)

    # 5. 构建 GeoJSON FeatureCollection
    feature = {
        "type": "Feature",
        "properties": {
            "distance_meters": distance_meters,
            "area_sqm": buffer_meters.area,
        },
        "geometry": json.loads(json.dumps(buffer_degrees.__geo_interface__)),
    }

    return {
        "type": "FeatureCollection",
        "features": [feature],
    }
