-- ==========================================
-- Phase 5: 朝阳区主要地铁站 → poi.category = subway
-- 便于 500m 缓冲与距离分析（坐标为近似）
-- ==========================================
INSERT INTO poi (name, category, geom) VALUES
('国贸站', 'subway', ST_SetSRID(ST_MakePoint(116.461, 39.909), 4326)),
('大望路站', 'subway', ST_SetSRID(ST_MakePoint(116.478, 39.908), 4326)),
('永安里站', 'subway', ST_SetSRID(ST_MakePoint(116.451, 39.908), 4326)),
('金台夕照站', 'subway', ST_SetSRID(ST_MakePoint(116.461, 39.917), 4326)),
('呼家楼站', 'subway', ST_SetSRID(ST_MakePoint(116.465, 39.923), 4326)),
('团结湖站', 'subway', ST_SetSRID(ST_MakePoint(116.466, 39.934), 4326)),
('农业展览馆站', 'subway', ST_SetSRID(ST_MakePoint(116.465, 39.942), 4326)),
('亮马桥站', 'subway', ST_SetSRID(ST_MakePoint(116.465, 39.950), 4326)),
('三元桥站', 'subway', ST_SetSRID(ST_MakePoint(116.457, 39.961), 4326)),
('望京站', 'subway', ST_SetSRID(ST_MakePoint(116.469, 39.999), 4326)),
('望京西站', 'subway', ST_SetSRID(ST_MakePoint(116.450, 39.996), 4326)),
('阜通站', 'subway', ST_SetSRID(ST_MakePoint(116.475, 39.992), 4326)),
('东风北桥站', 'subway', ST_SetSRID(ST_MakePoint(116.490, 39.958), 4326)),
('枣营站', 'subway', ST_SetSRID(ST_MakePoint(116.479, 39.944), 4326)),
('朝阳公园站', 'subway', ST_SetSRID(ST_MakePoint(116.488, 39.934), 4326)),
('金台路站', 'subway', ST_SetSRID(ST_MakePoint(116.482, 39.923), 4326)),
('红庙站', 'subway', ST_SetSRID(ST_MakePoint(116.483, 39.916), 4326)),
('双井站', 'subway', ST_SetSRID(ST_MakePoint(116.462, 39.893), 4326)),
('劲松站', 'subway', ST_SetSRID(ST_MakePoint(116.461, 39.884), 4326)),
('潘家园站', 'subway', ST_SetSRID(ST_MakePoint(116.461, 39.875), 4326)),
('十里河站', 'subway', ST_SetSRID(ST_MakePoint(116.473, 39.866), 4326)),
('三里屯站(公交枢纽近似)', 'subway', ST_SetSRID(ST_MakePoint(116.455, 39.937), 4326));