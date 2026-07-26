# GeoAI Phase 2 — 多步空间推理与智能选址

> 基于 Phase 1 骨架，补齐全部 GIS Tool + Agent 多步推理 + 前端交互增强。
> 执行日期: 2026-07-26

## 执行结果

| Step | 内容 | 状态 |
|------|------|------|
| Step 1 | 补齐空间分析引擎 (5 个新服务) | ✅ |
| Step 2 | Agent Tool 体系扩充 (2→7 Tool) | ✅ |
| Step 3 | 前端地图交互增强 | ✅ |
| Step 4 | 朝阳区 OSM 数据 (5349 POI) | ✅ |
| Step 5 | 端到端验证 | ⬜ 待 Agent 重启后测试 |

## 新增 API 清单

### Spatial Service (:8002)

| 端点 | 方法 | 说明 | 底层 |
|------|------|------|------|
| `/api/spatial/query` | POST | 空间数据查询 (buildings/poi/roads + bbox + category) | PostGIS |
| `/api/spatial/buffer` | POST | 缓冲区分析 | Shapely |
| `/api/spatial/distance` | POST | 距离计算 | PyProj |
| `/api/spatial/route` | POST | 路径规划 (walk) | OSMnx + NetworkX |
| `/api/spatial/overlay` | POST | 空间叠加 (intersection/union/difference) | GeoPandas |
| `/api/spatial/density` | POST | 核密度分析 (KDE) | SciPy |
| `/api/spatial/suitability` | POST | 加权叠加适宜性评价 | Shapely + NumPy |

### Agent Service (:8001)

| 端点 | 方法 | Tool 数量 | 说明 |
|------|------|-----------|------|
| `/api/agent/health` | GET | — | 健康检查 |
| `/api/agent/query` | POST | 7 | 自然语言 → 多步空间推理 |

**7 个 Tool：** `spatial_query`, `buffer_analysis`, `distance_analysis`, `route_analysis`, `overlay_analysis`, `density_analysis`, `suitability_analysis`

## 新增文件

| 文件 | 说明 |
|------|------|
| `spatial/src/services/query.py` | PostGIS 空间查询 |
| `spatial/src/services/route.py` | OSMnx 路径规划 |
| `spatial/src/services/overlay.py` | GeoPandas 空间叠加 |
| `spatial/src/services/density.py` | SciPy KDE 密度分析 |
| `spatial/src/services/suitability.py` | 加权叠加适宜性评价 |
| `frontend/src/components/map/DrawTool.tsx` | 地图矩形框选 |
| `database/init/02-osm-chaoyang.sql` | 朝阳区 5349 条 OSM POI |
| `database/scripts/fetch_osm.py` | OSM 数据采集脚本 |

## 修改文件

| 文件 | 改动 |
|------|------|
| `spatial/src/api/spatial_routes.py` | 5 新路由 (query/route/overlay/density/suitability) |
| `spatial/src/models/schemas.py` | 新 Pydantic 模型 |
| `spatial/pyproject.toml` | +osmnx, networkx, scipy |
| `agent/src/tools/spatial_tools.py` | 5 新 Tool + 7 个 Pydantic Schema |
| `agent/src/planning/planner.py` | 更新 SYSTEM_PROMPT (选址流程 + 7 Tool 说明) |
| `frontend/src/components/map/MapView.tsx` | 分级着色 + DrawTool 集成 |
| `frontend/src/components/chat/MessageList.tsx` | react-markdown 渲染 |
| `frontend/src/store/index.ts` | +drawMode + drawGeometry |
| `frontend/src/types/index.ts` | +DrawMode |
| `frontend/package.json` | +react-markdown |

## 数据库

```
geoai
├── buildings     6 rows (+ 200 OSM 建筑待补充)
├── poi           5355 rows (5349 OSM + 6 测试数据)
│   ├── cafe:      546
│   ├── restaurant: 2062
│   ├── bank:      519
│   └── other:     2228
└── roads         4 rows (测试数据; OSM 道路下载超时)
```

## 当前待修复

- Agent 语法错误已修复（中文引号 → 无引号），重启 Agent 即可
