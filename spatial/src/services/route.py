"""路径规划服务

使用 OSMnx 下载局部路网 + NetworkX 最短路径计算。
Phase 2: 步行路径。驾车路径后续通过 GraphHopper/OSRM 实现。
"""

from shapely.geometry import Point, LineString, mapping


def compute_route(
    origin: list[float],
    destination: list[float],
    mode: str = "walk",
) -> dict:
    """
    计算两点间的最短路径。

    Args:
        origin: [lon, lat] 起点坐标
        destination: [lon, lat] 终点坐标
        mode: walk | drive (Phase 2 仅 walk)

    Returns:
        GeoJSON FeatureCollection，包含路径 LineString
    """
    try:
        import osmnx as ox
        import networkx as nx
    except ImportError:
        raise RuntimeError("osmnx/networkx not installed. Run: uv add osmnx networkx")

    if mode not in ("walk", "drive"):
        raise ValueError(f"Mode '{mode}' not supported. Use 'walk' or 'drive'")

    origin_point = Point(origin[0], origin[1])
    dest_point = Point(destination[0], destination[1])

    # 计算包围盒并缓冲
    min_lon = min(origin[0], destination[0])
    max_lon = max(origin[0], destination[0])
    min_lat = min(origin[1], destination[1])
    max_lat = min(origin[1], destination[1])
    margin = 0.02  # ~2km
    bbox = (max_lat + margin, min_lat - margin, max_lon + margin, min_lon - margin)  # north, south, east, west

    # 下载路网
    network_type = "walk" if mode == "walk" else "drive"
    try:
        G = ox.graph_from_bbox(bbox=bbox, network_type=network_type, simplify=True)
    except Exception:
        # 回退: 使用更小的区域
        G = ox.graph_from_point(
            ((origin[1] + destination[1]) / 2, (origin[0] + destination[0]) / 2),
            dist=3000,
            network_type=network_type,
            simplify=True,
        )

    if G.number_of_nodes() == 0:
        raise ValueError("No road network found in this area")

    # 找到最近的节点
    orig_node = ox.distance.nearest_nodes(G, origin[0], origin[1])
    dest_node = ox.distance.nearest_nodes(G, destination[0], destination[1])

    # 最短路径
    route_nodes = nx.shortest_path(G, orig_node, dest_node, weight="length")

    # 提取坐标
    route_coords = []
    for u, v in zip(route_nodes[:-1], route_nodes[1:]):
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            edge = edge_data[0] if isinstance(edge_data, dict) and 0 in edge_data else edge_data
            if "geometry" in edge:
                route_coords.extend(list(edge["geometry"].coords))
            else:
                route_coords.append((G.nodes[u]["x"], G.nodes[u]["y"]))

    # 加最后一个点
    route_coords.append((G.nodes[dest_node]["x"], G.nodes[dest_node]["y"]))

    # 去重
    seen = set()
    unique_coords = []
    for c in route_coords:
        key = (round(c[0], 7), round(c[1], 7))
        if key not in seen:
            seen.add(key)
            unique_coords.append(list(c))

    if len(unique_coords) < 2:
        raise ValueError("Could not compute a valid route")

    # 计算总长度
    line = LineString([(c[0], c[1]) for c in unique_coords])
    # 粗略距离: 用 3857 算, 简单转换
    from pyproj import Transformer
    from shapely.ops import transform

    t = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    length_m = transform(t.transform, line).length

    feature = {
        "type": "Feature",
        "properties": {
            "mode": mode,
            "distance_meters": round(length_m, 1),
            "nodes": len(unique_coords),
        },
        "geometry": mapping(line),
    }

    return {
        "type": "FeatureCollection",
        "features": [feature],
    }
