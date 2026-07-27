# GeoAI Phase 1 — Foundation 执行方案

> 基于《第一章 项目总体设计》和《第二章 Agent 总体架构设计》
>
> 目标：搭建五层架构骨架，实现"用户输入自然语言 → Agent 解析 → 调用 GIS 服务 → 返回 GeoJSON → 地图展示"的最小闭环。

## 已完成

- [x] 项目基础设施（.gitignore, README, CLAUDE.md, .env.example）
- [x] 空间数据层（PostGIS Docker 容器启动，3 表 + 测试数据）
- [x] 空间能力服务层（FastAPI + buffer + distance）
- [x] Spatial Agent 层（LangChain + LangGraph + 2 Tools）
- [x] 用户交互层（React + Mapbox + Cesium + ChatPanel）
- [x] Docker Compose 一键编排
- [x] DeepSeek API 配置（agent/.env）
- [x] Mapbox + Cesium Token 配置（frontend/.env.local）

## 技术栈

| 层级     | 技术                                                         | 端口 |
| -------- | ------------------------------------------------------------ | ---- |
| 前端     | React 19, TypeScript, Mapbox GL JS, CesiumJS, Vite, Zustand  | 5173 |
| Agent    | LangChain, LangGraph, FastAPI,**DeepSeek** (`deepseek-chat`) | 8001 |
| 空间服务 | FastAPI, GeoPandas, Shapely, PyProj                          | 8002 |
| 数据库   | PostgreSQL 16 + PostGIS 3.4 (Docker)                         | 5432 |
| 部署     | Docker Compose                                               | —    |

## 环境配置文件一览

| 文件                     | 用途            | 配置项                                           |
| ------------------------ | --------------- | ------------------------------------------------ |
| `agent/.env`             | Agent 本地开发  | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_MODEL` |
| `frontend/.env.local`    | 前端本地开发    | `VITE_MAPBOX_TOKEN`, `VITE_CESIUM_ION_TOKEN`     |
| `docker/.env.example`    | Docker 部署模板 | 全部变量                                         |
| `spatial/pyproject.toml` | Spatial 依赖    | FastAPI, GeoPandas, Shapely 等                   |
| `agent/pyproject.toml`   | Agent 依赖      | LangChain, LangGraph, langchain-openai 等        |

## 详细启动步骤

### 前置检查

```bash
# 确认 Docker 正在运行
docker ps

# 确认 Python 3.12+ 和 uv 可用
python --version   # 需要 ≥ 3.12
uv --version

# 确认 Node.js 和 pnpm 可用
node --version     # 需要 ≥ 20
pnpm --version
```

---

### Step 1: 启动 PostGIS 数据库

```bash
cd d:/study/GeoAI/docker

# 确保之前没有残留容器
docker compose down -v 2>/dev/null

# 启动 PostGIS（首次会拉取镜像，约 2 分钟）
docker compose up -d postgis

# 等待 healthy 状态
docker ps --filter name=geoai-postgis

# 验证数据库
docker exec geoai-postgis psql -U geoai -d geoai -c "SELECT PostGIS_Version();"
```

---

### Step 2: 启动空间能力服务 (port 8002)

```bash
cd d:/study/GeoAI/spatial

# 安装依赖（首次）
uv sync

# 启动服务
uv run uvicorn src.main:app --reload --port 8002
```

验证：

```bash
# 另一个终端
curl http://localhost:8002/api/health

# 测试缓冲区分析
curl -X POST http://localhost:8002/api/spatial/buffer \
  -H "Content-Type: application/json" \
  -d '{"geometry": {"type":"Point","coordinates":[116.458,39.908]}, "distance": 500}'
```

---

### Step 3: 启动 Spatial Agent 服务 (port 8001)

> **前提**：`agent/.env` 中已配置 DeepSeek API Key

```bash
cd d:/study/GeoAI/agent

# 安装依赖（首次）
uv sync

# 启动服务
uv run uvicorn src.main:app --reload --port 8001
```

验证：

```bash
# 另一个终端
curl http://localhost:8001/api/agent/health

