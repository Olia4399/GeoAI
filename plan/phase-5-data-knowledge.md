| Step | 内容 | 环境要求 | 状态 |
|------|------|----------|------|
| Step 1 | 本方案文档入库 `plan/` | 无 | ✅ |
| Step 2 | 扩写 `knowledge_items.json`（29→60+） | 无 | ✅（本机执行） |
| Step 3 | SQL：`04-population-grid` / `05-metro-poi` / `06-seed-roads-buildings` | 无（写文件） | ✅（本机执行） |
| Step 4 | 改进 `fetch_osm.py` + `plan/data-collection-runbook.md` | 无 | ✅（本机执行） |
| Step 5 | `query.py` 支持 `population_grid` | 无 | ✅（本机执行） |
| Step 6 | 更新 ops 归档 INDEX / LESSONS | 无 | ✅（本机执行） |
| Step 7 | 有 Docker 机器：灌库 + OSM 道路/建筑全量 + `build_kb` | Docker + 科学上网 | ⬜ 待上机 |
## 增益说明
| 交付 | 对项目的增益 |
|------|----------------|
| 知识扩写 | 报告 RAG 更贴咖啡/充电/零售/餐饮/药店；权重与缓冲半径可被 Agent 引用 |
| 人口网格 SQL | 适宜性/选址可按人口密度打分（示意数据可演示，全量 WorldPop 后替换） |
| 地铁 POI | 缓冲/距离分析可对齐「距地铁 ≤500m」行业标准 |
| 加密道路/建筑种子 | 无 OSM 时 route / overlay / 3D 仍有可用几何 |
| 采集 Runbook | 换机可复现：下载 → SQL → init → 验证 |
## 上机待办（Step 7）
```bash
# 有科学上网 + Docker 时
cd docker && docker compose up -d postgis
cd ../database && python scripts/fetch_osm.py --layers roads,buildings --building-limit 500
# 将生成/增量写入 init/02 或独立 07-osm-roads-buildings.sql 后重建库
cd ../agent && uv run python -m src.knowledge.build_kb
```
详见 [`data-collection-runbook.md`](./data-collection-runbook.md)。
## 文件索引
| 文件 | 说明 |
|------|------|
| `plan/phase-5-data-knowledge.md` | 本方案 |
| `plan/data-collection-runbook.md` | 采集与灌库手册 |
| `agent/src/knowledge/data/knowledge_items.json` | RAG 源 |
| `database/init/04-population-grid.sql` | 人口网格 |
| `database/init/05-metro-poi.sql` | 地铁站 POI |
| `database/init/06-seed-roads-buildings.sql` | 道路/建筑加密种子 |
| `database/scripts/fetch_osm.py` | OSM 采集 |
| `spatial/src/services/query.py` | 查询白名单 |
