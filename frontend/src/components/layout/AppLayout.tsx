import { useState, useCallback, useRef, useEffect } from "react";
import { useAppStore } from "../../store";
import { Header } from "./Header";
import { MapView } from "../map/MapView";
import { CesiumView } from "../map/CesiumView";
import { ChatPanel } from "../chat/ChatPanel";
import { MessageList } from "../chat/MessageList";
import { HistoryPanel } from "../chat/HistoryPanel";

type PanelTab = "chat" | "history";

const MIN_SIDEBAR = 300;
const MAX_SIDEBAR = 600;
const DEFAULT_SIDEBAR = 360;

export function AppLayout() {
  const mapMode = useAppStore((s) => s.mapMode);
  const [tab, setTab] = useState<PanelTab>("chat");
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_SIDEBAR);
  const dragging = useRef(false);

  const onMouseDown = useCallback(() => {
    dragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const w = Math.min(MAX_SIDEBAR, Math.max(MIN_SIDEBAR, e.clientX));
      setSidebarWidth(w);
    };
    const onMouseUp = () => {
      dragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ height: 48, flexShrink: 0 }}><Header /></div>
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* 可拖拽侧栏 */}
        <div style={{
          width: sidebarWidth,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid #e0e0e0",
          background: "#fafafa",
        }}>
          <div style={{ display: "flex", borderBottom: "1px solid #e0e0e0", background: "#fff" }}>
            {(["chat", "history"] as PanelTab[]).map((t) => (
              <div
                key={t}
                onClick={() => setTab(t)}
                style={{
                  flex: 1,
                  padding: "10px 0",
                  textAlign: "center",
                  fontSize: 13,
                  cursor: "pointer",
                  fontWeight: 500,
                  borderBottom: tab === t ? "2px solid #1a237e" : "2px solid transparent",
                  color: tab === t ? "#1a237e" : "#666",
                }}
              >
                {t === "chat" ? "💬 分析" : "📁 历史"}
              </div>
            ))}
          </div>
          {tab === "chat" ? (
            <>
              <ChatPanel />
              <MessageList />
            </>
          ) : (
            <HistoryPanel />
          )}
        </div>

        {/* 拖拽手柄 */}
        <div
          onMouseDown={onMouseDown}
          style={{
            width: 5,
            cursor: "col-resize",
            background: "transparent",
            flexShrink: 0,
            zIndex: 20,
            transition: "background 0.15s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#1a237e33")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        />

        {/* 地图区域 */}
        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          {mapMode === "2d" ? <MapView /> : <CesiumView />}
        </div>
      </div>
    </div>
  );
}
