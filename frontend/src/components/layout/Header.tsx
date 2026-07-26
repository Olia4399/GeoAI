import { useAppStore } from "../../store";
import type { MapMode } from "../../types";

const HEADER_STYLE: Record<string, React.CSSProperties> = {
  bar: {
    height: 48,
    display: "flex",
    alignItems: "center",
    padding: "0 16px",
    background: "linear-gradient(135deg, #1a237e 0%, #0d47a1 100%)",
    color: "#fff",
    gap: 16,
  },
  title: {
    fontSize: 16,
    fontWeight: 700,
    letterSpacing: 0.5,
  },
  spacer: { flex: 1 },
  modeBtn: {
    padding: "4px 14px",
    borderRadius: 4,
    border: "1px solid rgba(255,255,255,0.3)",
    background: "transparent",
    color: "#fff",
    cursor: "pointer",
    fontSize: 13,
  },
  modeBtnActive: {
    background: "rgba(255,255,255,0.25)",
    border: "1px solid rgba(255,255,255,0.6)",
  },
};

export function Header() {
  const mapMode = useAppStore((s) => s.mapMode);
  const setMapMode = useAppStore((s) => s.setMapMode);

  return (
    <div style={HEADER_STYLE.bar}>
      <span style={HEADER_STYLE.title}>🌏 GeoAI 城市空间智能分析平台</span>
      <span style={HEADER_STYLE.spacer} />
      <span style={{ fontSize: 12, opacity: 0.7 }}>Phase 1 — Foundation</span>
      <button
        style={{
          ...HEADER_STYLE.modeBtn,
          ...(mapMode === "2d" ? HEADER_STYLE.modeBtnActive : {}),
        }}
        onClick={() => setMapMode("2d")}
      >
        2D 地图
      </button>
      <button
        style={{
          ...HEADER_STYLE.modeBtn,
          ...(mapMode === "3d" ? HEADER_STYLE.modeBtnActive : {}),
        }}
        onClick={() => setMapMode("3d")}
      >
        3D 地球
      </button>
    </div>
  );
}
