# GeoAI 城市空间智能分析平台

基于大语言模型 Agent、空间数据库和 WebGIS 技术的城市空间智能分析平台。

## 系统架构

```
┌──────────────────────────────┐
│          用户交互层            │
│ React + Cesium + Mapbox       │
│ 自然语言输入 / 地图交互        │
└───────────────▲──────────────┘
                │
┌───────────────┴──────────────┐
│        Spatial Agent层        │
│ LLM + MCP + Function Calling  │
│ 意图识别 / 任务规划 / 工具调用 │
└───────────────▲──────────────┘
                │
┌───────────────┴──────────────┐
│        空间能力服务层          │
│ Python GIS Engine             │
│ 空间分析 / 遥感分析 / AI模型   │
└───────────────▲──────────────┘
                │
┌───────────────┴──────────────┐
│        空间数据层              │
│ PostgreSQL + PostGIS          │
│ GeoServer                     │
│ Raster / Vector Data          │
└───────────────▲──────────────┘
                │
┌───────────────┴──────────────┐
│        数据采集层              │
│ OSM / 遥感 / 点云 / IoT       │
└──────────────────────────────┘
```

## 技术栈

| 层级     | 技术                                               |
| -------- | -------------------------------------------------- |
| 前端     | React 19, TypeScript, Mapbox GL JS, CesiumJS, Vite |
| Agent    | LangChain, LangGraph, FastAPI, OpenAI 兼容 API     |
| 空间服务 | FastAPI, GeoPandas, Shapely, PySAL, Rasterio       |
| 数据库   | PostgreSQL 16, PostGIS 3.4                         |
| 部署     | Docker Compose                                     |

## 快速启动

### 前置要求

- Docker & Docker Compose
- Node.js 20+ & pnpm
- Python 3.12+ & uv
- Mapbox Token ([申请](https://account.mapbox.com/))
- Cesium Ion Token ([申请](https://ion.cesium.com/))
- LLM API Key (OpenAI 兼容)

### 一键启动

```bash
cd docker
cp .env.example .env
# 编辑 .env 填入 API Keys
docker compose up -d
```

服务端口：

- 前端：http://localhost:5173
- Agent API：http://localhost:8001
- Spatial API：http://localhost:8002
- PostGIS：localhost:5432

### 本地开发

```bash
# 数据库
cd docker && docker compose up -d postgis

# 空间服务 (8002)
cd spatial && uv sync && uv run uvicorn src.main:app --reload --port 8002

# Agent 服务 (8001)
cd agent && uv sync && uv run uvicorn src.main:app --reload --port 8001

# 前端 (5173)
cd frontend && pnpm install && pnpm dev
```

## 核心能力

1. 自然语言驱动空间分析 Agent
2. 空间分析计算引擎
3. 时空变化分析
4. 遥感 AI 识别
5. 三维城市数字孪生
6. 智能空间报告生成

## 项目结构

```
GeoAI/
├── plan/          # 执行方案
├── frontend/      # 用户交互层
├── agent/         # Spatial Agent 层
├── spatial/       # 空间能力服务层
├── database/      # 空间数据层
├── docker/        # Docker 编排
├── data/          # 数据目录
└── docs/          # 文档
```
