import { useState } from "react";
import { useAppStore } from "../../store";
import { Header } from "./Header";
import { MapView } from "../map/MapView";
import { CesiumView } from "../map/CesiumView";
import { ChatPanel } from "../chat/ChatPanel";
import { MessageList } from "../chat/MessageList";

const LAYOUT_STYLE: Record<string, React.CSSProperties> = {
  container: {
    width: "100%",
    height: "100%",
    display: "flex",
    flexDirection: "column",
  },
  header: {
    height: 48,
    flexShrink: 0,
  },
  body: {
    flex: 1,
    display: "flex",
    overflow: "hidden",
  },
  sidebar: {
    width: 360,
    flexShrink: 0,
    display: "flex",
    flexDirection: "column",
    borderRight: "1px solid #e0e0e0",
    background: "#fafafa",
  },
  mapArea: {
    flex: 1,
    position: "relative" as const,
  },
};

export function AppLayout() {
  const mapMode = useAppStore((s) => s.mapMode);
  const [showReport, setShowReport] = useState(false);

  return (
    <div style={LAYOUT_STYLE.container}>
      <div style={LAYOUT_STYLE.header}>
        <Header />
      </div>
      <div style={LAYOUT_STYLE.body}>
        <div style={LAYOUT_STYLE.sidebar}>
          <ChatPanel />
          <MessageList />
        </div>
        <div style={LAYOUT_STYLE.mapArea}>
          {mapMode === "2d" ? <MapView /> : <CesiumView />}
        </div>
      </div>
    </div>
  );
}
