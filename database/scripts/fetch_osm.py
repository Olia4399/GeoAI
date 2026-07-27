"""
OSM 数据采集脚本 — 下载北京朝阳区道路/建筑/POI 并生成 SQL INSERT。

使用 OSMnx 从 OpenStreetMap 下载数据。
默认输出: database/init/02-osm-chaoyang.sql（会覆盖）
建议道路/建筑增量输出到: database/init/07-osm-roads-buildings.sql
Usage:
    cd database
    uv run --directory ../spatial python scripts/fetch_osm.py --layers roads,buildings --building-limit 500
    uv run --directory ../spatial python scripts/fetch_osm.py --layers poi --output init/02-osm-chaoyang.sql
"""
from __future__ import annotations
import argparse
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    import osmnx as ox
except ImportError:
    print("Please install osmnx: cd spatial && uv add osmnx")
    sys.exit(1)

# 朝阳区坐标 (粗略范围)
NORTH, SOUTH = 40.01, 39.82
EAST, WEST = 116.60, 116.35

DEFAULT_RETRIES = 3
RETRY_SLEEP_SEC = 5

def _with_retry(label: str, fn, retries: int | None = None):
    retries = DEFAULT_RETRIES if retries is None else retries
    last_err = None
    for i in range(1, retries + 1):
        try:
            return fn()
        except Exception as e:
            last_err = e
            print(f"[{label}] attempt {i}/{retries} failed: {e}")
            if i < retries:
                time.sleep(RETRY_SLEEP_SEC * i)
    print(f"[{label}] gave up: {last_err}")
    return None

def fetch_poi(output):
    """下载 POI 数据"""
    print("[POI] Fetching...")
    def _run():
        tags = {
            "amenity": ["cafe", "restaurant", "school", "hospital", "bank"],
            "shop": True,
            "leisure": "park",
            "railway": "station",
            "station": "subway",
        }
        pois = ox.features_from_bbox(
            bbox=(WEST, SOUTH, EAST, NORTH),
            tags=tags,
        )
        return pois.to_crs("EPSG:4326")
    pois = _with_retry("POI", _run)
    if pois is None:
        return 0
    count = 0
    for _, row in pois.iterrows():
        if row.geometry is None or row.geometry.geom_type != "Point":
            continue
        name = str(row.get("name", "")).replace("'", "''")[:200] if row.get("name") else ""
        category = ""
        # 地铁优先映射为 subway
        if str(row.get("station", "")).lower() == "subway" or str(row.get("railway", "")) == "station":
            category = "subway"
        else:
            for tag_col in ["amenity", "shop", "leisure"]:
                val = row.get(tag_col)
                if val:
                    category = str(val)
                    break
        if not name or not category:
            continue
        lon, lat = row.geometry.x, row.geometry.y
        output.write(
            f"INSERT INTO poi (name, category, geom) VALUES "
            f"('{name}', '{category}', ST_SetSRID(ST_MakePoint({lon:.6f}, {lat:.6f}), 4326));\n"
        )
        count += 1
    print(f"[POI] {count} records written")
    return count


def fetch_roads(output):
    """下载道路数据"""
    print("[Roads] Fetching...")
    def _run():
        G = ox.graph_from_bbox(
            bbox=(NORTH, SOUTH, EAST, WEST),
            network_type="drive",
            simplify=True,
        )

        edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        return edges.to_crs("EPSG:4326")

    edges = _with_retry("Roads", _run)
    if edges is None:
        return 0
    count = 0
    seen = set()
    for _, row in edges.iterrows():
        if row.geometry is None:
            continue
        name = str(row.get("name", "")).replace("'", "''")[:200] if row.get("name") else ""
        if not name:
            # 无名道路用 osm id 占位，避免路网过稀
            name = f"road_{row.name if hasattr(row, 'name') else count}"
            name = str(name).replace("'", "''")[:200]
        key = (name, round(row.geometry.centroid.x, 5), round(row.geometry.centroid.y, 5))
        if key in seen:
            continue
        seen.add(key)

        road_type = str(row.get("highway", "tertiary"))
        if isinstance(row.get("highway"), list):
            road_type = str(row.get("highway")[0])
        speed_raw = row.get("maxspeed", 50)
        speed = int(speed_raw) if str(speed_raw).isdigit() else 50

        coords = [f"{x:.6f} {y:.6f}" for x, y in row.geometry.coords]
        if len(coords) < 2:
            continue
        linestr = f"LINESTRING({', '.join(coords)})"

        output.write(
            f"INSERT INTO roads (name, road_type, speed_limit, geom) VALUES "
            f"('{name}', '{road_type}', {speed}, ST_GeomFromText('{linestr}', 4326));\n"
        )
        count += 1
    print(f"[Roads] {count} records written")
    return count


