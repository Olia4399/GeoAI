import { useEffect, useRef } from "react";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import { useAppStore } from "../../store";

const CESIUM_TOKEN = import.meta.env.VITE_CESIUM_ION_TOKEN || "";

export function CesiumView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const agentResponse = useAppStore((s) => s.agentResponse);

  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return;

    if (CESIUM_TOKEN) {
      Cesium.Ion.defaultAccessToken = CESIUM_TOKEN;
    }

    const viewer = new Cesium.Viewer(containerRef.current, {
      terrain: CESIUM_TOKEN
        ? Cesium.Terrain.fromWorldTerrain()
        : undefined,
      animation: false,
      timeline: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      geocoder: false,
    });

    // 飞到北京国贸
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(116.458, 39.908, 5000),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-45),
        roll: 0,
      },
    });

    viewerRef.current = viewer;

    return () => {
      viewer.destroy();
      viewerRef.current = null;
    };
  }, []);

  // 当 Agent 返回结果时，加载 GeoJSON 到 Cesium
  useEffect(() => {
    if (!agentResponse?.results || !viewerRef.current) return;
    const viewer = viewerRef.current;

    agentResponse.results.forEach((fc) => {
      if (fc?.features?.length) {
        Cesium.GeoJsonDataSource.load(fc as any, {
          stroke: Cesium.Color.RED,
          fill: Cesium.Color.RED.withAlpha(0.3),
          strokeWidth: 2,
        }).then((ds) => {
          viewer.dataSources.add(ds);
          viewer.flyTo(ds);
        });
      }
    });
  }, [agentResponse]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%" }}
    />
  );
}
