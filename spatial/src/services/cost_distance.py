"""成本距离 (Cost Distance) 服务

在代价栅格上从源点做累积最小代价传播 (Dijkstra)，
输出每个网格单元的 cost_distance，可选输出到目标点的最小代价路径。
"""

from __future__ import annotations

import heapq
from typing import Any

import numpy as np
from pyproj import Transformer
from shapely.geometry import box, mapping, shape
from shapely.ops import transform as shapely_transform


def _extract_points(features: list[dict]) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    for feat in features:
        geom = feat.get("geometry") or feat
        if not isinstance(geom, dict):
            continue
        if geom.get("type") == "Point":
            lon, lat = geom["coordinates"][:2]
            coords.append((float(lon), float(lat)))
        elif geom.get("type") == "Feature" and geom.get("geometry", {}).get("type") == "Point":
            lon, lat = geom["geometry"]["coordinates"][:2]
            coords.append((float(lon), float(lat)))
    return coords


def _feature_cost(feat: dict, default: float = 1.0) -> float:
    props = feat.get("properties") or {}
    for key in ("cost", "friction", "impedance"):
        if key in props and props[key] is not None:
            try:
                val = float(props[key])
                return max(val, 1e-6)
            except (TypeError, ValueError):
                continue
    return default


def compute_cost_distance(
    sources: list[dict],
    cost_features: list[dict] | None = None,
    resolution: int = 40,
    default_cost: float = 1.0,
    bbox: list[float] | None = None,
    destinations: list[dict] | None = None,
) -> dict[str, Any]:
    """
    计算成本距离表面。

    Args:
        sources: 源点 GeoJSON features（Point）
        cost_features: 代价图层 features；属性 cost/friction/impedance 为相对代价
        resolution: 栅格每边格数 (10–200)
        default_cost: 无代价要素覆盖时的默认代价
        bbox: 可选 [minLon, minLat, maxLon, maxLat]；缺省由源点/代价要素外包确定
        destinations: 可选目标点；若提供则额外返回 least_cost_paths

    Returns:
        FeatureCollection：网格单元带 cost_distance；另含 meta，可选 paths
    """
    src_pts = _extract_points(sources)
    if not src_pts:
        raise ValueError("At least one source Point is required")

    cost_features = cost_features or []
    resolution = int(np.clip(resolution, 10, 200))

    to_m = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    to_ll = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    def lonlat_to_m(lon: float, lat: float) -> tuple[float, float]:
        return to_m.transform(lon, lat)

    src_m = [lonlat_to_m(lon, lat) for lon, lat in src_pts]

    geoms_m: list[tuple[Any, float]] = []
    for feat in cost_features:
        geom = feat.get("geometry")
        if not geom:
            continue
        g = shape(geom)
        if g.is_empty:
            continue
        g_m = shapely_transform(to_m.transform, g)
        geoms_m.append((g_m, _feature_cost(feat, default_cost)))

    if bbox and len(bbox) == 4:
        minx, miny = lonlat_to_m(bbox[0], bbox[1])
        maxx, maxy = lonlat_to_m(bbox[2], bbox[3])
    else:
        xs = [p[0] for p in src_m]
        ys = [p[1] for p in src_m]
        for g, _ in geoms_m:
            b = g.bounds
            xs.extend([b[0], b[2]])
            ys.extend([b[1], b[3]])
        pad = 800.0  # 米
        minx, maxx = min(xs) - pad, max(xs) + pad
        miny, maxy = min(ys) - pad, max(ys) + pad

    if maxx <= minx or maxy <= miny:
        raise ValueError("Invalid analysis extent")

    width = resolution
    height = resolution
    cell_w = (maxx - minx) / width
    cell_h = (maxy - miny) / height

    # 代价栅格
    cost = np.full((height, width), float(default_cost), dtype=np.float64)
    for j in range(height):
        for i in range(width):
            cell = box(
                minx + i * cell_w,
                miny + j * cell_h,
                minx + (i + 1) * cell_w,
                miny + (j + 1) * cell_h,
            )
            # 取覆盖要素中最大代价（障碍/高摩擦优先）
            cell_cost = default_cost
            for g, c in geoms_m:
                if cell.intersects(g):
                    cell_cost = max(cell_cost, c)
            cost[j, i] = cell_cost

    def xy_to_ij(x: float, y: float) -> tuple[int, int]:
        i = int(np.clip((x - minx) / cell_w, 0, width - 1))
        j = int(np.clip((y - miny) / cell_h, 0, height - 1))
        return i, j

    # Dijkstra 累积代价
    dist = np.full((height, width), np.inf, dtype=np.float64)
    parent: dict[tuple[int, int], tuple[int, int] | None] = {}
    heap: list[tuple[float, int, int]] = []

    for sx, sy in src_m:
        i, j = xy_to_ij(sx, sy)
        dist[j, i] = 0.0
        parent[(i, j)] = None
        heapq.heappush(heap, (0.0, i, j))

    neighbors = [
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, 1.41421356237),
        (-1, 1, 1.41421356237),
        (1, -1, 1.41421356237),
        (1, 1, 1.41421356237),
    ]

    while heap:
        d, i, j = heapq.heappop(heap)
        if d > dist[j, i]:
            continue
        for di, dj, step in neighbors:
            ni, nj = i + di, j + dj
            if ni < 0 or ni >= width or nj < 0 or nj >= height:
                continue
            # 边代价 ≈ 平均摩擦 × 步长 × 像元尺寸
            edge = 0.5 * (cost[j, i] + cost[nj, ni]) * step * ((cell_w + cell_h) * 0.5)
            nd = d + edge
            if nd < dist[nj, ni]:
                dist[nj, ni] = nd
                parent[(ni, nj)] = (i, j)
                heapq.heappush(heap, (nd, ni, nj))

    features: list[dict] = []
    finite = dist[np.isfinite(dist)]
    max_d = float(finite.max()) if finite.size else 0.0

    for j in range(height):
        for i in range(width):
            dval = dist[j, i]
            if not np.isfinite(dval):
                continue
            x0 = minx + i * cell_w
            y0 = miny + j * cell_h
            cell_poly = box(x0, y0, x0 + cell_w, y0 + cell_h)
            cell_ll = shapely_transform(to_ll.transform, cell_poly)
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "cost_distance": round(float(dval), 2),
                        "friction": round(float(cost[j, i]), 4),
                        "normalized": round(float(dval / max_d * 100), 2) if max_d > 0 else 0.0,
                    },
                    "geometry": mapping(cell_ll),
                }
            )

    result: dict[str, Any] = {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "method": "cost_distance_dijkstra",
            "resolution": resolution,
            "default_cost": default_cost,
            "source_count": len(src_pts),
            "max_cost_distance": round(max_d, 2),
        },
    }

    if destinations:
        dest_pts = _extract_points(destinations)
        paths: list[dict] = []
        for idx, (dx, dy) in enumerate(dest_pts):
            dm = lonlat_to_m(dx, dy)
            ti, tj = xy_to_ij(dm[0], dm[1])
            if not np.isfinite(dist[tj, ti]):
                continue
            # 回溯路径
            chain: list[tuple[int, int]] = []
            cur: tuple[int, int] | None = (ti, tj)
            seen: set[tuple[int, int]] = set()
            while cur is not None and cur not in seen:
                seen.add(cur)
                chain.append(cur)
                cur = parent.get(cur)
            chain.reverse()
            line_coords = []
            for ci, cj in chain:
                cx = minx + (ci + 0.5) * cell_w
                cy = miny + (cj + 0.5) * cell_h
                lon, lat = to_ll.transform(cx, cy)
                line_coords.append([lon, lat])
            if len(line_coords) >= 2:
                paths.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "destination_index": idx,
                            "cost_distance": round(float(dist[tj, ti]), 2),
                        },
                        "geometry": {"type": "LineString", "coordinates": line_coords},
                    }
                )
        result["paths"] = {"type": "FeatureCollection", "features": paths}

    return result
