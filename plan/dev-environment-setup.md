# GeoAI 本机开发环境补齐与启动指南

> 目标机器：Windows 10/11（当前仓库路径 `D:\pack\GeoAI\GeoAI`）  
> 日期：2026-07-27  
> 关联：[`phase-1-foundation.md`](./phase-1-foundation.md)、[`README.md`](../README.md)

---

## 1. 本机现状快照（2026-07-27 实测）

| 组件 | 要求 | 本机状态 | 动作 |
|------|------|----------|------|
| Git | 任意近期版 | ✅ `2.53.0` | 无需安装 |
| Python | ≥ 3.12 | ✅ `3.12.10` | 无需安装 |
| Node.js | ≥ 20 | ✅ `v20.19.0` | 无需安装 |
| pnpm | 任意 8/9+ | ✅ `9.12.0` | 无需安装 |
| **uv** | 最新稳定版 | ❌ 未安装 | **必须安装** |
| **Docker Desktop** | 含 Compose v2 | ❌ 未安装 | **必须安装**（PostGIS 依赖） |
| WSL2 | Docker Desktop 推荐后端 | ❌ 未就绪 | 安装 Docker 时一并启用 |
| `agent/.env` | LLM Key | ❌ 缺失 | **必须创建** |
| `frontend/.env.local` | Mapbox / Cesium | ❌ 缺失 | **必须创建** |
| `docker/.env` | 一键编排用 | ❌ 缺失 | Docker 全量启动时需要 |
| `docker/.env.example` | 模板 | ❌ 仓库中缺失 | 见下文模板（已补齐） |

**结论**：语言运行时基本齐全；要跑通闭环，还需补 **Docker + uv + 3 份密钥配置**。

---

## 2. 必须补齐清单

### 2.1 系统软件

#### A. uv（Python 包管理，agent / spatial 共用）

PowerShell（当前用户）：

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

安装后**新开终端**验证：

```powershell
uv --version
```

若命令仍找不到，把 `%USERPROFILE%\.local\bin` 加入用户 PATH，或重启 IDE。

#### B. Docker Desktop（跑 PostGIS；也可一键起全栈）

1. 确认 BIOS / Windows 功能已开：
   - 虚拟化（Task Manager → 性能 → CPU → 虚拟化 = 已启用）
   - 「适用于 Linux 的 Windows 子系统」「虚拟机平台」
