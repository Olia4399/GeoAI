import { useEffect, useRef } from "react";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import { useAppStore } from "../../store";
import type { GeoJSONFeatureCollection } from "../../types";

const CESIUM_TOKEN = import.meta.env.VITE_CESIUM_ION_TOKEN || "";

/** 按 score 分级取色 */
function getScoreColor(score: number): Cesium.Color {
  if (score >= 80) return Cesium.Color.fromCssColorString("#1b5e20").withAlpha(0.8);
  if (score >= 60) return Cesium.Color.fromCssColorString("#4caf50").withAlpha(0.7);
  if (score >= 40) return Cesium.Color.fromCssColorString("#ffeb3b").withAlpha(0.6);
  if (score >= 20) return Cesium.Color.fromCssColorString("#ff9800").withAlpha(0.6);
  return Cesium.Color.fromCssColorString("#f44336").withAlpha(0.5);
}

/** 从 GeoJSON FeatureCollection 渲染 3D 实体 */
function addAnalysis3D(viewer: Cesium.Viewer, fc: GeoJSONFeatureCollection) {
  if (!fc?.features?.length) return;

  fc.features.forEach((feature) => {
    const geom = feature.geometry;
    const props = feature.properties || {};
    const score = typeof props.score === "number" ? props.score : 50;
    const color = getScoreColor(score);

    if (geom.type === "Polygon" && geom.coordinates?.[0]) {
      viewer.entities.add({
        polygon: {
          hierarchy: Cesium.Cartesian3.fromDegreesArray(
            geom.coordinates[0].flatMap((c: number[]) => [c[0], c[1]])
          ),
          extrudedHeight: Math.max(score * 2, 10), // 得分越高柱子越高
          material: color,
          outline: true,
          outlineColor: Cesium.Color.WHITE,
        },
        properties: new Cesium.ConstantProperty(props),
      });
    } else if (geom.type === "Point" && geom.coordinates) {
      viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(
          geom.coordinates[0],
          geom.coordinates[1],
          50
        ),
        point: {
          pixelSize: 8,
          color: color,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 1,
        },
        properties: new Cesium.ConstantProperty(props),
      });
    }
  });
}

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
      terrain: CESIUM_TOKEN ? Cesium.Terrain.fromWorldTerrain() : undefined,
      animation: false,
      timeline: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      geocoder: false,
    });

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

  // Agent 结果 → 3D 实体
  useEffect(() => {
    if (!agentResponse?.results || !viewerRef.current) return;
    const viewer = viewerRef.current;

    // 清除旧实体
    viewer.entities.removeAll();

    agentResponse.results.forEach((fc) => {
      if (fc?.features?.length) {
        // 检查是否有 score → 3D 分级渲染
        const hasScore = fc.features.some(
          (f) => typeof f.properties?.score === "number"
        );
        if (hasScore) {
          addAnalysis3D(viewer, fc);
        } else {
          // 无 score → 用 GeoJsonDataSource 默认红色
          Cesium.GeoJsonDataSource.load(fc as any, {
            stroke: Cesium.Color.RED,
            fill: Cesium.Color.RED.withAlpha(0.3),
            strokeWidth: 2,
          }).then((ds) => {
            viewer.dataSources.add(ds);
            viewer.flyTo(ds);
          });
        }
      }
    });

    // 飞到数据范围
    if (agentResponse.results.length > 0) {
      viewer.flyTo(viewer.entities);
    }
  }, [agentResponse]);

  return (
    <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
  );
}
