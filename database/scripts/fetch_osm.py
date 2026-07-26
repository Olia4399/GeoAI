"""
OSM 数据采集脚本 — 下载北京朝阳区道路/建筑/POI 并生成 SQL INSERT。

使用 OSMnx 从 OpenStreetMap 下载数据。
输出: database/init/02-osm-chaoyang.sql
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    import osmnx as ox
except ImportError:
    print("Please install osmnx: uv add osmnx")
    sys.exit(1)

# 朝阳区坐标 (粗略范围)
NORTH, SOUTH = 40.01, 39.82
EAST, WEST = 116.60, 116.35


def fetch_poi(output):
    """下载 POI 数据"""
    print("[POI] Fetching...")
    tags = {
        "amenity": ["cafe", "restaurant", "school", "hospital", "bank"],
        "shop": True,
        "leisure": "park",
    }
    try:
        pois = ox.features_from_bbox(
            bbox=(WEST, SOUTH, EAST, NORTH),
            tags=tags,
        )
        pois = pois.to_crs("EPSG:4326")

        count = 0
        for _, row in pois.iterrows():
            if row.geometry is None or row.geometry.geom_type != "Point":
                continue
            name = str(row.get("name", "")).replace("'", "''")[:200] if row.get("name") else ""
            category = ""
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
    except Exception as e:
        print(f"[POI] Error: {e}")


def fetch_roads(output):
    """下载道路数据"""
    print("[Roads] Fetching...")
    try:
        G = ox.graph_from_bbox(
            bbox=(NORTH, SOUTH, EAST, WEST),
            network_type="drive",
            simplify=True,
        )

        edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        edges = edges.to_crs("EPSG:4326")

        count = 0
        seen = set()
        for _, row in edges.iterrows():
            if row.geometry is None:
                continue
            name = str(row.get("name", "")).replace("'", "''")[:200] if row.get("name") else ""
            if not name or name in seen:
                continue
            seen.add(name)

            road_type = str(row.get("highway", "tertiary"))
            speed = int(row.get("maxspeed", 50)) if str(row.get("maxspeed", "0")).isdigit() else 50

            coords = []
            for x, y in row.geometry.coords:
                coords.append(f"{x:.6f} {y:.6f}")
            linestr = f"LINESTRING({', '.join(coords)})"

            output.write(
                f"INSERT INTO roads (name, road_type, speed_limit, geom) VALUES "
                f"('{name}', '{road_type}', {speed}, ST_GeomFromText('{linestr}', 4326));\n"
            )
            count += 1

        print(f"[Roads] {count} records written")
    except Exception as e:
        print(f"[Roads] Error: {e}")


def fetch_buildings(output):
    """下载建筑数据"""
    print("[Buildings] Fetching...")
    try:
        bldgs = ox.features_from_bbox(
            bbox=(WEST, SOUTH, EAST, NORTH),
            tags={"building": True},
        )
        bldgs = bldgs.to_crs("EPSG:4326")

        count = 0
        for _, row in bldgs.iterrows():
            if row.geometry is None or row.geometry.geom_type not in ("Polygon", "MultiPolygon"):
                continue
            name = str(row.get("name", "")).replace("'", "''")[:200] if row.get("name") else f"building_{count+1}"
            height = float(row.get("height", 10)) if row.get("height") and str(row.get("height")).replace(".", "").isdigit() else 10.0
            usage = str(row.get("building", "residential"))
            levels = int(row.get("building:levels", 3)) if str(row.get("building:levels", "3")).isdigit() else 3

            coords = []
            geom = row.geometry
            if geom.geom_type == "MultiPolygon":
                geom = list(geom.geoms)[0]  # 取第一个Polygon
            for x, y in geom.exterior.coords:
                coords.append(f"{x:.6f} {y:.6f}")
            poly_text = f"POLYGON(({', '.join(coords)}))"

            output.write(
                f"INSERT INTO buildings (name, height, floors, usage, geom) VALUES "
                f"('{name}', {height}, {levels}, '{usage}', ST_GeomFromText('{poly_text}', 4326));\n"
            )
            count += 1

            if count >= 200:  # 建筑太多会爆 SQL 文件，限制 200
                break

        print(f"[Buildings] {count} records written")
    except Exception as e:
        print(f"[Buildings] Error: {e}")


def main():
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "init", "02-osm-chaoyang.sql"
    )
    output_path = os.path.abspath(output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("-- ==========================================\n")
        f.write("-- OSM 北京朝阳区数据\n")
        f.write("-- 自动采集脚本: database/scripts/fetch_osm.py\n")
        f.write("-- ==========================================\n\n")

        fetch_poi(f)
        f.write("\n")
        fetch_roads(f)
        f.write("\n")
        fetch_buildings(f)

        f.write("\n-- Done\n")

    # 统计行数
    with open(output_path) as f:
        lines = f.readlines()
    print(f"\n✅ Written {len(lines)} lines to {output_path}")


if __name__ == "__main__":
    main()
