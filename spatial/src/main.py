"""
GeoAI Spatial Service — FastAPI 应用入口
空间能力服务层: 提供 GIS 分析 REST API
"""

from contextlib import asynccontextmanager

import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.health import router as health_router
from .api.spatial_routes import router as spatial_router


def get_db_url() -> str:
    """获取数据库连接 URL，优先从环境变量读取"""
    import os
    return os.getenv(
        "DATABASE_URL",
        "postgresql://geoai:geoai123@localhost:5432/geoai",
    )


# 全局数据库连接 (开发阶段简单连接池)
db_conn = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期: 启动时连接数据库，关闭时断开"""
    global db_conn
    try:
        db_conn = psycopg2.connect(get_db_url())
        print(f"[spatial] Database connected: {get_db_url()}")
    except Exception as e:
        print(f"[spatial] WARNING: Database not available: {e}")
        db_conn = None
    yield
    if db_conn:
        db_conn.close()
        print("[spatial] Database connection closed")


app = FastAPI(
    title="GeoAI Spatial Service",
    description="空间能力服务层 — 缓冲区分析、距离计算、路径规划、空间叠加、密度分析、适宜性评价",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 允许前端和 Agent 调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router, prefix="/api")
app.include_router(spatial_router, prefix="/api/spatial")
