import { useState } from "react";
import { useAppStore } from "../../store";
import { Header } from "./Header";
import { MapView } from "../map/MapView";
import { CesiumView } from "../map/CesiumView";
import { ChatPanel } from "../chat/ChatPanel";
import { MessageList } from "../chat/MessageList";
import { HistoryPanel } from "../chat/HistoryPanel";

const LAYOUT_STYLE: Record<string, React.CSSProperties> = {
  container: { width: "100%", height: "100%", display: "flex", flexDirection: "column" },
  header: { height: 48, flexShrink: 0 },
  body: { flex: 1, display: "flex", overflow: "hidden" },
  sidebar: { width: 360, flexShrink: 0, display: "flex", flexDirection: "column", borderRight: "1px solid #e0e0e0", background: "#fafafa" },
  mapArea: { flex: 1, position: "relative" as const },
  tabs: { display: "flex", borderBottom: "1px solid #e0e0e0", background: "#fff" },
  tab: { flex: 1, padding: "10px 0", textAlign: "center" as const, fontSize: 13, cursor: "pointer", borderBottom: "2px solid transparent", fontWeight: 500 },
  tabActive: { borderBottom: "2px solid #1a237e", color: "#1a237e" },
};

type PanelTab = "chat" | "history";

export function AppLayout() {
  const mapMode = useAppStore((s) => s.mapMode);
  const [tab, setTab] = useState<PanelTab>("chat");

  return (
    <div style={LAYOUT_STYLE.container}>
      <div style={LAYOUT_STYLE.header}><Header /></div>
      <div style={LAYOUT_STYLE.body}>
        <div style={LAYOUT_STYLE.sidebar}>
          <div style={LAYOUT_STYLE.tabs}>
            <div
              style={{ ...LAYOUT_STYLE.tab, ...(tab === "chat" ? LAYOUT_STYLE.tabActive : {}) }}
              onClick={() => setTab("chat")}
            >
              💬 分析
            </div>
            <div
              style={{ ...LAYOUT_STYLE.tab, ...(tab === "history" ? LAYOUT_STYLE.tabActive : {}) }}
              onClick={() => setTab("history")}
            >
              📁 历史
            </div>
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
        <div style={LAYOUT_STYLE.mapArea}>
          {mapMode === "2d" ? <MapView /> : <CesiumView />}
        </div>
      </div>
    </div>
  );
}
