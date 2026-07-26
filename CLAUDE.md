# GeoAI 城市空间智能分析平台 — AI 开发指南

## 项目定位

构建基于 LLM Agent、空间数据库和 WebGIS 技术的城市空间智能分析平台。用户通过自然语言或地图交互提出空间问题，AI 自动理解需求、规划分析流程、调用 GIS 工具完成空间计算，并通过三维地图和智能报告反馈决策结果。

## 技术选型

| 层级 | 技术 | 端口 |
|------|------|------|
| 前端 | React 19 + TypeScript + Vite + Mapbox GL JS + CesiumJS | 5173 |
| Agent | LangChain + LangGraph (ReAct) + FastAPI | 8001 |
| 空间服务 | FastAPI + GeoPandas + Shapely + PySAL | 8002 |
| 数据库 | PostgreSQL 16 + PostGIS 3.4 | 5432 |
| 包管理 | pnpm (前端), uv (Python) | — |
| LLM | OpenAI 兼容 API (gpt-4o / deepseek 等) | — |

## 目录约定

- `plan/` — 各 Phase 执行方案文档，不可放置代码
- `frontend/` — 用户交互层，React SPA
- `agent/` — Spatial Agent 层，Python FastAPI 服务
- `spatial/` — 空间能力服务层，Python FastAPI 服务
- `database/` — SQL 初始化脚本和迁移
- `docker/` — Docker Compose 编排和环境变量模板
- `data/` — 原始/处理后/示例数据，不纳入版本控制
- `docs/` — 文档和 API 说明

## 开发约定

### Python 服务
- 使用 uv 管理依赖，`pyproject.toml` 定义项目
- FastAPI 应用工厂模式，`src/main.py` 为入口
- Pydantic v2 定义请求/响应模型
- 空间坐标统一使用 WGS84 (SRID 4326)
- 距离计算时转换到 EPSG:3857 (米制)

### 前端
- 使用 pnpm，Vite 构建
- Zustand 状态管理，不引入 Redux
- 组件按功能分层：layout / map / chat / report
- Mapbox GL CSS 在 index.html 中引入，Cesium CSS 在组件内引入
- API 调用统一通过 `services/api.ts` 和 `services/agent.ts`

### 数据库
- 所有空间表统一 SRID 4326
- 必须为几何列创建 GiST 索引
- 初始化脚本放在 `database/init/`，按编号顺序执行

## 核心概念

### Spatial Agent 工作流
```
用户自然语言 → LLM 意图解析 → Agent 任务规划 → Tool 调用 
→ Spatial Service 执行 → PostGIS 查询 → 结果返回 
→ Cesium/Mapbox 可视化 → LLM 报告生成
```

### GIS Tool 设计原则
- Agent 不直接调用底层 GIS 函数（如 ST_Buffer）
- 暴露业务级 Tool（如 `buffer_analysis`）
- Tool 内部封装 PostGIS / Shapely / GeoPandas 调用

### 六大核心能力
1. 自然语言驱动空间分析 Agent
2. 空间分析计算引擎（buffer, distance, route, overlay, density, suitability）
3. 时空变化分析
4. 遥感 AI 识别（YOLO, SAM, SegFormer）
5. 三维城市数字孪生（Cesium 3D Tiles）
6. 智能空间报告生成（LLM + RAG）
