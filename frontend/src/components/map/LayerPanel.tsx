export type LayerId =
  | "poi"
  | "roads"
  | "buildings"
  | "districts"
  | "analysis"
  | "draw";

export interface LayerDef {
  id: LayerId;
  label: string;
  color: string;
  /** Mapbox style 图层 id 前缀：勾选后真正 setLayoutProperty 显隐 */
  mapPrefix?: string;
  /** 底图无对应数据，仅占位展示 */
  disabled?: boolean;
}

export const LAYERS: LayerDef[] = [
  { id: "poi", label: "POI 兴趣点", color: "#4488ff", mapPrefix: "poi" },
  { id: "roads", label: "道路网络", color: "#888888", mapPrefix: "road" },
  { id: "buildings", label: "建筑", color: "#ff9800", mapPrefix: "building" },
  { id: "analysis", label: "分析结果", color: "#4caf50", mapPrefix: "agent-result" },
  { id: "draw", label: "框选区域", color: "#1a237e", mapPrefix: "draw-geometry" },
  { id: "districts", label: "行政区划", color: "#9c27b0", disabled: true },
];

const PANEL: React.CSSProperties = {
  position: "absolute",
  top: 50,
  right: 10,
  zIndex: 10,
  background: "#fff",
  borderRadius: 8,
  boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
  width: 220,
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
      <div style={{ position: "absolute", top: 10, right: 50, zIndex: 10 }}>
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
        const disabled = Boolean(layer.disabled);
        return (
          <div
            key={layer.id}
            style={{
              ...ROW,
              opacity: disabled ? 0.55 : 1,
              cursor: disabled ? "default" : "pointer",
            }}
            onClick={() => {
              if (!disabled) onVisibilityChange(layer.id, !isVisible);
            }}
          >
            <input
              type="checkbox"
              checked={isVisible}
              disabled={disabled}
              onChange={(e) => {
                e.stopPropagation();
                onVisibilityChange(layer.id, e.target.checked);
              }}
              style={{ cursor: disabled ? "default" : "pointer" }}
            />
            <div
              style={{
                ...SWATCH,
                background: isVisible && !disabled ? layer.color : "#ddd",
              }}
            />
            <span
              style={{
                flex: 1,
                color: isVisible && !disabled ? "#333" : "#ccc",
              }}
            >
              {layer.label}
            </span>
            {disabled && (
              <span style={{ fontSize: 10, color: "#bbb" }}>暂无</span>
            )}
          </div>
        );
      })}
      {/* 分析评分图例：与 MapView 的 score 插值着色一致 */}
      <div style={{ padding: "8px 12px", borderTop: "1px solid #eee" }}>
        <div
          style={{
            fontSize: 11,
            color: "#666",
            fontWeight: 600,
            marginBottom: 4,
          }}
        >
          分析评分图例
        </div>
        <div
          style={{
            height: 8,
            borderRadius: 4,
            background:
              "linear-gradient(to right, #f44336 0%, #ff9800 20%, #ffeb3b 40%, #4caf50 60%, #1b5e20 80%, #003300 100%)",
          }}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 10,
            color: "#999",
            marginTop: 2,
          }}
        >
          <span>0</span>
          <span>20</span>
          <span>40</span>
          <span>60</span>
          <span>80</span>
          <span>100</span>
        </div>
        <div style={{ fontSize: 10, color: "#999", marginTop: 4 }}>
          分数越高越适合（绿），越低越不适合（红）
        </div>
      </div>
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
