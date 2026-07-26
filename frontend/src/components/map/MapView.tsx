import { useEffect, useRef, useCallback } from "react";
import mapboxgl from "mapbox-gl";
import { useAppStore } from "../../store";
import type { GeoJSONFeatureCollection } from "../../types";
import { DrawTool } from "./DrawTool";

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

export function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const layersRef = useRef<string[]>([]);

  const setMapBounds = useAppStore((s) => s.setMapBounds);
  const agentResponse = useAppStore((s) => s.agentResponse);
  const drawGeometry = useAppStore((s) => s.drawGeometry);

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
      const bounds = map.getBounds();
      setMapBounds([bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()]);
    });

    map.on("moveend", () => {
      const bounds = map.getBounds();
      setMapBounds([bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()]);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // 渲染框选区域
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapRef.current?.loaded()) return;

    const layerId = "draw-geometry";
    try { map.removeLayer(layerId); map.removeSource(layerId); } catch { /* */ }

    if (drawGeometry?.features?.length) {
      map.addSource(layerId, { type: "geojson", data: drawGeometry as any });
      map.addLayer({
        id: layerId,
        type: "line",
        source: layerId,
        paint: { "line-color": "#1a237e", "line-width": 2, "line-dasharray": [4, 4] },
      });
      layersRef.current.push(layerId);
    }
  }, [drawGeometry]);

  // 当 Agent 返回结果时渲染 GeoJSON，支持分级着色
  const addGeoJSONLayer = useCallback(
    (fc: GeoJSONFeatureCollection, layerId: string) => {
      const map = mapRef.current;
      if (!map || !fc?.features?.length) return;

      try { map.removeLayer(layerId); map.removeSource(layerId); } catch { /* */ }

      // 检查是否有 score 属性 → 分级着色
      const hasScore = fc.features.some(
        (f) => typeof f.properties?.score === "number"
      );

      map.addSource(layerId, { type: "geojson", data: fc as any });

      if (hasScore) {
        // 按 score 分段着色
        const cases: any[] = [];
        COLOR_SCALE.forEach((step) => {
          cases.push(step.threshold);
          cases.push(step.color);
        });
        // score → color mapping via match + interpolation
        map.addLayer({
          id: layerId,
          type: "fill",
          source: layerId,
          paint: {
            "fill-color": [
              "interpolate",
              ["linear"],
              ["get", "score"],
              0, "#f44336",
              20, "#ff9800",
              40, "#ffeb3b",
              60, "#4caf50",
              80, "#1b5e20",
              100, "#003300",
            ],
            "fill-opacity": 0.5,
            "fill-outline-color": "#333",
          },
        });
      } else {
        // 无 score: 默认蓝色
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

      // 飞到数据范围
      try {
        const bounds = new mapboxgl.LngLatBounds();
        fc.features.forEach((f) => {
          if (f.geometry?.type === "Point" && f.geometry.coordinates) {
            bounds.extend(f.geometry.coordinates as [number, number]);
          }
        });
        if (!bounds.isEmpty()) {
          map.fitBounds(bounds, { padding: 80, maxZoom: 15 });
        }
      } catch { /* ignore */ }
    },
    []
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
      <DrawTool map={mapRef.current} />
    </div>
  );
}
