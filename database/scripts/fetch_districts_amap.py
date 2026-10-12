"""从高德行政区划 API 抓取北京 16 区真实边界，替换 districts 表的矩形近似数据。

用法：
    cd spatial && ./.venv/Scripts/python.exe ../database/scripts/fetch_districts_amap.py

说明：
    - 按 adcode 逐区查询（避免"朝阳区"命中长春朝阳区的同名歧义）；
    - 高德返回 GCJ02 坐标折线，用 spatial 服务的 gcj02_to_wgs84 转换为 WGS84 后入库；
    - 多重环时取顶点最多的主体环并给出警告（保留原 area_sqkm 官方数值不改）；
    - 需要 spatial/.env 中配置 AMAP_KEY。
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "spatial"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO / "spatial" / ".env")

import os  # noqa: E402
import time  # noqa: E402

import psycopg2  # noqa: E402
import requests  # noqa: E402

from src.services.geocode import gcj02_to_wgs84  # noqa: E402

# 北京 16 区 adcode（2010 年区划调整后）
BEIJING_DISTRICTS = [
    ("110101", "东城区"), ("110102", "西城区"), ("110105", "朝阳区"),
    ("110106", "丰台区"), ("110107", "石景山区"), ("110108", "海淀区"),
    ("110109", "门头沟区"), ("110111", "房山区"), ("110112", "通州区"),
    ("110113", "顺义区"), ("110114", "昌平区"), ("110115", "大兴区"),
    ("110116", "怀柔区"), ("110117", "平谷区"), ("110118", "密云区"),
    ("110119", "延庆区"),
]


def fetch_district_polyline(adcode: str, key: str) -> str:
    """按 adcode 查询单个区，返回 polyline 字符串"""
    resp = requests.get(
        "https://restapi.amap.com/v3/config/district",
        params={"keywords": adcode, "subdistrict": 0, "extensions": "all", "key": key},
        timeout=30,
    )
    data = resp.json()
    if data.get("status") != "1":
        raise RuntimeError(f"高德 API 异常: status={data.get('status')} info={data.get('info')}")
    dists = data.get("districts") or []
    if not dists:
        raise RuntimeError(f"adcode={adcode} 无返回")
    return dists[0].get("polyline") or ""


def polyline_to_wgs84_polygon(polyline: str) -> tuple[str, int]:
    """高德折线（GCJ02，多环用 | 分隔）→ WKT POLYGON（WGS84，取主体环）"""
    rings = [r for r in polyline.split("|") if r.strip()]
    if not rings:
        raise ValueError("空折线")
    if len(rings) > 1:
        print(f"    ⚠ 含 {len(rings)} 个环，取顶点最多的主体环（飞地/离岛略过）")
    main = max(rings, key=lambda r: len(r.split(";")))
    coords = []
    for pair in main.split(";"):
        lng_s, lat_s = pair.split(",")
        lng, lat = gcj02_to_wgs84(float(lng_s), float(lat_s))
        coords.append((round(lng, 6), round(lat, 6)))
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    wkt = "POLYGON((" + ", ".join(f"{x} {y}" for x, y in coords) + "))"
    return wkt, len(coords)


def main():
    key = os.getenv("AMAP_KEY", "").strip()
    if not key:
        raise RuntimeError("未配置 AMAP_KEY（spatial/.env）")

    conn = psycopg2.connect("postgresql://geoai:geoai123@localhost:5432/geoai")
    cur = conn.cursor()

    updated = 0
    for i, (adcode, name) in enumerate(BEIJING_DISTRICTS):
        if i:
            time.sleep(0.8)  # 控制 QPS，避免个人认证低并发限制（CUQPS_HAS_EXCEEDED_THE_LIMIT）
        try:
            polyline = fetch_district_polyline(adcode, key)
            wkt, n = polyline_to_wgs84_polygon(polyline)
        except Exception as e:
            print(f"  {name}({adcode}): 失败 {e}")
            continue
        cur.execute(
            "UPDATE districts SET geom = ST_MakeValid(ST_GeomFromText(%s, 4326)) WHERE name = %s",
            (wkt, name),
        )
        if cur.rowcount:
            print(f"  {name}({adcode}): 已更新（{n} 个顶点）")
            updated += 1
        else:
            print(f"  {name}({adcode}): districts 表中无此区名，未更新")

    conn.commit()

    # 验证：面积与有效性
    cur.execute(
        """
        SELECT name, round((ST_Area(geom::geography)/1e6)::numeric, 1) AS km2, ST_IsValid(geom)
        FROM districts WHERE name IN ('东城区','朝阳区','海淀区','通州区')
        ORDER BY name
        """
    )
    print("\n验证（面积 km² / 有效性）：")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} km² | valid={row[2]}")

    conn.close()
    print(f"\n完成：更新 {updated}/16 个区")


if __name__ == "__main__":
    main()
