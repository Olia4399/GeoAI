import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import { useAppStore } from "../../store";

const BTN_STYLE: React.CSSProperties = {
  padding: "6px 12px",
  border: "1px solid #ccc",
  borderRadius: 4,
  background: "#fff",
  cursor: "pointer",
  fontSize: 12,
  fontWeight: 500,
};

const ACTIVE_BTN: React.CSSProperties = {
  ...BTN_STYLE,
  background: "#1a237e",
  color: "#fff",
  borderColor: "#1a237e",
};

interface DrawToolProps {
  map: mapboxgl.Map | null;
}

export function DrawTool({ map }: DrawToolProps) {
  const drawMode = useAppStore((s) => s.drawMode);
  const setDrawMode = useAppStore((s) => s.setDrawMode);
  const setDrawGeometry = useAppStore((s) => s.setDrawGeometry);
  const rectRef = useRef<{ start: mapboxgl.LngLat; box: mapboxgl.Marker | null }>({
    start: new mapboxgl.LngLat(0, 0),
    box: null,
  });

  useEffect(() => {
    if (!map) return;

    if (drawMode === "rectangle") {
      map.getCanvas().style.cursor = "crosshair";

      const onMouseDown = (e: mapboxgl.MapMouseEvent) => {
        rectRef.current.start = e.lngLat;
        // 清除旧框
        if (rectRef.current.box) {
          rectRef.current.box.remove();
          rectRef.current.box = null;
        }
      };

      const onMouseUp = (e: mapboxgl.MapMouseEvent) => {
        const start = rectRef.current.start;
        const end = e.lngLat;

        const minLon = Math.min(start.lng, end.lng);
        const maxLon = Math.max(start.lng, end.lng);
        const minLat = Math.min(start.lat, end.lat);
        const maxLat = Math.max(start.lat, end.lat);

        if (Math.abs(maxLon - minLon) < 0.001 && Math.abs(maxLat - minLat) < 0.001) {
          return; // 太小忽略
        }

        const geojson = {
          type: "Polygon" as const,
          coordinates: [[
            [minLon, minLat],
            [maxLon, minLat],
            [maxLon, maxLat],
            [minLon, maxLat],
            [minLon, minLat],
          ]],
        };

        setDrawGeometry({
          type: "FeatureCollection",
          features: [
            { type: "Feature", properties: {}, geometry: geojson },
          ],
        });

        // 地图上画框
        if (rectRef.current.box) rectRef.current.box.remove();
        const el = document.createElement("div");
        el.style.border = "2px dashed #1a237e";
        el.style.background = "rgba(26, 35, 126, 0.1)";
        el.style.position = "absolute";
        el.style.pointerEvents = "none";
        const box = new mapboxgl.Marker({ element: el });
        box.setLngLat([(minLon + maxLon) / 2, (minLat + maxLat) / 2]);
        box.addTo(map);
        rectRef.current.box = box;

        setDrawMode(null);
        map.getCanvas().style.cursor = "";
      };

      map.on("mousedown", onMouseDown);
      map.on("mouseup", onMouseUp);

      return () => {
        map.off("mousedown", onMouseDown);
        map.off("mouseup", onMouseUp);
        map.getCanvas().style.cursor = "";
      };
    } else {
      map.getCanvas().style.cursor = "";
    }
  }, [map, drawMode]);

  if (!map) return null;

  return (
    <div
      style={{
        position: "absolute",
        top: 10,
        left: 10,
        zIndex: 10,
        display: "flex",
        gap: 6,
      }}
    >
      <button
        style={drawMode === "rectangle" ? ACTIVE_BTN : BTN_STYLE}
        onClick={() => setDrawMode(drawMode === "rectangle" ? null : "rectangle")}
      >
        {drawMode === "rectangle" ? "📐 框选中..." : "📐 框选区域"}
      </button>
    </div>
  );
}
