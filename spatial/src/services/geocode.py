"""地理编码服务 — 地名 → WGS84 坐标（分级降级）

L1 districts 表（区级精确/前缀匹配，如 "朝阳" → "朝阳区"）
L2 POI 名称锚点：精确/前缀（"国贸" → "国贸站"）
L3a 百度地理编码 API（BD09 → WGS84；含置信度过滤，低置信降级打点按未收录处理）
L3b 高德地理编码 API（GCJ02 → WGS84；百度无额度/不可用时的备援，需配置 AMAP_KEY）
L2' POI"包含"弱匹配兜底（低置信、带提示，仅当以上全部失败，如 "天安门" → 某旅行社名）

返回结构区分"未收录"（found=False，业务正常）与"服务故障"（note 说明），
让上层 Agent 决定是否用 LLM 知识坐标兜底。
"""

import math
import os

import requests

from .. import database
from ..database import get_db_url

import psycopg2
import psycopg2.extras


# ============================================================
# 坐标系转换：BD09 → GCJ02 → WGS84
# 百度返回 BD09（火星坐标加密体系），库内数据是 WGS84，必须转换后才能对齐
# ============================================================

_A = 6378245.0  # 克拉索夫斯基椭球长半轴
_EE = 0.00669342162296594323  # 偏心率平方


def _out_of_china(lng: float, lat: float) -> bool:
    return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)


def _transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320.0 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lng: float, lat: float) -> tuple[float, float]:
    """WGS84 → GCJ02 正变换（用于反解的迭代）"""
    if _out_of_china(lng, lat):
        return lng, lat
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - _EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (_A / sqrtmagic * math.cos(radlat) * math.pi)
    return lng + dlng, lat + dlat


def gcj02_to_wgs84(lng: float, lat: float) -> tuple[float, float]:
    """GCJ02 → WGS84：迭代逼近正变换的反解（3 轮迭代精度 ~0.1m 级）"""
    if _out_of_china(lng, lat):
        return lng, lat
    wgs_lng, wgs_lat = lng, lat
    for _ in range(3):
        gcj_lng, gcj_lat = wgs84_to_gcj02(wgs_lng, wgs_lat)
        wgs_lng -= gcj_lng - lng
        wgs_lat -= gcj_lat - lat
    return wgs_lng, wgs_lat


def bd09_to_wgs84(lng: float, lat: float) -> tuple[float, float]:
    """BD09 → GCJ02 → WGS84（百度坐标系转国标 WGS84）"""
    x = lng - 0.0065
    y = lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * math.pi * 3000.0 / 180.0)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * math.pi * 3000.0 / 180.0)
    gcj_lng = z * math.cos(theta)
    gcj_lat = z * math.sin(theta)
    return gcj02_to_wgs84(gcj_lng, gcj_lat)


# ============================================================
# L1 / L2 / L3 分级地理编码
# ============================================================

def _get_conn():
    conn = database.db_conn
    if not conn or conn.closed:
        conn = psycopg2.connect(get_db_url())
    return conn


