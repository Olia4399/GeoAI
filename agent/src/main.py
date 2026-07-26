"""
GeoAI Spatial Agent — FastAPI 应用入口
Spatial Agent 层: LLM 意图理解 + 任务规划 + 工具调用 + 结果解释
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

# 自动加载 agent/.env 文件
from dotenv import load_dotenv

_env_file = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_file)
print(f"[agent] Loaded env from: {_env_file}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router as agent_router
from .api.history_routes import router as history_router


def get_spatial_service_url() -> str:
    return os.getenv("SPATIAL_SERVICE_URL", "http://localhost:8002")


def get_llm_config() -> dict:
    return {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "model": os.getenv("LLM_MODEL", "gpt-4o"),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[agent] Spatial Service URL: {get_spatial_service_url()}")
    llm = get_llm_config()
    print(f"[agent] LLM: {llm['model']} @ {llm['base_url']}")
    yield


app = FastAPI(
    title="GeoAI Spatial Agent",
    description="Spatial Agent 层 — 自然语言空间分析调度",
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

app.include_router(agent_router, prefix="/api/agent")
app.include_router(history_router, prefix="/api/agent")
