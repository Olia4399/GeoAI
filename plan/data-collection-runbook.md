cd database
# 建议在 spatial 或带 osmnx 的环境
uv run --directory ../spatial python scripts/fetch_osm.py --layers roads,buildings --building-limit 500
# 仅道路
uv run --directory ../spatial python scripts/fetch_osm.py --layers roads --output init/07-osm-roads-buildings.sql
# 仅建筑（限制条数防 SQL 过大）
uv run --directory ../spatial python scripts/fetch_osm.py --layers buildings --building-limit 500
```
失败常见原因：Overpass 超时/墙；处理：开代理、缩小 bbox、分图层重试。
## 4. 人口网格升级（可选）
示意数据足够演示 Agent 查询。升级路径：
1. 下载 WorldPop / GPW 北京裁剪 GeoTIFF  
2. `rasterio` / `gdal_polygonize` 转点或面密度  
3. `INSERT INTO population_grid ...` 替换示意格网  
## 5. 知识库重建
```bash
cd agent
# 编辑 src/knowledge/data/knowledge_items.json 后：
uv run python -m src.knowledge.build_kb
curl http://localhost:8001/api/agent/health
```
## 6. 验收 SQL
```sql
SELECT 'poi' AS t, COUNT(*) FROM poi
UNION ALL SELECT 'roads', COUNT(*) FROM roads
UNION ALL SELECT 'buildings', COUNT(*) FROM buildings
UNION ALL SELECT 'districts', COUNT(*) FROM districts
UNION ALL SELECT 'population_grid', COUNT(*) FROM population_grid;
SELECT category, COUNT(*) FROM poi WHERE category IN ('subway','cafe','restaurant') GROUP BY 1;
```
目标（灌库后）：roads ≫ 4、buildings ≫ 6；population_grid > 0；subway POI ≥ 15。
