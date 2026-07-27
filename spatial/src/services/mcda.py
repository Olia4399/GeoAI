"""多准则决策分析 (MCDA) 服务

对离散候选方案做多准则评价与排序。
支持: weighted_sum (WSM)、weighted_product (WPM)、topsis。
与 suitability（空间加权叠加栅格）互补：本模块面向方案层 ranking。
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np


Method = Literal["weighted_sum", "weighted_product", "topsis"]


def _criterion_value(props: dict, name: str) -> float | None:
    if name not in props or props[name] is None:
        return None
    try:
        return float(props[name])
    except (TypeError, ValueError):
        return None


def _normalize_weights(criteria: list[dict]) -> list[dict]:
    cleaned = []
    for c in criteria:
        name = c.get("name")
        if not name:
            raise ValueError("Each criterion must have a name")
        weight = float(c.get("weight", 1.0))
        direction = c.get("direction", "benefit")
        if direction not in ("benefit", "cost"):
            raise ValueError(f"Invalid direction for '{name}': use benefit | cost")
        cleaned.append({"name": name, "weight": weight, "direction": direction})
    total = sum(c["weight"] for c in cleaned)
    if total <= 0:
        raise ValueError("Sum of criterion weights must be > 0")
    for c in cleaned:
        c["weight"] = c["weight"] / total
    return cleaned


def _build_matrix(
    alternatives: list[dict],
    criteria: list[dict],
) -> tuple[np.ndarray, list[dict], list[int]]:
    """返回决策矩阵 X[n,m]、有效方案、原始索引。"""
    rows: list[list[float]] = []
    kept: list[dict] = []
    indices: list[int] = []

    for idx, feat in enumerate(alternatives):
        props = feat.get("properties") or {}
        row: list[float] = []
        ok = True
        for c in criteria:
            val = _criterion_value(props, c["name"])
            if val is None:
                ok = False
                break
            row.append(val)
        if ok:
            rows.append(row)
            kept.append(feat)
            indices.append(idx)

    if not rows:
        raise ValueError("No alternatives with complete criterion values")
    return np.asarray(rows, dtype=np.float64), kept, indices


def _minmax_normalize(X: np.ndarray, criteria: list[dict]) -> np.ndarray:
    """按 benefit/cost 做 min-max 归一化到 [0,1]，越高越好。"""
    N = np.zeros_like(X)
    for j, c in enumerate(criteria):
        col = X[:, j]
        cmin, cmax = float(col.min()), float(col.max())
        if abs(cmax - cmin) < 1e-12:
            N[:, j] = 1.0
            continue
        if c["direction"] == "benefit":
            N[:, j] = (col - cmin) / (cmax - cmin)
        else:
            N[:, j] = (cmax - col) / (cmax - cmin)
    return N


def _weighted_sum(N: np.ndarray, weights: np.ndarray) -> np.ndarray:
    return N @ weights


def _weighted_product(N: np.ndarray, weights: np.ndarray) -> np.ndarray:
    # 避免 0^w：用极小正数
    safe = np.clip(N, 1e-12, None)
    return np.prod(safe ** weights, axis=1)


def _topsis(X: np.ndarray, criteria: list[dict], weights: np.ndarray) -> np.ndarray:
    """向量归一化 + 理想解距离。"""
    denom = np.sqrt((X**2).sum(axis=0))
    denom = np.where(denom < 1e-12, 1.0, denom)
    R = X / denom
    V = R * weights

    ideal_best = np.zeros(V.shape[1])
    ideal_worst = np.zeros(V.shape[1])
    for j, c in enumerate(criteria):
        if c["direction"] == "benefit":
            ideal_best[j] = V[:, j].max()
            ideal_worst[j] = V[:, j].min()
        else:
            ideal_best[j] = V[:, j].min()
            ideal_worst[j] = V[:, j].max()

    d_best = np.sqrt(((V - ideal_best) ** 2).sum(axis=1))
    d_worst = np.sqrt(((V - ideal_worst) ** 2).sum(axis=1))
    return d_worst / np.clip(d_best + d_worst, 1e-12, None)


def compute_mcda(
    alternatives: list[dict],
    criteria: list[dict],
    method: Method = "topsis",
) -> dict[str, Any]:
    """
    多准则决策排序。

    Args:
        alternatives: GeoJSON features；properties 中需包含各准则数值字段
        criteria: [{name, weight, direction: benefit|cost}, ...]
        method: weighted_sum | weighted_product | topsis

    Returns:
        FeatureCollection：原几何 + score / rank / method；meta 含方法说明
    """
    if method not in ("weighted_sum", "weighted_product", "topsis"):
        raise ValueError("method must be weighted_sum | weighted_product | topsis")
    if not alternatives:
        raise ValueError("alternatives must not be empty")
    if not criteria:
        raise ValueError("criteria must not be empty")

    crit = _normalize_weights(criteria)
    X, kept, indices = _build_matrix(alternatives, crit)
    weights = np.array([c["weight"] for c in crit], dtype=np.float64)

    if method == "topsis":
        scores = _topsis(X, crit, weights)
    else:
        N = _minmax_normalize(X, crit)
        if method == "weighted_sum":
            scores = _weighted_sum(N, weights)
        else:
            scores = _weighted_product(N, weights)

    order = np.argsort(-scores)  # 降序
    rank_of = {int(order[i]): i + 1 for i in range(len(order))}

    features: list[dict] = []
    for local_i, feat in enumerate(kept):
        props = dict(feat.get("properties") or {})
        props.update(
            {
                "mcda_score": round(float(scores[local_i]), 6),
                "mcda_rank": rank_of[local_i],
                "mcda_method": method,
                "alternative_index": indices[local_i],
            }
        )
        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": feat.get("geometry"),
            }
        )

    features.sort(key=lambda f: f["properties"]["mcda_rank"])

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "method": method,
            "criteria": crit,
            "alternative_count": len(features),
            "note": "Higher mcda_score is better. Suitability Analysis is grid weighted-overlay; MCDA ranks discrete alternatives.",
        },
    }
