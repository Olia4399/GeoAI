"""Voronoi (泰森多边形) 服务

基于 Shapely voronoi_diagram，对点集生成泰森多边形，
可选裁剪到研究区边界。
"""

from __future__ import annotations

from typing import Any

from shapely.geometry import MultiPoint, Point, box, mapping, shape
from shapely.ops import voronoi_diagram


def _extract_point_features(points: list[dict]) -> list[tuple[Point, dict]]:
    result: list[tuple[Point, dict]] = []
    for feat in points:
        geom = feat.get("geometry")
        props = dict(feat.get("properties") or {})
        if geom is None and feat.get("type") == "Point":
            geom = feat
        if not geom or geom.get("type") != "Point":
            continue
        lon, lat = geom["coordinates"][:2]
        result.append((Point(float(lon), float(lat)), props))
    return result


def compute_voronoi(
    points: list[dict],
    clip_boundary: dict | None = None,
    buffer_ratio: float = 0.1,
) -> dict[str, Any]:
    """
    生成 Voronoi 多边形。

    Args:
        points: 点集 GeoJSON features
        clip_boundary: 可选裁剪边界 GeoJSON Polygon / MultiPolygon / bbox Feature
        buffer_ratio: 无裁剪边界时，对外包矩形外扩比例

    Returns:
        GeoJSON FeatureCollection，每个面带 site_index 与源点属性
    """
    sites = _extract_point_features(points)
    if len(sites) < 2:
        raise ValueError("Voronoi requires at least 2 points")

    pts = [p for p, _ in sites]
    mp = MultiPoint(pts)

    if clip_boundary:
        clip_geom = shape(clip_boundary if clip_boundary.get("type") != "Feature" else clip_boundary["geometry"])
        if clip_geom.is_empty:
            raise ValueError("clip_boundary geometry is empty")
        envelope = clip_geom
    else:
        minx, miny, maxx, maxy = mp.bounds
        dx = max(maxx - minx, 1e-6)
        dy = max(maxy - miny, 1e-6)
        pad_x = dx * buffer_ratio
        pad_y = dy * buffer_ratio
        envelope = box(minx - pad_x, miny - pad_y, maxx + pad_x, maxy + pad_y)

    # Shapely voronoi_diagram：envelope 约束外延
    regions = voronoi_diagram(mp, envelope=envelope, edges=False)
    if regions.is_empty:
        return {"type": "FeatureCollection", "features": []}

    polys = list(regions.geoms) if hasattr(regions, "geoms") else [regions]
    clip = envelope if clip_boundary is None else shape(
        clip_boundary if clip_boundary.get("type") != "Feature" else clip_boundary["geometry"]
    )

    features: list[dict] = []
    for poly in polys:
        if poly.is_empty or poly.area <= 0:
            continue
        clipped = poly.intersection(clip)
        if clipped.is_empty:
            continue
        # 匹配落在该多边形内的生成点
        matched_idx = None
        matched_props: dict = {}
        for idx, (pt, props) in enumerate(sites):
            if clipped.covers(pt) or clipped.intersects(pt.buffer(1e-9)):
                matched_idx = idx
                matched_props = props
                break

        # MultiPolygon 拆分
        parts = list(clipped.geoms) if clipped.geom_type == "MultiPolygon" else [clipped]
        for part in parts:
            if part.is_empty or part.area <= 0:
                continue
            props_out = {
                "site_index": matched_idx,
                "area_deg2": round(float(part.area), 10),
                **{k: v for k, v in matched_props.items() if k not in ("site_index", "area_deg2")},
            }
            features.append(
                {
                    "type": "Feature",
                    "properties": props_out,
                    "geometry": mapping(part),
                }
            )

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "method": "voronoi_diagram",
            "site_count": len(sites),
            "polygon_count": len(features),
        },
    }
