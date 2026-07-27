"""
GeoAI Spatial Service — FastAPI 应用入口
空间能力服务层: 提供 GIS 分析 REST API
"""

from contextlib import asynccontextmanager
from pathlib import Path

# 自动加载 spatial/.env 文件（如果存在）
from dotenv import load_dotenv

_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
    print(f"[spatial] Loaded env from: {_env_file}")

import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.health import router as health_router
from .api.spatial_routes import router as spatial_router
from .database import get_db_url
from . import database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期: 启动时连接数据库，关闭时断开"""
    try:
        database.db_conn = psycopg2.connect(get_db_url())
        print(f"[spatial] Database connected: {get_db_url()}")
    except Exception as e:
        print(f"[spatial] WARNING: Database not available: {e}")
    yield
    if database.db_conn:
        database.db_conn.close()
        print("[spatial] Database connection closed")


app = FastAPI(
    title="GeoAI Spatial Service",
    description="空间能力服务层 — 缓冲区、欧氏/网络/成本距离、叠加、核密度、Voronoi、适宜性、MCDA",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(spatial_router, prefix="/api/spatial")
