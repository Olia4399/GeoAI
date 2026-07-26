"""空间分析 API 路由"""

from fastapi import APIRouter, HTTPException

from ..models.schemas import (
    BufferRequest,
    BufferResponse,
    DistanceRequest,
    DistanceResponse,
    SpatialError,
)
from ..services.buffer import compute_buffer
from ..services.distance import compute_distance

router = APIRouter()


@router.post(
    "/buffer",
    response_model=BufferResponse,
    summary="缓冲区分析",
    description="计算空间对象指定距离的缓冲区范围，返回 GeoJSON FeatureCollection",
)
def buffer_analysis(req: BufferRequest):
    try:
        result = compute_buffer(req.geometry, req.distance)
        return BufferResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Buffer analysis failed: {e}")


@router.post(
    "/distance",
    response_model=DistanceResponse,
    summary="距离计算",
    description="计算两个空间对象之间的距离 (米)",
)
def distance_analysis(req: DistanceRequest):
    try:
        result = compute_distance(req.source, req.target)
        return DistanceResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Distance analysis failed: {e}")


# ---- Phase 1 接口桩 ----

@router.post("/route", summary="路径规划 (Phase 2 实现)")
def route_analysis():
    raise HTTPException(status_code=501, detail="Route analysis — coming in Phase 2")


@router.post("/overlay", summary="空间叠加分析 (Phase 2 实现)")
def overlay_analysis():
    raise HTTPException(status_code=501, detail="Overlay analysis — coming in Phase 2")


@router.post("/suitability", summary="适宜性评价 (Phase 2 实现)")
def suitability_analysis():
    raise HTTPException(status_code=501, detail="Suitability analysis — coming in Phase 2")
