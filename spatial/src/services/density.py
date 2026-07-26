"""核密度分析服务

使用 SciPy KDE 对点集做核密度估计，生成密度等值面 GeoJSON。
"""

import numpy as np
from shapely.geometry import Point, Polygon, shape, mapping
from pyproj import Transformer


def compute_density(
    points: list[dict],
    bandwidth: float = 500,
    resolution: int = 50,
) -> dict:
    """
    对点集做核密度估计 (KDE)，生成等值面。

    Args:
        points: GeoJSON FeatureCollection 的 features 列表
        bandwidth: KDE 带宽 (米)
        resolution: 输出网格每边的像素数

    Returns:
        GeoJSON FeatureCollection，每个网格单元带 density 属性
    """
    from scipy.stats import gaussian_kde

    if not points:
        return {"type": "FeatureCollection", "features": []}

    # 提取坐标并转换到米制
    coords_4326 = []
    for pt in points:
        geom = pt.get("geometry", {})
        if geom.get("type") == "Point":
            coords_4326.append(geom["coordinates"])
        elif geom.get("type") == "Feature":
            coords_4326.append(geom["geometry"]["coordinates"])

    if len(coords_4326) < 2:
        # 少于 2 个点无法做 KDE，返回原始点
        return {"type": "FeatureCollection", "features": points}

    # WGS84 → 3857 (米制)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    coords_m = [transformer.transform(c[0], c[1]) for c in coords_4326]

    xs = np.array([c[0] for c in coords_m])
    ys = np.array([c[1] for c in coords_m])

    # KDE
    try:
        kde = gaussian_kde([xs, ys], bw_method=bandwidth / 111320.0)  # 近似转度
    except Exception:
        return {"type": "FeatureCollection", "features": points}

    # 生成评估网格
    margin = bandwidth * 2
    gx = np.linspace(xs.min() - margin, xs.max() + margin, resolution)
    gy = np.linspace(ys.min() - margin, ys.max() + margin, resolution)
    gxx, gyy = np.meshgrid(gx, gy)
    grid_coords = np.vstack([gxx.ravel(), gyy.ravel()])

    # 评估 KDE
    z = kde(grid_coords).reshape(resolution, resolution)
    # 归一化到 0-100
    if z.max() > z.min():
        z_norm = (z - z.min()) / (z.max() - z.min()) * 100
    else:
        z_norm = np.zeros_like(z)

    # 转回 WGS84 并构建网格
    t_back = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    features = []
    for i in range(resolution - 1):
        for j in range(resolution - 1):
            # 四个角点
            corners = [
                t_back.transform(gx[j], gy[i]),
                t_back.transform(gx[j + 1], gy[i]),
                t_back.transform(gx[j + 1], gy[i + 1]),
                t_back.transform(gx[j], gy[i + 1]),
            ]
            poly = Polygon([(c[0], c[1]) for c in corners])
            density_val = round(float(z_norm[i, j]), 2)

            if density_val > 1:  # 过滤极低密度
                features.append({
                    "type": "Feature",
                    "properties": {"density": density_val},
                    "geometry": mapping(poly),
                })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