def fetch_buildings(output, building_limit: int = 200):
    """下载建筑数据"""
    print(f"[Buildings] Fetching (limit={building_limit})...")
    def _run():
        bldgs = ox.features_from_bbox(
            bbox=(WEST, SOUTH, EAST, NORTH),
            tags={"building": True},
        )
        return bldgs.to_crs("EPSG:4326")

        count = 0
    bldgs = _with_retry("Buildings", _run)
    if bldgs is None:
        return 0

    count = 0
    for _, row in bldgs.iterrows():
        if row.geometry is None or row.geometry.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        name = str(row.get("name", "")).replace("'", "''")[:200] if row.get("name") else f"building_{count+1}"
        height = (
            float(row.get("height", 10))
            if row.get("height") and str(row.get("height")).replace(".", "").isdigit()
            else 10.0
        )
        usage = str(row.get("building", "residential"))
        levels = int(row.get("building:levels", 3)) if str(row.get("building:levels", "3")).isdigit() else 3

        geom = row.geometry
        if geom.geom_type == "MultiPolygon":
            geom = list(geom.geoms)[0]
        coords = [f"{x:.6f} {y:.6f}" for x, y in geom.exterior.coords]
        poly_text = f"POLYGON(({', '.join(coords)}))"

        output.write(
            f"INSERT INTO buildings (name, height, floors, usage, geom) VALUES "
            f"('{name}', {height}, {levels}, '{usage}', ST_GeomFromText('{poly_text}', 4326));\n"
        )
        count += 1
        if count >= building_limit:
            break

    print(f"[Buildings] {count} records written")
    return count


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch OSM data into SQL INSERT files")
    parser.add_argument(
        "--layers",
        default="poi,roads,buildings",
        help="Comma-separated: poi,roads,buildings",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output SQL path (default depends on layers)",
    )
    parser.add_argument(
        "--building-limit",
        type=int,
        default=500,
        help="Max building rows (default 500)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Network retries per layer",
    )
    return parser.parse_args()
def main():
    args = parse_args()
    global DEFAULT_RETRIES
    DEFAULT_RETRIES = args.retries
    layers = [x.strip() for x in args.layers.split(",") if x.strip()]
    script_dir = os.path.dirname(__file__)
    if args.output:
        output_path = os.path.abspath(os.path.join(script_dir, args.output) if not os.path.isabs(args.output) else args.output)
    elif layers == ["poi"]:


    with open(output_path, "w", encoding="utf-8") as f:
        f.write("-- ==========================================\n")
        f.write("-- OSM 北京朝阳区数据\n")
        f.write("-- 自动采集脚本: database/scripts/fetch_osm.py\n")
        f.write(f"-- layers: {','.join(layers)}\n")
        f.write("-- ==========================================\n\n")

        if "poi" in layers:
            totals["poi"] = fetch_poi(f)
            f.write("\n")
        if "roads" in layers:
            totals["roads"] = fetch_roads(f)
            f.write("\n")
        if "buildings" in layers:
            totals["buildings"] = fetch_buildings(f, building_limit=args.building_limit)
            f.write("\n")

        f.write("\n-- Done\n")

    with open(output_path, encoding="utf-8") as f:
        lines = f.readlines()
    print(f"\n✅ Written {len(lines)} lines to {output_path}")
    print(f"   totals: {totals}")


if __name__ == "__main__":
    main()
