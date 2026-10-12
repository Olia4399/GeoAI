import { useEffect, useRef, useCallback } from "react";
import mapboxgl from "mapbox-gl";
import { useAppStore } from "../../store";
import type { GeoJSONFeatureCollection } from "../../types";
import { DrawTool } from "./DrawTool";
import { LayerPanel, LAYERS } from "./LayerPanel";
import { useState } from "react";

const MAPBOX_TOKEN =
  import.meta.env.VITE_MAPBOX_TOKEN ||
  "pk.eyJ1IjoibWFwYm94LWRlbW8iLCJhIjoiY2x0MHF4dXJuMDhnazJpcGdkYXNhM3pzdyJ9.HklN5NjLgKjDMaVhVQn5Fw";

mapboxgl.accessToken = MAPBOX_TOKEN;

const DEFAULT_CENTER: [number, number] = [116.458, 39.908];
const DEFAULT_ZOOM = 13;

/** 按 score 分级着色 */
const COLOR_SCALE = [
  { threshold: 80, color: "#1b5e20" },
  { threshold: 60, color: "#4caf50" },
  { threshold: 40, color: "#ffeb3b" },
  { threshold: 20, color: "#ff9800" },
  { threshold: 0, color: "#f44336" },
];

function getScoreColor(score: number): string {
  for (const step of COLOR_SCALE) {
    if (score >= step.threshold) return step.color;
  }
  return "#f44336";
}

/** 转义要素属性文本，避免数据源里的 HTML 片段造成注入 */
function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (ch) => {
    switch (ch) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      default:
        return "&#39;";
    }
  });
}

/** 生成"中心点 + 半径(米)"的圆形多边形（64 段，展示用途，度制近似足够） */
function makeCirclePolygon(
  center: [number, number],
  radiusM: number,
  segments = 64,
) {
  const [lng, lat] = center;
  const dLat = radiusM / 111320;
  const dLng = radiusM / (111320 * Math.cos((lat * Math.PI) / 180));
  const ring: [number, number][] = [];
  for (let i = 0; i <= segments; i++) {
    const t = (i / segments) * Math.PI * 2;
    ring.push([lng + dLng * Math.cos(t), lat + dLat * Math.sin(t)]);
  }
  return {
    type: "Feature" as const,
    properties: {},
    geometry: { type: "Polygon" as const, coordinates: [ring] },
  };
}

