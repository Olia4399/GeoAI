# GeoAI Phase 1 — Foundation 执行方案

> 基于《第一章 项目总体设计》和《第二章 Agent 总体架构设计》
>
> 目标：搭建五层架构骨架，实现"用户输入自然语言 → Agent 解析 → 调用 GIS 服务 → 返回 GeoJSON → 地图展示"的最小闭环。

## 已完成

- [x] 项目基础设施（.gitignore, README, CLAUDE.md, .env.example）
- [x] 空间数据层（PostGIS 初始化 SQL，含测试数据）
- [x] 空间能力服务层（FastAPI + buffer + distance）
- [x] Spatial Agent 层（LangChain + LangGraph + 2 Tools）
- [x] 用户交互层（React + Mapbox + Cesium + ChatPanel）
- [x] Docker Compose 一键编排

## 技术栈

| 层级 | 技术 | 端口 |
|------|------|------|
| 前端 | React 19, TypeScript, Mapbox GL JS, CesiumJS, Vite, Zustand | 5173 |
| Agent | LangChain, LangGraph, FastAPI, OpenAI 兼容 API | 8001 |
| 空间服务 | FastAPI, GeoPandas, Shapely, PyProj | 8002 |
| 数据库 | PostgreSQL 16, PostGIS 3.4 | 5432 |
| 部署 | Docker Compose | — |

## 项目结构

```
GeoAI/
├── plan/                          # 执行方案
│   └── phase-1-foundation.md
├── frontend/                      # 用户交互层 (React + Mapbox + Cesium)
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/            # AppLayout, Header
│   │   │   ├── map/               # MapView, CesiumView
│   │   │   └── chat/              # ChatPanel, MessageList
│   │   ├── services/              # api.ts, agent.ts
│   │   ├── store/                 # Zustand store
│   │   └── types/
│   ├── package.json, tsconfig.json, vite.config.ts
│   └── index.html
├── agent/                         # Spatial Agent 层 (LangChain + LangGraph)
│   ├── src/
│   │   ├── intent/parser.py       # LLM 意图解析 (Structured Output)
│   │   ├── planning/planner.py    # ReAct Agent 任务规划
│   │   ├── tools/                 # Tool 注册中心 + 空间 Tool 定义
│   │   └── reasoning/interpreter.py  # LLM 结果解释
│   ├── api/routes.py              # POST /api/agent/query
│   └── pyproject.toml
├── spatial/                       # 空间能力服务层 (FastAPI)
│   ├── src/
│   │   ├── api/                   # health, spatial_routes
│   │   ├── services/              # buffer, distance, density
│   │   └── models/schemas.py
│   └── pyproject.toml
├── database/
│   └── init/01-init-spatial.sql   # PostGIS 扩展 + 表 + 测试数据
├── docker/
│   ├── docker-compose.yml         # 一键启动 4 服务
│   ├── Dockerfile.spatial/agent/frontend
│   └── .env.example
├── data/                          # 数据目录 (raw/processed/samples)
├── .gitignore, README.md, CLAUDE.md
```

## 启动方式

### 本地开发

```bash
# 1. 数据库
cd docker && docker compose up -d postgis

# 2. Spatial Service (8002)
cd spatial && uv sync && uv run uvicorn src.main:app --reload --port 8002

# 3. Agent Service (8001)
cd agent && uv sync && uv run uvicorn src.main:app --reload --port 8001

# 4. Frontend (5173)
cd frontend && pnpm install && pnpm dev
```

### Docker 一键部署

```bash
cd docker
cp .env.example .env   # 编辑填入 API Keys
docker compose up -d
```

## 当前 API 清单

### Spatial Service (:8002)
| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/api/health` | GET | 健康检查 + DB 状态 | ✅ |
| `/api/spatial/buffer` | POST | 缓冲区分析 | ✅ |
| `/api/spatial/distance` | POST | 距离计算 | ✅ |
| `/api/spatial/route` | POST | 路径规划 | 🔜 Phase 2 |
| `/api/spatial/overlay` | POST | 空间叠加 | 🔜 Phase 2 |
| `/api/spatial/suitability` | POST | 适宜性评价 | 🔜 Phase 2 |

### Agent Service (:8001)
| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/api/agent/health` | GET | 健康检查 | ✅ |
| `/api/agent/query` | POST | 自然语言空间查询 | ✅ |

## 验证步骤

### 1. 验证 Spatial Service

```bash
# 健康检查
curl http://localhost:8002/api/health

# 缓冲区分析
curl -X POST http://localhost:8002/api/spatial/buffer \
  -H "Content-Type: application/json" \
  -d '{"geometry": {"type":"Point","coordinates":[116.458,39.908]}, "distance": 500}'

# 距离计算
curl -X POST http://localhost:8002/api/spatial/distance \
  -H "Content-Type: application/json" \
  -d '{"source":{"type":"Point","coordinates":[116.458,39.908]},"target":{"type":"Point","coordinates":[116.468,39.906]}}'
```

### 2. 验证 Agent Service

```bash
curl -X POST http://localhost:8001/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "计算北京国贸周边500米的缓冲区"}'
```

### 3. 验证前端

打开 http://localhost:5173，在输入框输入空间分析问题。

## Phase 2 规划方向

1. 完善 6 个核心 GIS Tool（route, overlay, density, suitability）
2. 多步 Agent 工作流（选址分析完整链路）
3. PostGIS 集成（Agent 直接空间查询）
4. 地图交互输入（框选区域 → Agent 分析）
5. 3D Cesium 分析结果叠加

## Phase 3 规划方向

1. 遥感 AI 识别模块（PyTorch + YOLO/SAM）
2. 时空变化分析
3. 智能报告生成（RAG + 空间知识库）
4. 多 Agent 协作
