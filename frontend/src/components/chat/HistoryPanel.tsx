import { useEffect, useState } from "react";
import { useAppStore } from "../../store";
import { agentApi } from "../../services/agent";
import ReactMarkdown from "react-markdown";

interface HistoryItem {
  id: string;
  created_at: string;
  query: string;
  intent: { task_type: string; location: string } | null;
}

interface DetailItem extends HistoryItem {
  steps: any[];
  results: any[];
  report: string;
}

const STYLE = {
  container: { flex: 1, overflow: "auto", padding: 12 },
  listItem: {
    padding: "8px 12px",
    borderBottom: "1px solid #eee",
    cursor: "pointer",
    fontSize: 13,
  },
  listItemHover: { background: "#f0f0f0" },
  badge: {
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 8,
    fontSize: 10,
    background: "#e8eaf6",
    color: "#1a237e",
    marginRight: 6,
  },
  btn: {
    padding: "4px 10px",
    borderRadius: 4,
    border: "1px solid #ccc",
    background: "#fff",
    cursor: "pointer",
    fontSize: 11,
  },
  backBtn: {
    padding: "4px 12px",
    border: "none",
    background: "transparent",
    color: "#1a237e",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
  },
};

type View = "list" | "detail" | "compare";

export function HistoryPanel() {
  const [view, setView] = useState<View>("list");
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [detail, setDetail] = useState<DetailItem | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchList = async () => {
    setLoading(true);
    try {
      const res = await agentApi.history();
      setItems(res.items || []);
    } catch {
      setItems([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchList();
  }, []);

  const openDetail = async (id: string) => {
    setLoading(true);
    try {
      const res = await agentApi.historyDetail(id);
      setDetail(res);
      setView("detail");
    } catch { /* ignore */ }
    setLoading(false);
  };

  const toggleCompare = (id: string) => {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id].slice(0, 2)
    );
  };

  if (view === "detail" && detail) {
    return (
      <div style={STYLE.container}>
        <button style={STYLE.backBtn} onClick={() => { setView("list"); setDetail(null); }}>
          ← 返回列表
        </button>
        <div style={{ fontSize: 12, color: "#999", margin: "4px 0" }}>
          {detail.created_at?.slice(0, 16)}
        </div>
        <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>
          {detail.query}
        </div>
        {detail.intent && (
          <div style={{ marginBottom: 10 }}>
            <span style={STYLE.badge}>{detail.intent.task_type}</span>
            <span style={STYLE.badge}>{detail.intent.location}</span>
          </div>
        )}
        {detail.steps?.length > 0 && (
          <div style={{ fontSize: 12, color: "#666", marginBottom: 8 }}>
            📋 {detail.steps.length} 个分析步骤
          </div>
        )}
        {detail.results?.length > 0 && (
          <div style={{ fontSize: 12, color: "#666", marginBottom: 8 }}>
            📊 {detail.results.length} 个结果集
          </div>
        )}
        <div style={{ background: "#fff", borderRadius: 8, padding: 12, border: "1px solid #e8e8e8" }}>
          <ReactMarkdown>{detail.report || "无报告"}</ReactMarkdown>
        </div>
      </div>
    );
  }

  return (
    <div style={STYLE.container}>
      <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>📁 分析历史</span>
        <button style={STYLE.btn} onClick={fetchList} disabled={loading}>
          {loading ? "..." : "刷新"}
        </button>
      </div>

      {compareIds.length > 0 && (
        <div style={{ marginBottom: 8, fontSize: 12 }}>
          已选 {compareIds.length}/2 项
          {compareIds.length === 2 && (
            <span style={{ marginLeft: 8, color: "#1a237e", cursor: "pointer" }}
              onClick={() => setView("compare")}>
              对比 →
            </span>
          )}
        </div>
      )}

      {items.length === 0 && !loading && (
        <div style={{ color: "#bbb", textAlign: "center", padding: 20, fontSize: 13 }}>
          暂无历史分析，开始一次空间分析后自动保存
        </div>
      )}

      {items.map((item) => (
        <div
          key={item.id}
          style={{
            ...STYLE.listItem,
            background: compareIds.includes(item.id) ? "#e8eaf6" : "transparent",
          }}
          onClick={() => openDetail(item.id)}
        >
          <div style={{ fontWeight: 500, marginBottom: 4 }}>{item.query.slice(0, 60)}</div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            {item.intent && <span style={STYLE.badge}>{item.intent.task_type}</span>}
            <span style={{ fontSize: 11, color: "#999" }}>
              {item.created_at?.slice(0, 16).replace("T", " ")}
            </span>
            <span style={{ flex: 1 }} />
            <button
              style={{ ...STYLE.btn, fontSize: 10 }}
              onClick={(e) => { e.stopPropagation(); toggleCompare(item.id); }}
            >
              {compareIds.includes(item.id) ? "取消" : "对比"}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
