"""适宜性评价服务

加权叠加 (Weighted Overlay): 将多个评分图层按权重合并，输出综合得分的 GeoJSON。
"""

import json
from typing import Any

from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import numpy as np


def compute_suitability(
    layers: list[dict],
    weights: dict[str, float],
    grid_size: float = 0.002,
) -> dict:
    """
    多因子加权叠加，计算每个空间单元的综合适宜性得分。

    Args:
        layers: [{name, features: GeoJSON FeatureCollection}, ...]
        weights: {layer_name: weight} (权重之和应为 1.0)
        grid_size: 网格单元大小 (度，约 200m)

    Returns:
        GeoJSON FeatureCollection，每个 feature 带 score 属性
    """
    if not layers:
        raise ValueError("At least one layer is required")
    if not weights:
        raise ValueError("Weights are required")

    # 归一化权重
    total = sum(weights.values())
    norm_weights = {k: v / total for k, v in weights.items()}

    # 构建覆盖所有图层的网格
    all_polys = []
    for layer in layers:
        for feat in layer.get("features", []):
            g = shape(feat["geometry"])
            all_polys.append(g)

    if not all_polys:
        return {"type": "FeatureCollection", "features": []}

    combined = unary_union(all_polys)
    bounds = combined.bounds  # (minx, miny, maxx, maxy)

    # 生成网格
    x = np.arange(bounds[0], bounds[2], grid_size)
    y = np.arange(bounds[1], bounds[3], grid_size)

    from shapely.geometry import box as shapely_box

    scored_cells = []

    for i in range(len(x)):
        for j in range(len(y)):
            cell = shapely_box(x[i], y[j], x[i] + grid_size, y[j] + grid_size)
            if not cell.intersects(combined):
                continue

            total_score = 0.0

            for layer in layers:
                layer_name = layer.get("name", "")
                weight = norm_weights.get(layer_name, 0.0)
                if weight == 0.0:
                    continue

                # 计算该图层在此网格内的平均得分
                layer_score = 0.0
                layer_count = 0

                for feat in layer.get("features", []):
                    f_geom = shape(feat["geometry"])
                    if cell.intersects(f_geom):
                        intersection = cell.intersection(f_geom)
                        score_val = (
                            feat.get("properties", {}).get("score", 50)
                            if feat.get("properties")
                            else 50
                        )
                        area_ratio = intersection.area / f_geom.area if f_geom.area > 0 else 1.0
                        layer_score += score_val * area_ratio
                        layer_count += 1

                if layer_count > 0:
                    layer_score /= layer_count

                total_score += layer_score * weight

            if total_score > 0:
                scored_cells.append({
                    "type": "Feature",
                    "properties": {"score": round(total_score, 2)},
                    "geometry": mapping(cell),
                })

    return {
        "type": "FeatureCollection",
        "features": scored_cells,
    }
