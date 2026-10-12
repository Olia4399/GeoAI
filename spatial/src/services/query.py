"""空间数据查询服务

直接从 PostGIS 查询矢量空间数据，返回 GeoJSON FeatureCollection。
这是 Agent 与数据库的桥梁。
"""

import math

from .. import database
from ..database import get_db_url

import psycopg2
import psycopg2.extras


def spatial_query(
    table: str,
    bbox: list[float] | None = None,
    district: str | None = None,
    category: str | None = None,
    limit: int = 200,
) -> dict:
    """
    查询空间表的 GeoJSON 数据。

    Args:
        table: 表名 (buildings / poi / roads / districts / population_grid)
        bbox: [minLon, minLat, maxLon, maxLat] 可选
        district: 行政区精确过滤（按 districts 表真实区界 ST_Contains，而非矩形近似）
        category: 类别过滤 (poi.category 或 buildings.usage)
        limit: 最大返回条数

    Returns:
        GeoJSON FeatureCollection
    """
    # 表名白名单防注入
    allowed_tables = {"buildings", "poi", "roads", "districts", "population_grid"}
    if table not in allowed_tables:
        raise ValueError(f"Table '{table}' not allowed. Choose from: {allowed_tables}")

    conn = database.db_conn
    if not conn or conn.closed:
        conn = psycopg2.connect(get_db_url())

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 构建 SQL
    geom_col = "geom"
    cols = "id, name, geom"
    where_parts = []
    params = []

    if table == "buildings":
        cols = "id, name, height, usage, geom"
        if category:
            where_parts.append("usage = %s")
            params.append(category)
    elif table == "poi":
        cols = "id, name, category, geom"
        if category:
            where_parts.append("category = %s")
            params.append(category)
    elif table == "roads":
        cols = "id, name, road_type, speed_limit, geom"
        if category:
            where_parts.append("road_type = %s")
            params.append(category)
    elif table == "districts":
        cols = "id, name, admin_level, population_10k, area_sqkm, geom"
        if category:
            # category 可以是区名
            where_parts.append("name = %s")
            params.append(category)
    elif table == "population_grid":
        cols = "id, grid_id, pop_density, score, district, geom"
        if category:
            where_parts.append("district = %s")
            params.append(category)
    
    if bbox and len(bbox) == 4:
        where_parts.append(
            "geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)"
        )
        params.extend([bbox[0], bbox[1], bbox[2], bbox[3]])

    # 行政区精确过滤：谓词交给 districts 表真实区界（支持"朝阳"→"朝阳区"前缀）
    if district:
        where_parts.append(
            f"EXISTS (SELECT 1 FROM districts d WHERE (d.name = %s OR d.name LIKE %s || '%%') "
            f"AND ST_Contains(d.geom, {table}.geom))"
        )
        params.append(district)
        params.append(district)

    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    sql = f"""
        SELECT {cols}, ST_AsGeoJSON(geom)::json AS geometry
        FROM {table}
        WHERE {where_clause}
        LIMIT %s
    """
    params.append(limit)

    cur.execute(sql, params)
    rows = cur.fetchall()

    features = []
    for row in rows:
        geom = row.pop("geometry")
        props = {k: str(v) if isinstance(v, (bytes,)) else v for k, v in row.items()}
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": geom,
        })

    cur.close()

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def nearby_query(
    center: list[float],
    radius: float,
    table: str = "poi",
    category: str | None = None,
    district: str | None = None,
    limit: int = 100,
) -> dict:
    """圆域附近查询：返回 center 半径 radius 米内的设施，按距离升序。

    两段式过滤（与索引设计一致）：
      ① geom && ST_Expand(中心点, 度余量) —— 包围盒粗筛，走 GiST 索引；
      ② ST_DWithin(geography) —— 精确的米制圆域判断（geography 直接按米算，避免"度当米"）。
    """
    allowed_tables = {"buildings", "poi", "roads", "districts", "population_grid"}
    if table not in allowed_tables:
        raise ValueError(f"Table '{table}' not allowed. Choose from: {allowed_tables}")
    if len(center) != 2:
        raise ValueError("center must be [lon, lat]")
    if radius <= 0:
        raise ValueError("radius must be > 0")

    lon, lat = float(center[0]), float(center[1])

    conn = database.db_conn
    if not conn or conn.closed:
        conn = psycopg2.connect(get_db_url())

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cols = "id, name, geom"
    if table == "buildings":
        cols = "id, name, height, usage, geom"
    elif table == "poi":
        cols = "id, name, category, geom"
    elif table == "roads":
        cols = "id, name, road_type, speed_limit, geom"

    # 经度方向的度余量（1° 经度 ≈ 111320*cos(lat) 米，取最大值保证包围盒是圆的超集）
    deg_margin = radius / 111320.0 / max(math.cos(math.radians(lat)), 0.1)

    where_parts = [
        "geom && ST_Expand(ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)",
        "ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)",
    ]
    where_params: list = [lon, lat, deg_margin, lon, lat, radius]

    if category and table == "poi":
        where_parts.append("category = %s")
        where_params.append(category)
    elif category and table == "buildings":
        where_parts.append("usage = %s")
        where_params.append(category)

    # 行政区精确过滤（可与圆域叠加：如"朝阳区范围内、国贸 2km 内的银行"）
    if district:
        where_parts.append(
            f"EXISTS (SELECT 1 FROM districts d WHERE (d.name = %s OR d.name LIKE %s || '%%') "
            f"AND ST_Contains(d.geom, {table}.geom))"
        )
        where_params.append(district)
        where_params.append(district)

    sql = f"""
        SELECT {cols},
               ST_AsGeoJSON(geom)::json AS geometry,
               ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) AS distance_m
        FROM {table}
        WHERE {" AND ".join(where_parts)}
        ORDER BY distance_m
        LIMIT %s
    """
    params = [lon, lat] + where_params + [limit]

    cur.execute(sql, params)
    rows = cur.fetchall()

    features = []
    for row in rows:
        geom = row.pop("geometry")
        dist = row.pop("distance_m", None)
        props = {k: str(v) if isinstance(v, (bytes,)) else v for k, v in row.items()}
        if dist is not None:
            props["distance_m"] = round(float(dist), 1)
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": geom,
        })

    cur.close()

    return {
        "type": "FeatureCollection",
        "features": features,
        "center": [lon, lat],
        "radius": radius,
    }
