"""健康检查接口"""

from fastapi import APIRouter

from ..main import db_conn

router = APIRouter()


@router.get("/health")
def health_check():
    """检查服务健康状态，包含数据库连接"""
    db_status = "connected" if db_conn and not db_conn.closed else "disconnected"
    return {
        "status": "ok",
        "service": "geoai-spatial",
        "version": "0.1.0",
        "database": db_status,
    }
