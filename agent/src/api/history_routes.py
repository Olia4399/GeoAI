"""分析历史 API 路由"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..storage.history import save_analysis, list_analyses, get_analysis, delete_analysis

router = APIRouter()


class CompareRequest(BaseModel):
    id_a: str
    id_b: str


@router.get("/history")
def history_list(limit: int = 20, offset: int = 0):
    """列出历史分析"""
    return {
        "total": len(list_analyses(1000)),
        "items": list_analyses(limit, offset),
    }


@router.get("/history/{analysis_id}")
def history_detail(analysis_id: str):
    """查看某次分析详情"""
    item = get_analysis(analysis_id)
    if not item:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return item


@router.delete("/history/{analysis_id}")
def history_delete(analysis_id: str):
    """删除某次分析"""
    ok = delete_analysis(analysis_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"status": "deleted", "id": analysis_id}


@router.post("/compare")
def compare_analyses(req: CompareRequest):
    """对比两次分析"""
    a = get_analysis(req.id_a)
    b = get_analysis(req.id_b)
    if not a or not b:
        raise HTTPException(status_code=404, detail="One or both analyses not found")
    return {
        "analysis_a": {"id": a["id"], "query": a["query"], "intent": a["intent"]},
        "analysis_b": {"id": b["id"], "query": b["query"], "intent": b["intent"]},
    }
