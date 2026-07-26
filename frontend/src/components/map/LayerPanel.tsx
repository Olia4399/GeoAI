import { useState } from "react";

type LayerId = "poi" | "roads" | "buildings" | "districts" | "analysis" | "buffer";

interface LayerDef {
  id: LayerId;
  label: string;
  color: string;
}

const LAYERS: LayerDef[] = [
  { id: "poi", label: "POI 兴趣点", color: "#4488ff" },
  { id: "roads", label: "道路网络", color: "#888888" },
  { id: "buildings", label: "建筑", color: "#ff9800" },
  { id: "districts", label: "行政区划", color: "#9c27b0" },
  { id: "analysis", label: "分析结果", color: "#4caf50" },
  { id: "buffer", label: "缓冲区", color: "#f44336" },
];

const PANEL: React.CSSProperties = {
  position: "absolute",
  top: 50,
  right: 10,
  zIndex: 10,
  background: "#fff",
  borderRadius: 8,
  boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
  width: 200,
  fontSize: 12,
  overflow: "hidden",
};

const HEADER: React.CSSProperties = {
  padding: "8px 12px",
  fontWeight: 600,
  borderBottom: "1px solid #eee",
  display: "flex",
  justifyContent: "space-between",
  cursor: "pointer",
};

const ROW: React.CSSProperties = {
  padding: "6px 12px",
  display: "flex",
  alignItems: "center",
  gap: 8,
  borderBottom: "1px solid #f5f5f5",
  cursor: "pointer",
};

const SWATCH: React.CSSProperties = {
  width: 14,
  height: 14,
  borderRadius: 3,
  flexShrink: 0,
};

interface LayerPanelProps {
  visible: boolean;
  onToggle: () => void;
  visibility: Record<string, boolean>;
  onVisibilityChange: (id: LayerId, visible: boolean) => void;
}

export function LayerPanel({
  visible,
  onToggle,
  visibility,
  onVisibilityChange,
}: LayerPanelProps) {
  if (!visible) {
    return (
      <div style={{ position: "absolute", top: 50, right: 10, zIndex: 10 }}>
        <button
          onClick={onToggle}
          style={{
            padding: "6px 12px",
            borderRadius: 6,
            border: "1px solid #ccc",
            background: "#fff",
            cursor: "pointer",
            fontSize: 12,
            boxShadow: "0 1px 4px rgba(0,0,0,0.1)",
          }}
        >
          🗂 图层
        </button>
      </div>
    );
  }

  return (
    <div style={PANEL}>
      <div style={HEADER} onClick={onToggle}>
        <span>🗂 图层管理</span>
        <span style={{ color: "#999", fontSize: 11 }}>收起</span>
      </div>
      {LAYERS.map((layer) => {
        const isVisible = visibility[layer.id] !== false;
        return (
          <div
            key={layer.id}
            style={ROW}
            onClick={() => onVisibilityChange(layer.id, !isVisible)}
          >
            <input
              type="checkbox"
              checked={isVisible}
              onChange={(e) => {
                e.stopPropagation();
                onVisibilityChange(layer.id, e.target.checked);
              }}
              style={{ cursor: "pointer" }}
            />
            <div
              style={{
                ...SWATCH,
                background: isVisible ? layer.color : "#ddd",
              }}
            />
            <span style={{ flex: 1, color: isVisible ? "#333" : "#ccc" }}>
              {layer.label}
            </span>
          </div>
        );
      })}
      <div
        style={{
          padding: "6px 12px",
          color: "#999",
          fontSize: 10,
          borderTop: "1px solid #eee",
        }}
      >
        勾选切换图层显示 · 点击行切换
      </div>
    </div>
  );
}
