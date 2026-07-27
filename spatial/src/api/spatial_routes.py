"""空间分析 API 路由 — 核心 GIS Tool + query"""

from fastapi import APIRouter, HTTPException

from ..models.schemas import (
    BufferRequest,
    BufferResponse,
    CostDistanceRequest,
    DistanceRequest,
    DistanceResponse,
    McdaRequest,
    QueryRequest,
    QueryResponse,
    RouteRequest,
    OverlayRequest,
    DensityRequest,
    SuitabilityRequest,
    VoronoiRequest,
)
from ..services.buffer import compute_buffer
from ..services.cost_distance import compute_cost_distance
from ..services.distance import compute_distance
from ..services.mcda import compute_mcda
from ..services.query import spatial_query
from ..services.route import compute_route
from ..services.overlay import compute_overlay
from ..services.density import compute_density
from ..services.suitability import compute_suitability
from ..services.temporal import temporal_analysis as temporal_svc
from ..services.voronoi import compute_voronoi

router = APIRouter()


@router.post("/buffer", response_model=BufferResponse, summary="缓冲区分析")
def buffer_analysis(req: BufferRequest):
    try:
        result = compute_buffer(req.geometry, req.distance)
        return BufferResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Buffer analysis failed: {e}")


@router.post("/distance", response_model=DistanceResponse, summary="距离计算")
def distance_analysis(req: DistanceRequest):
    try:
        result = compute_distance(req.source, req.target)
        return DistanceResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Distance analysis failed: {e}")


@router.post("/query", response_model=QueryResponse, summary="空间数据查询")
def query_spatial(req: QueryRequest):
    """从 PostGIS 查询空间数据，返回 GeoJSON FeatureCollection"""
    try:
        result = spatial_query(
            table=req.table,
            bbox=req.bbox,
            category=req.category,
            limit=req.limit,
        )
        return QueryResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spatial query failed: {e}")


@router.post("/route", summary="路径规划")
def route_analysis(req: RouteRequest):
    try:
        result = compute_route(
            origin=req.origin,
            destination=req.destination,
            mode=req.mode,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route analysis failed: {e}")


@router.post("/overlay", summary="空间叠加分析")
def overlay_analysis(req: OverlayRequest):
    try:
        result = compute_overlay(
            layer_a=req.layer_a,
            layer_b=req.layer_b,
            operation=req.operation,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overlay analysis failed: {e}")


@router.post("/density", summary="核密度分析")
def density_analysis(req: DensityRequest):
    try:
        result = compute_density(
            points=req.points,
            bandwidth=req.bandwidth,
            resolution=req.resolution,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Density analysis failed: {e}")


@router.post("/temporal", summary="时空变化分析")
def temporal_analysis(req: QueryRequest):
    try:
        result = temporal_svc(
            table=req.table,
            bbox=req.bbox,
            category=req.category,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Temporal analysis failed: {e}")


@router.post("/suitability", summary="适宜性评价")
def suitability_analysis(req: SuitabilityRequest):
    try:
        layers = [{"name": l.name, "features": l.features} for l in req.layers]
        result = compute_suitability(
            layers=layers,
            weights=req.weights,
            grid_size=req.grid_size,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suitability analysis failed: {e}")


@router.post("/cost-distance", summary="成本距离分析")
def cost_distance_analysis(req: CostDistanceRequest):
    try:
        return compute_cost_distance(
            sources=req.sources,
            cost_features=req.cost_features,
            resolution=req.resolution,
            default_cost=req.default_cost,
            bbox=req.bbox,
            destinations=req.destinations,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cost distance analysis failed: {e}")


@router.post("/voronoi", summary="Voronoi 泰森多边形")
def voronoi_analysis(req: VoronoiRequest):
    try:
        return compute_voronoi(
            points=req.points,
            clip_boundary=req.clip_boundary,
            buffer_ratio=req.buffer_ratio,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voronoi analysis failed: {e}")


@router.post("/mcda", summary="多准则决策分析")
def mcda_analysis(req: McdaRequest):
    try:
        criteria = [c.model_dump() for c in req.criteria]
        return compute_mcda(
            alternatives=req.alternatives,
            criteria=criteria,
            method=req.method,  # type: ignore[arg-type]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCDA analysis failed: {e}")
