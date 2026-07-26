"""空间数据查询服务

直接从 PostGIS 查询矢量空间数据，返回 GeoJSON FeatureCollection。
这是 Agent 与数据库的桥梁。
"""

from .. import database
from ..database import get_db_url

import psycopg2
import psycopg2.extras


def spatial_query(
    table: str,
    bbox: list[float] | None = None,
    category: str | None = None,
    limit: int = 200,
) -> dict:
    """
    查询空间表的 GeoJSON 数据。

    Args:
        table: 表名 (buildings / poi / roads)
        bbox: [minLon, minLat, maxLon, maxLat] 可选
        category: 类别过滤 (poi.category 或 buildings.usage)
        limit: 最大返回条数

    Returns:
        GeoJSON FeatureCollection
    """
    # 表名白名单防注入
    allowed_tables = {"buildings", "poi", "roads"}
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

    if bbox and len(bbox) == 4:
        where_parts.append(
            "geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)"
        )
        params.extend([bbox[0], bbox[1], bbox[2], bbox[3]])

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