def _geocode_districts(name: str) -> dict | None:
    """L1: 区级名称（districts 表），支持精确与"朝阳"→"朝阳区"前缀匹配"""
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT name,
               ST_X(ST_PointOnSurface(geom)) AS lon,
               ST_Y(ST_PointOnSurface(geom)) AS lat
        FROM districts
        WHERE name = %s OR name LIKE %s || '%%'
        ORDER BY CASE WHEN name = %s THEN 0 ELSE 1 END, length(name)
        LIMIT 1
        """,
        (name, name, name),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return {
        "source": "districts",
        "matched_name": row["name"],
        "geometry": {"type": "Point", "coordinates": [round(row["lon"], 6), round(row["lat"], 6)]},
    }


def _geocode_poi(name: str, allow_contains: bool = False) -> dict | None:
    """L2: POI 名称锚点，排序 精确 > 前缀（同级取最短名，区域名优先短锚点）。

    默认只做 精确/前缀 匹配（高置信，如 "国贸" → "国贸站"）；
    allow_contains=True 时才允许"名称包含"的弱匹配（最后兜底，坐标可能偏离目标）。
    """
    if allow_contains:
        where = "name = %s OR name LIKE %s || '%%' OR name LIKE '%%' || %s || '%%'"
        rank = "CASE WHEN name = %s THEN 0 WHEN name LIKE %s || '%%' THEN 1 ELSE 2 END"
        params: tuple = (name, name, name, name, name)
    else:
        where = "name = %s OR name LIKE %s || '%%'"
        rank = "CASE WHEN name = %s THEN 0 ELSE 1 END"
        params = (name, name, name)

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        f"""
        SELECT name, category, ST_AsGeoJSON(geom)::json AS geometry
        FROM poi
        WHERE {where}
        ORDER BY {rank}, length(name)
        LIMIT 1
        """,
        params,
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return {
        "source": "poi",
        "matched_name": row["name"],
        "geometry": row["geometry"],
    }


def _geocode_baidu(name: str, city: str) -> tuple[dict | None, str | None]:
    """L3: 百度地理编码（BD09 → WGS84）。返回 (结果|None, 错误备注|None)"""
    ak = os.getenv("BAIDU_MAP_AK", "").strip()
    if not ak:
        return None, "未配置 BAIDU_MAP_AK，跳过百度地理编码"
    try:
        resp = requests.get(
            "https://api.map.baidu.com/geocoding/v3/",
            params={"address": name, "output": "json", "ak": ak, "city": city},
            timeout=10,
        )
        data = resp.json()
    except Exception as e:
        return None, f"百度 API 请求失败: {e}"

    if data.get("status") != 0:
        # status 非 0 = AK/配额/服务问题（区别于"未收录"）
        return None, f"百度 API 异常 status={data.get('status')} message={data.get('message', data.get('msg', ''))}"

    result = data.get("result") or {}
    loc = result.get("location") or {}
    if not loc.get("lng"):
        return None, None  # 正常返回但无结果 → 确实未收录

    confidence = result.get("confidence") or 0
    if confidence < 30:
        # 百度对无意义输入会"降级打点"（如落到城市中心，confidence≈20, level=城市）→ 按未收录处理
        return None, f"百度匹配置信度过低已丢弃 (confidence={confidence}, level={result.get('level')})"

    lng, lat = bd09_to_wgs84(float(loc["lng"]), float(loc["lat"]))
    hit = {
        "source": "baidu",
        "matched_name": name,
        "geometry": {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]},
        "confidence": confidence,
    }
    if confidence < 60:
        hit["_note"] = f"百度匹配置信度 {confidence}（{result.get('level')}），坐标为近似"
    return hit, None


def _geocode_amap(name: str, city: str) -> tuple[dict | None, str | None]:
    """L3b: 高德地理编码（GCJ02 → WGS84）。百度不可用/无额度时的备援。返回 (结果|None, 错误备注|None)"""
    key = os.getenv("AMAP_KEY", "").strip()
    if not key:
        return None, None  # 未配置：静默跳过（不算故障）
    try:
        resp = requests.get(
            "https://restapi.amap.com/v3/geocode/geo",
            params={"address": name, "city": city, "key": key},
            timeout=10,
        )
        data = resp.json()
    except Exception as e:
        return None, f"高德 API 请求失败: {e}"

    if data.get("status") != "1":
        # 高德的 status/info 是字符串（"1"/"0"），区别于百度的数字 status
        return None, f"高德 API 异常 status={data.get('status')} info={data.get('info')}"

    geocodes = data.get("geocodes") or []
    if not geocodes:
        return None, None  # 无结果 → 确实未收录

    top = geocodes[0]
    try:
        gcj_lng, gcj_lat = (float(x) for x in str(top.get("location", "")).split(","))
    except Exception:
        return None, None

    lng, lat = gcj02_to_wgs84(gcj_lng, gcj_lat)
    hit = {
        "source": "amap",
        "matched_name": name,
        "geometry": {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]},
        "level": top.get("level"),
    }
    if top.get("level") in ("省", "城市", "区县"):
        hit["_note"] = f"高德匹配为{top.get('level')}级，坐标为近似"
    return hit, None


def geocode(name: str, city: str | None = None) -> dict:
    """分级地理编码：L1 districts → L2 poi → L3 百度。

    Returns:
        {"found": bool, "source": "districts|poi|baidu"|None, "matched_name": str|None,
         "geometry": WGS84 GeoJSON Point|None, "note": str|None}
        found=False 表示未收录（业务正常返回）；服务侧异常写入 note。
    """
    name = (name or "").strip()
    if not name:
        return {"found": False, "source": None, "matched_name": None, "geometry": None, "note": "地名为空"}

    city = city or os.getenv("GEOCODE_CITY", "北京市")

    # L1 区级名称（高置信）
    hit = _geocode_districts(name)
    if hit:
        return {"found": True, "note": None, **hit}

    # L2 POI 锚点：精确/前缀（高置信，如 "国贸" → "国贸站"）
    hit = _geocode_poi(name)
    if hit:
        return {"found": True, "note": None, **hit}

    # L3a 百度（BD09→WGS84，含置信度过滤）
    hit, err = _geocode_baidu(name, city)
    if hit:
        note = hit.pop("_note", None)
        return {"found": True, "note": note, **hit}

    # L3b 高德（GCJ02→WGS84；百度无额度/不可用/低置信时的备援）
    hit, amap_err = _geocode_amap(name, city)
    if hit:
        note = hit.pop("_note", None)
        return {"found": True, "note": note, **hit}

    # L2' 兜底：POI 名称"包含"弱匹配（低置信，带提示）
    hit = _geocode_poi(name, allow_contains=True)
    if hit:
        return {
            "found": True,
            "note": "POI 名称包含匹配（弱锚点，坐标可能偏离目标）",
            **hit,
        }

    notes = "; ".join(n for n in (err, amap_err) if n)
    return {
        "found": False,
        "source": None,
        "matched_name": None,
        "geometry": None,
        "note": notes or None,  # None = 确实未收录；有值 = 上游异常（AK/网络/配额/低置信丢弃）
    }