# 测试空间分析（需要 ~15-30 秒，取决于 LLM 响应）
curl -X POST http://localhost:8001/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "计算北京国贸周边500米的缓冲区"}'
```

---

### Step 4: 启动前端 (port 5173)

> **前提**：`frontend/.env.local` 中已配置 Mapbox + Cesium Token

```bash
cd d:/study/GeoAI/frontend

# 安装依赖（首次）
pnpm install

# 启动开发服务器
pnpm dev
```

浏览器打开 http://localhost:5173，在聊天面板输入空间分析问题。

---

### 一键启动（Docker）

```bash
cd d:/study/GeoAI/docker
cp .env.example .env   # 编辑填入所有 Key
docker compose up -d    # 启动全部 4 个服务
```

---

## 完整启动流程图

```
Docker Desktop 启动
        │
        ▼
  postgis (:5432)    ← docker compose up -d postgis
        │
        ▼
  spatial  (:8002)   ← cd spatial  && uv run uvicorn ...
        │
        ▼
  agent    (:8001)   ← cd agent   && uv run uvicorn ...
        │               (需要 OPENAI_API_KEY)
        ▼
  frontend (:5173)   ← cd frontend && pnpm dev
                        (需要 VITE_MAPBOX_TOKEN)
```

## 当前 API 清单

### Spatial Service (:8002)

| 端点                       | 方法 | 说明                 | 状态       |
| -------------------------- | ---- | -------------------- | ---------- |
| `/api/health`              | GET  | 健康检查 + DB 状态   | ✅         |
| `/api/spatial/buffer`      | POST | 缓冲区分析 (Shapely) | ✅         |
| `/api/spatial/distance`    | POST | 距离计算 (PyProj)    | ✅         |
| `/api/spatial/route`       | POST | 路径规划             | 🔜 Phase 2 |
| `/api/spatial/overlay`     | POST | 空间叠加             | 🔜 Phase 2 |
| `/api/spatial/suitability` | POST | 适宜性评价           | 🔜 Phase 2 |

### Agent Service (:8001)

| 端点                | 方法 | 说明             | 状态 |
| ------------------- | ---- | ---------------- | ---- |
| `/api/agent/health` | GET  | 健康检查         | ✅   |
| `/api/agent/query`  | POST | 自然语言空间查询 | ✅   |

## 项目结构

```
GeoAI/
├── plan/                          # 执行方案
│   └── phase-1-foundation.md
├── frontend/                      # 用户交互层
│   ├── .env.local                 # Mapbox + Cesium Token ← 本地开发
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
├── agent/                         # Spatial Agent 层
│   ├── .env                       # DeepSeek API Key ← 本地开发
│   ├── src/
│   │   ├── intent/parser.py       # LLM 意图解析 (Structured Output)
│   │   ├── planning/planner.py    # LangGraph ReAct Agent
│   │   ├── tools/                 # Tool 注册中心 + spatial_tools
│   │   └── reasoning/interpreter.py  # LLM 结果 → 自然语言报告
│   ├── api/routes.py              # POST /api/agent/query
│   └── pyproject.toml
├── spatial/                       # 空间能力服务层
│   ├── src/
│   │   ├── api/                   # health, spatial_routes
│   │   ├── services/              # buffer, distance, density
│   │   └── models/schemas.py
│   └── pyproject.toml
├── database/
│   └── init/01-init-spatial.sql   # PostGIS 扩展 + 表 + 北京国贸测试数据
├── docker/
│   ├── docker-compose.yml         # 一键启动 4 服务
│   ├── Dockerfile.spatial/agent/frontend
│   └── .env.example              # 环境变量模板 (默认 DeepSeek)
├── data/                          # raw/processed/samples
├── .gitignore, README.md, CLAUDE.md
```

## Phase 2 规划方向

> 已由 Phase 2–5 承接，详见 `plan/phase-*.md`。

1. 完善 6 个核心 GIS Tool（route, overlay, density, suitability）
2. 多步 Agent 工作流（选址分析完整链路）
3. PostGIS 集成（Agent 直接空间查询）
4. 地图交互输入（框选区域 → Agent 分析）
5. 3D Cesium 分析结果叠加

## Phase 5 (当前)

数据底座与知识库：见 [`phase-5-data-knowledge.md`](./phase-5-data-knowledge.md) 与 [`data-collection-runbook.md`](./data-collection-runbook.md)。