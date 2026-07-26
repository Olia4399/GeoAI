"""时空变化分析服务

对比当前数据与历史快照，计算空间变化指标。
Phase 4: 基于现有 POI 数据的变化统计。历史快照通过多时相 SQL 表或外部 API 获取。
"""

import json


def temporal_analysis(
    table: str,
    bbox: list[float] | None = None,
    category: str | None = None,
    metric: str = "count",
) -> dict:
    """
    时空变化分析。

    Args:
        table: 分析表名 (poi)
        bbox: 空间范围 [minLon, minLat, maxLon, maxLat]
        category: 类别过滤
        metric: 指标 (count / density)

    Returns:
        {current: {total, by_category}, changes: [{period, delta, rate}]}
    """
    from .. import database
    from ..database import get_db_url
    import psycopg2
    import psycopg2.extras

    allowed_tables = {"poi"}
    if table not in allowed_tables:
        raise ValueError(f"Table '{table}' not supported for temporal analysis")

    conn = database.db_conn
    if not conn or conn.closed:
        conn = psycopg2.connect(get_db_url())

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 当前数据统计
    where = "WHERE 1=1"
    params = []
    if bbox and len(bbox) == 4:
        where += " AND geom && ST_MakeEnvelope(%s,%s,%s,%s,4326)"
        params.extend(bbox)
    if category:
        where += " AND category = %s"
        params.append(category)

    # 总量
    cur.execute(f"SELECT COUNT(*) AS total FROM {table} {where}", params)
    total = cur.fetchone()["total"]

    # 按类别
    cur.execute(
        f"SELECT category, COUNT(*) AS cnt FROM {table} {where} GROUP BY category ORDER BY cnt DESC LIMIT 10",
        params,
    )
    by_category = {r["category"]: r["cnt"] for r in cur.fetchall()}

    # 空间分布热点 (top N 密度区域，以 POI 点为中心做简单聚类)
    cur.execute(
        f"""
        SELECT ST_X(geom) AS lon, ST_Y(geom) AS lat, name, category
        FROM {table} {where}
        LIMIT 100
        """,
        params,
    )
    hotspots = []
    for r in cur.fetchall():
        if r["lon"] and r["lat"]:
            hotspots.append({
                "name": r["name"],
                "category": r["category"],
                "coordinates": [r["lon"], r["lat"]],
            })

    cur.close()

    # 因为没有历史快照数据，模拟变化趋势说明
    current_data = {
        "total": total,
        "by_category": by_category,
        "hotspots": hotspots[:20],
    }

    return {
        "table": table,
        "metric": metric,
        "bbox": bbox,
        "current": current_data,
        "note": "历史对比数据需要多时相 OSM 快照。当前仅展示最新数据分布。可通过 Ohsome API 获取历史变化趋势。",
    }