export function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const layersRef = useRef<string[]>([]);
  // 要素 hover 提示框复用同一实例（避免频繁创建）
  const popupRef = useRef<mapboxgl.Popup | null>(null);
  const [layerPanelVisible, setLayerPanelVisible] = useState(false);
  // 地图实例必须用 state 持有：ref 更新不触发渲染，DrawTool 会一直拿到过期的 null
  const [mapInstance, setMapInstance] = useState<mapboxgl.Map | null>(null);

  const setMapBounds = useAppStore((s) => s.setMapBounds);
  const agentResponse = useAppStore((s) => s.agentResponse);
  const drawGeometry = useAppStore((s) => s.drawGeometry);
  const layerVisibility = useAppStore((s) => s.layerVisibility);
  const setLayerVisibility = useAppStore((s) => s.setLayerVisibility);

  // 图层显隐真正落到 Mapbox style 图层上（按 id 前缀匹配，如 road-*、agent-result-*）
  const applyVisibilityRef = useRef<() => void>(() => {});
  applyVisibilityRef.current = () => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    LAYERS.forEach((layer) => {
      const prefix = layer.mapPrefix;
      if (!prefix || layer.disabled) return;
      const visible = layerVisibility[layer.id] !== false;
      (map.getStyle().layers || [])
        .filter((l) => l.id.startsWith(prefix))
        .forEach((l) =>
          map.setLayoutProperty(
            l.id,
            "visibility",
            visible ? "visible" : "none",
          ),
        );
    });
  };

  useEffect(() => {
    applyVisibilityRef.current();
  }, [layerVisibility]);

  // 初始化地图
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/light-v11",
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
    });

    map.addControl(new mapboxgl.NavigationControl(), "top-right");

    map.on("load", () => {
      // mapbox-gl 3.x 类型中 getBounds 可空（globe 投影），load/moveend 时必有值
      const bounds = map.getBounds()!;
      setMapBounds([
        bounds.getWest(),
        bounds.getSouth(),
        bounds.getEast(),
        bounds.getNorth(),
      ]);
      // style 就绪后应用一次图层显隐
      applyVisibilityRef.current();
    });

    map.on("moveend", () => {
      const bounds = map.getBounds()!;
      setMapBounds([
        bounds.getWest(),
        bounds.getSouth(),
        bounds.getEast(),
        bounds.getNorth(),
      ]);
    });

    mapRef.current = map;
    setMapInstance(map);

    return () => {
      map.remove();
      mapRef.current = null;
      setMapInstance(null);
    };
  }, []);

  // 渲染框选区域
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapRef.current?.loaded()) return;

    const layerId = "draw-geometry";
    try {
      map.removeLayer(layerId);
      map.removeSource(layerId);
    } catch {
      /* */
    }

    if (drawGeometry?.features?.length) {
      map.addSource(layerId, { type: "geojson", data: drawGeometry as any });
      map.addLayer({
        id: layerId,
        type: "line",
        source: layerId,
        paint: {
          "line-color": "#1a237e",
          "line-width": 2,
          "line-dasharray": [4, 4],
        },
      });
      layersRef.current.push(layerId);
    }
  }, [drawGeometry]);

  // 当 Agent 返回结果时渲染 GeoJSON：按几何类型分派图层（点/线/面），
  // 面支持 score 分级着色；携带 center+radius 元数据的结果额外绘制"范围圈"
  const addGeoJSONLayer = useCallback(
    (fc: GeoJSONFeatureCollection, layerId: string) => {
      const map = mapRef.current;
      if (!map || !fc?.features?.length) return;

      // 幂等清理（含上次渲染可能残留的范围圈图层/数据源）
      const rm = (id: string) => {
        try {
          if (map.getLayer(id)) map.removeLayer(id);
        } catch {
          /* */
        }
        try {
          if (map.getSource(id)) map.removeSource(id);
        } catch {
          /* */
        }
      };
      rm(`${layerId}-radius-fill`); // 先移除填充层（否则数据源仍被占用无法移除）
      rm(`${layerId}-radius`);
      rm(layerId);

      // 显式 string：项目 GeoJSONGeometry 是判别联合，运行时可能遇到 Multi* 类型
      const geomType: string = fc.features[0]?.geometry?.type || "Polygon";
      const isPoint = geomType === "Point" || geomType === "MultiPoint";
      const isLine =
        geomType === "LineString" || geomType === "MultiLineString";
      // 检查是否有 score 属性 → 分级着色
      const hasScore = fc.features.some(
        (f) => typeof f.properties?.score === "number",
      );

      map.addSource(layerId, { type: "geojson", data: fc as any });

      // score → 颜色（点/面共用同一插值）
      const scoreColor: any = [
        "interpolate",
        ["linear"],
        ["get", "score"],
        0,
        "#f44336",
        20,
        "#ff9800",
        40,
        "#ffeb3b",
        60,
        "#4caf50",
        80,
        "#1b5e20",
        100,
        "#003300",
      ];

      if (isPoint) {
        // 点要素（POI 查询/附近查询等）：fill 层无法渲染点，必须用 circle 层
        map.addLayer({
          id: layerId,
          type: "circle",
          source: layerId,
          paint: {
            "circle-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              10,
              4,
              14,
              7,
              18,
              12,
            ],
            "circle-color": hasScore ? scoreColor : "#4488ff",
            "circle-opacity": 0.9,
            "circle-stroke-width": 1.5,
            "circle-stroke-color": "#ffffff",
          },
        });

        // hover 提示：显示要素名称 + 类别/距离（先 off 再 on，避免重渲染时重复注册）
        // mapbox-gl 类型声明缺少 off(type, layerId) 重载（运行时支持），放宽类型
        (map as any).off("mousemove", layerId);
        (map as any).off("mouseleave", layerId);
        map.on("mousemove", layerId, (e) => {
          const f = e.features?.[0];
          if (!f) return;
          const props = ((f as any).properties || {}) as Record<string, any>;
          const name = props.name || props.category || "未命名要素";
          const extra: string[] = [];
          if (props.name && props.category) extra.push(String(props.category));
          if (typeof props.distance_m === "number")
            extra.push(`距离 ${props.distance_m} 米`);
          if (!popupRef.current) {
            popupRef.current = new mapboxgl.Popup({
              closeButton: false,
              closeOnClick: false,
              offset: 12,
              maxWidth: "280px",
            });
          }
          popupRef.current
            .setLngLat(e.lngLat)
            .setHTML(
              `<div style="font-size:12px;line-height:1.6;color:#333">` +
                `<strong style="color:#1a237e">${escapeHtml(String(name))}</strong>` +
                (extra.length
                  ? `<br/><span style="color:#666">${escapeHtml(extra.join(" · "))}</span>`
                  : "") +
                `</div>`,
            )
            .addTo(map);
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", layerId, () => {
          popupRef.current?.remove();
          map.getCanvas().style.cursor = "";
        });
      } else if (isLine) {
        // 线要素（路径规划等）
        map.addLayer({
          id: layerId,
          type: "line",
          source: layerId,
          paint: {
            "line-color": "#4488ff",
            "line-width": 3,
            "line-opacity": 0.85,
          },
        });
      } else if (hasScore) {
        // 面要素 + score：分级着色
        map.addLayer({
          id: layerId,
          type: "fill",
          source: layerId,
          paint: {
            "fill-color": scoreColor,
            "fill-opacity": 0.5,
            "fill-outline-color": "#333",
          },
        });
      } else {
        // 面要素无 score：默认蓝色
        map.addLayer({
          id: layerId,
          type: "fill",
          source: layerId,
          paint: {
            "fill-color": "#4488ff",
            "fill-opacity": 0.35,
            "fill-outline-color": "#4488ff",
          },
        });
      }

      layersRef.current.push(layerId);
      // 新结果图层立即套用当前显隐设置
      applyVisibilityRef.current();

      // 收集边界（递归取任意几何类型的坐标），供 fitBounds 使用
      const bounds = new mapboxgl.LngLatBounds();
      const extendCoords = (c: any) => {
        if (typeof c?.[0] === "number") bounds.extend(c as [number, number]);
        else if (Array.isArray(c)) c.forEach(extendCoords);
      };
      fc.features.forEach((f) => {
        const coords = f.geometry?.coordinates;
        if (coords) extendCoords(coords);
      });

      // 附近查询结果携带 center+radius 元数据（米） → 绘制范围圈：虚线边 + 浅填充
      const center = (fc as any).center as [number, number] | undefined;
      const radius = (fc as any).radius as number | undefined;
      if (Array.isArray(center) && typeof radius === "number" && radius > 0) {
        const rid = `${layerId}-radius`;
        map.addSource(rid, {
          type: "geojson",
          data: makeCirclePolygon(center, radius) as any,
        });
        map.addLayer({
          id: `${rid}-fill`,
          type: "fill",
          source: rid,
          paint: { "fill-color": "#1a237e", "fill-opacity": 0.06 },
        });
        map.addLayer({
          id: rid,
          type: "line",
          source: rid,
          paint: {
            "line-color": "#1a237e",
            "line-width": 1.5,
            "line-dasharray": [3, 2],
          },
        });
        const dLat = radius / 111320;
        const dLng = radius / (111320 * Math.cos((center[1] * Math.PI) / 180));
        bounds.extend([center[0] - dLng, center[1] - dLat]);
        bounds.extend([center[0] + dLng, center[1] + dLat]);
      }

      // 飞到数据范围
      try {
        if (!bounds.isEmpty()) {
          map.fitBounds(bounds, { padding: 80, maxZoom: 15 });
        }
      } catch {
        /* ignore */
      }
    },
    [],
  );

  // 响应 Agent 结果变化
  useEffect(() => {
    if (!agentResponse?.results || !mapRef.current) return;
    agentResponse.results.forEach((fc, i) => {
      addGeoJSONLayer(fc, `agent-result-${i}`);
    });
  }, [agentResponse, addGeoJSONLayer]);

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      <DrawTool map={mapInstance} />
      <LayerPanel
        visible={layerPanelVisible}
        onToggle={() => setLayerPanelVisible(!layerPanelVisible)}
        visibility={layerVisibility}
        onVisibilityChange={(id, visible) => setLayerVisibility(id, visible)}
      />
    </div>
  );
}
