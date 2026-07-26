import { useEffect, useRef, useCallback } from "react";
import mapboxgl from "mapbox-gl";
import { useAppStore } from "../../store";
import type { GeoJSONFeatureCollection } from "../../types";

// Phase 1: Mapbox token from env or demo token
const MAPBOX_TOKEN =
  import.meta.env.VITE_MAPBOX_TOKEN ||
  "pk.eyJ1IjoibWFwYm94LWRlbW8iLCJhIjoiY2x0MHF4dXJuMDhnazJpcGdkYXNhM3pzdyJ9.HklN5NjLgKjDMaVhVQn5Fw";

mapboxgl.accessToken = MAPBOX_TOKEN;

const DEFAULT_CENTER: [number, number] = [116.458, 39.908]; // 北京国贸
const DEFAULT_ZOOM = 13;

export function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const layersRef = useRef<string[]>([]);

  const setMapBounds = useAppStore((s) => s.setMapBounds);
  const agentResponse = useAppStore((s) => s.agentResponse);

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
      // 同步地图 bounds 到 store
      const bounds = map.getBounds();
      setMapBounds([
        bounds.getWest(),
        bounds.getSouth(),
        bounds.getEast(),
        bounds.getNorth(),
      ]);
    });

    map.on("moveend", () => {
      const bounds = map.getBounds();
      setMapBounds([
        bounds.getWest(),
        bounds.getSouth(),
        bounds.getEast(),
        bounds.getNorth(),
      ]);
    });

    // 地图点击获取坐标
    map.on("click", (e) => {
      console.log("[Map] Click at:", e.lngLat.toArray());
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // 当 Agent 返回结果时，渲染 GeoJSON 到地图
  const addGeoJSONLayer = useCallback(
    (data: GeoJSONFeatureCollection, layerId: string, color = "#ff4444") => {
      const map = mapRef.current;
      if (!map) return;

      // 移除旧图层
      if (layersRef.current.includes(layerId)) {
        try {
          map.removeLayer(layerId);
          map.removeSource(layerId);
        } catch { /* ignore */ }
      }

      map.addSource(layerId, { type: "geojson", data: data as any });
      map.addLayer({
        id: layerId,
        type: "fill",
        source: layerId,
        paint: {
          "fill-color": color,
          "fill-opacity": 0.35,
          "fill-outline-color": color,
        },
      });
      layersRef.current.push(layerId);

      // 飞至数据范围
      // map.fitBounds awaits bounds computation; use flyTo for simplicity
      map.flyTo({ center: DEFAULT_CENTER, zoom: 14 });
    },
    []
  );

  // 响应 Agent 结果变化
  useEffect(() => {
    if (!agentResponse?.results || !mapRef.current) return;
    agentResponse.results.forEach((fc, i) => {
      if (fc?.features?.length) {
        addGeoJSONLayer(fc, `agent-result-${i}`, i === 0 ? "#ff4444" : "#4488ff");
      }
    });
  }, [agentResponse, addGeoJSONLayer]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%" }}
    />
  );
}