2. 安装 [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
3. 安装过程若提示安装 WSL2，按向导完成并重启
4. 启动 Docker Desktop，等待引擎 Ready
5. 验证：

```powershell
docker --version
docker compose version
docker ps
```

> 本项目本地开发**最低**只需容器 `postgis`；`spatial` / `agent` / `frontend` 建议用本机进程热重载开发。

#### C.（可选）WSL2 Ubuntu

仅在 Docker 安装向导要求、或希望在 Linux 子系统里跑命令时安装：

```powershell
wsl --install -d Ubuntu
```

### 2.2 第三方账号 / API Key

| Key | 用途 | 申请地址 | 落盘位置 |
|-----|------|----------|----------|
| DeepSeek / OpenAI 兼容 Key | Agent 意图解析、规划、报告 | [DeepSeek 开放平台](https://platform.deepseek.com/) 或其他兼容端点 | `agent/.env` |
| Mapbox Access Token | 2D 底图 | [Mapbox Account](https://account.mapbox.com/) | `frontend/.env.local` |
| Cesium Ion Token | 3D 地形（可空，无 Token 时 3D 降级） | [Cesium Ion](https://ion.cesium.com/) | `frontend/.env.local` |

### 2.3 配置文件模板

仓库曾声明有 `.env.example`，当前磁盘上缺失。按下表在对应路径**新建文件**（勿提交真实 Key；已在 `.gitignore`）。

#### `agent/.env`

```env
# OpenAI 兼容协议（DeepSeek 示例）
OPENAI_API_KEY=sk-你的密钥
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# 本机 spatial 服务
SPATIAL_SERVICE_URL=http://localhost:8002
```

#### `frontend/.env.local`

```env
VITE_MAPBOX_TOKEN=pk.你的_mapbox_token
VITE_CESIUM_ION_TOKEN=你的_cesium_ion_token
```

#### `docker/.env`（仅「一键 Docker 全栈」需要）

可复制同目录 `docker/.env.example`（见 §6）后改名填 Key。

#### `spatial/.env`（可选）

不配则默认连本机 PostGIS：

```env
DATABASE_URL=postgresql://geoai:geoai123@localhost:5432/geoai
```

### 2.4 首次依赖安装（装完 uv / 有 Node 后）

在 **PowerShell** 中（路径按本机仓库）：

```powershell
cd D:\pack\GeoAI\GeoAI\spatial
uv sync

cd D:\pack\GeoAI\GeoAI\agent
uv sync
# 注意：agent 含 chromadb + sentence-transformers，首次会拉较大模型/依赖，预留磁盘与时间

cd D:\pack\GeoAI\GeoAI\frontend
pnpm install
```

---

## 3. 推荐启动方式：本机四进程（日常开发）

依赖顺序：**PostGIS → spatial → agent → frontend**。

### Step 0：前置检查

```powershell
docker ps
python --version   # ≥ 3.12
uv --version
node --version     # ≥ 20
pnpm --version
```

确认已存在：`agent\.env`、`frontend\.env.local`。

### Step 1：PostGIS（:5432）

```powershell
cd D:\pack\GeoAI\GeoAI\docker
docker compose up -d postgis
docker ps --filter name=geoai-postgis
docker exec geoai-postgis psql -U geoai -d geoai -c "SELECT PostGIS_Version();"
```

首次启动会执行 `database/init/*.sql`（仅空 volume 时）。若要强制重灌库：

```powershell
docker compose down -v
docker compose up -d postgis
```

### Step 2：Spatial 服务（:8002）

新开终端：

```powershell
cd D:\pack\GeoAI\GeoAI\spatial
uv run uvicorn src.main:app --reload --port 8002
```

验证：

```powershell
curl http://localhost:8002/api/health
```

### Step 3：Agent 服务（:8001）

新开终端：

```powershell
cd D:\pack\GeoAI\GeoAI\agent
uv run uvicorn src.main:app --reload --port 8001
```

验证：

```powershell
curl http://localhost:8001/api/agent/health
```

### Step 4：前端（:5173）

新开终端：

```powershell
cd D:\pack\GeoAI\GeoAI\frontend
pnpm dev
```

浏览器打开：http://localhost:5173  
Vite 已代理 `/api/agent` → `8001`、`/api/spatial` → `8002`。

### 启动依赖关系

```
Docker Desktop Ready
        │
        ▼
  postgis (:5432)     ← docker compose up -d postgis
        │
        ▼
  spatial (:8002)     ← uv run uvicorn ...
        │
        ▼
  agent   (:8001)     ← 需 OPENAI_API_KEY
        │
        ▼
  frontend(:5173)     ← 需 VITE_MAPBOX_TOKEN
```

---

## 4. 备选：Docker 一键全栈

适合演示 / 不改代码时：

```powershell
cd D:\pack\GeoAI\GeoAI\docker
Copy-Item .env.example .env
# 编辑 .env 填入 OPENAI_*、VITE_* 等
docker compose up -d --build
```

| 服务 | URL |
|------|-----|
| 前端 | http://localhost:5173 |
| Agent | http://localhost:8001 |
| Spatial | http://localhost:8002 |
| PostGIS | localhost:5432 |

---

## 5. 验收清单

| # | 检查项 | 期望 |
|---|--------|------|
| 1 | `docker exec geoai-postgis psql ... PostGIS_Version()` | 有版本号 |
| 2 | `GET :8002/api/health` | DB 连通、healthy |
| 3 | `GET :8001/api/agent/health` | healthy，且能读到 LLM 配置 |
| 4 | 浏览器 :5173 | 地图底图可见（Mapbox Token 有效） |
| 5 | 聊天：「计算北京国贸周边 500 米缓冲区」 | 约 15–30s 返回报告 + 地图图层 |

最小 buffer 直连自测（不经 LLM）：

```powershell
curl -X POST http://localhost:8002/api/spatial/buffer `
  -H "Content-Type: application/json" `
  -d "{\"geometry\":{\"type\":\"Point\",\"coordinates\":[116.458,39.908]},\"distance\":500}"
```

---

## 6. `docker/.env.example` 内容（模板）

若仓库中尚无该文件，可按下列内容创建 `docker/.env.example`：

```env
POSTGRES_DB=geoai
POSTGRES_USER=geoai
POSTGRES_PASSWORD=geoai123

OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

VITE_MAPBOX_TOKEN=
VITE_CESIUM_ION_TOKEN=
```

---

## 7. Windows 常见问题

| 现象 | 处理 |
|------|------|
| `docker` / `uv` 找不到 | 安装后重开终端；检查 PATH；Docker 需 Desktop 引擎已启动 |
| 5432 端口占用 | 停掉本机其它 PostgreSQL，或改 compose 端口映射 |
| `uv sync` 慢 / 失败 | 配置镜像（如清华 / Astral 文档）；代理环境设 `HTTP_PROXY` |
| agent 首次启动很慢 | `sentence-transformers` / Chroma 首次下载模型，属正常 |
| Mapbox 灰屏 | Token 无效或未写入 `frontend/.env.local`，改后需重启 `pnpm dev` |
| Agent 报 API Key | 检查 `agent/.env` 是否被加载（文件在 `agent/` 根目录，非 `src/`） |
| OSM 拉数失败 | 见 [`data-collection-runbook.md`](./data-collection-runbook.md)，Overpass 需代理或缩小 bbox |
| PowerShell 下 `curl` | 实际是 `Invoke-WebRequest` 别名；可用 `curl.exe` 或 `Invoke-RestMethod` |

---

## 8. 建议安装顺序（按本机缺口）

1. **安装 uv** → 验证 `uv --version`
2. **安装 Docker Desktop + WSL2** → 验证 `docker ps`
3. **申请并填写** DeepSeek / Mapbox / Cesium → 创建 `agent/.env`、`frontend/.env.local`
4. **`uv sync`（spatial、agent）+ `pnpm install`（frontend）**
5. 按 §3 依次启动四层，按 §5 验收

预计纯安装耗时：Docker/WSL 重启约 20–40 分钟；依赖下载视网络 10–30 分钟；密钥申请视账号情况。

---

## 9. 与旧文档路径差异

[`phase-1-foundation.md`](./phase-1-foundation.md) 中示例路径仍为 `d:/study/GeoAI/...`。  
**本机请统一使用**：`D:\pack\GeoAI\GeoAI\...`。
