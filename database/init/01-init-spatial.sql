-- ==========================================
-- GeoAI 空间数据库初始化脚本
-- Phase 1: 扩展 + 基础表 + GiST 索引 + 测试数据
-- ==========================================

-- 1. 启用空间扩展
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 2. 建表

-- 建筑表 (面)
CREATE TABLE IF NOT EXISTS buildings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    height FLOAT,                -- 高度 (米)
    floors INTEGER,              -- 楼层数
    usage VARCHAR(100),          -- 用途: residential, commercial, mixed
    geom GEOMETRY(POLYGON, 4326) NOT NULL
);

-- POI 兴趣点表 (点)
CREATE TABLE IF NOT EXISTS poi (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),       -- 类别: coffee, restaurant, retail, school, hospital
    geom GEOMETRY(POINT, 4326) NOT NULL
);

-- 道路表 (线)
CREATE TABLE IF NOT EXISTS roads (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    road_type VARCHAR(50),       -- motorway, primary, secondary, tertiary, residential
    speed_limit INTEGER,         -- 限速 km/h
    oneway BOOLEAN DEFAULT FALSE,
    geom GEOMETRY(LINESTRING, 4326) NOT NULL
);

-- 3. GiST 空间索引

CREATE INDEX IF NOT EXISTS idx_buildings_geom ON buildings USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_poi_geom ON poi USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_roads_geom ON roads USING GIST(geom);

-- 4. 测试数据: 北京国贸周边

-- 建筑
INSERT INTO buildings (name, height, floors, usage, geom) VALUES
('国贸大厦A座', 155, 38, 'commercial', ST_GeomFromText('POLYGON((116.458 39.908, 116.460 39.908, 116.460 39.910, 116.458 39.910, 116.458 39.908))', 4326)),
('国贸大厦B座', 120, 30, 'commercial', ST_GeomFromText('POLYGON((116.456 39.907, 116.458 39.907, 116.458 39.909, 116.456 39.909, 116.456 39.907))', 4326)),
('建外SOHO东区', 80, 20, 'mixed', ST_GeomFromText('POLYGON((116.462 39.905, 116.465 39.905, 116.465 39.907, 116.462 39.907, 116.462 39.905))', 4326)),
('万达广场', 100, 25, 'commercial', ST_GeomFromText('POLYGON((116.468 39.906, 116.471 39.906, 116.471 39.908, 116.468 39.908, 116.468 39.906))', 4326)),
('华贸中心', 90, 22, 'commercial', ST_GeomFromText('POLYGON((116.472 39.910, 116.475 39.910, 116.475 39.912, 116.472 39.912, 116.472 39.910))', 4326));

-- POI
INSERT INTO poi (name, category, geom) VALUES
('星巴克国贸店', 'coffee', ST_SetSRID(ST_MakePoint(116.459, 39.909), 4326)),
('瑞幸咖啡建外SOHO店', 'coffee', ST_SetSRID(ST_MakePoint(116.463, 39.906), 4326)),
('海底捞大望路店', 'restaurant', ST_SetSRID(ST_MakePoint(116.467, 39.907), 4326)),
('SKP商场', 'retail', ST_SetSRID(ST_MakePoint(116.473, 39.911), 4326)),
('朝阳医院', 'hospital', ST_SetSRID(ST_MakePoint(116.452, 39.915), 4326)),
('北京八十中学', 'school', ST_SetSRID(ST_MakePoint(116.466, 39.913), 4326));

-- 道路
INSERT INTO roads (name, road_type, speed_limit, geom) VALUES
('建国路', 'primary', 60, ST_GeomFromText('LINESTRING(116.450 39.908, 116.455 39.908, 116.460 39.908, 116.465 39.908, 116.470 39.908, 116.475 39.908, 116.480 39.908)', 4326)),
('东三环中路', 'primary', 80, ST_GeomFromText('LINESTRING(116.458 39.900, 116.458 39.905, 116.458 39.910, 116.458 39.915, 116.458 39.920)', 4326)),
('大望路', 'secondary', 50, ST_GeomFromText('LINESTRING(116.467 39.900, 116.467 39.905, 116.467 39.910, 116.467 39.915)', 4326)),
('光华路', 'secondary', 50, ST_GeomFromText('LINESTRING(116.450 39.912, 116.458 39.912, 116.467 39.912, 116.475 39.912)', 4326));
