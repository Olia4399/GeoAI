"""空间叠加分析服务

使用 GeoPandas overlay 对两个图层做交/并/差操作。
"""

from geopandas import GeoDataFrame
from shapely.geometry import shape


def compute_overlay(
    layer_a: dict,
    layer_b: dict,
    operation: str = "intersection",
) -> dict:
    """
    对两个 GeoJSON FeatureCollection 做空间叠加。

    Args:
        layer_a: 第一个 GeoJSON FeatureCollection
        layer_b: 第二个 GeoJSON FeatureCollection
        operation: intersection | union | difference

    Returns:
        叠加后的 GeoJSON FeatureCollection
    """
    valid_ops = {"intersection", "union", "difference"}
    if operation not in valid_ops:
        raise ValueError(f"Operation '{operation}' not supported. Choose: {valid_ops}")

    # 提前提取 features，空数组时直接返回，避免 GeoPandas from_features 空列表报错
    features_a = layer_a.get("features", []) if isinstance(layer_a, dict) else []
    features_b = layer_b.get("features", []) if isinstance(layer_b, dict) else []

    if not features_a or not features_b:
        return {"type": "FeatureCollection", "features": []}

    # GeoJSON → GeoDataFrame
    gdf_a = GeoDataFrame.from_features(features_a, crs="EPSG:4326")
    gdf_b = GeoDataFrame.from_features(features_b, crs="EPSG:4326")

    if gdf_a.empty or gdf_b.empty:
        return {"type": "FeatureCollection", "features": []}

    # 转换到米制做 overlay
    gdf_a_m = gdf_a.to_crs("EPSG:3857")
    gdf_b_m = gdf_b.to_crs("EPSG:3857")

    # 执行叠加
    result_m = gdf_a_m.overlay(gdf_b_m, how=operation)

    # 转回 WGS84
    result = result_m.to_crs("EPSG:4326")

    geo = result.__geo_interface__
    geo["type"] = "FeatureCollection"

    # 转为标准格式
    features = []
    for feat in geo.get("features", []):
        features.append({
            "type": "Feature",
            "properties": feat.get("properties", {}),
            "geometry": feat.get("geometry", {}),
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
