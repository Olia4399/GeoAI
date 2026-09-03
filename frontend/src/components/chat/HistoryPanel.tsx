import { useEffect, useState } from "react";
import { agentApi, toAgentError } from "../../services/agent";
import type { AgentError } from "../../types";
import { ReportContent, COLORS } from "./ReportRenderer";
import { ErrorCard } from "./ErrorCard";

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
    padding: "10px 12px",
    borderBottom: "1px solid #eee",
    cursor: "pointer",
    fontSize: 13,
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  badge: {
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: 8,
    fontSize: 10,
    background: "#e8eaf6",
    color: "#1a237e",
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

/** 圆形对比按钮：中空白色；选中后中心显示小实心圆点 */
const circleBtn = (selected: boolean): React.CSSProperties => ({
  width: 24,
  height: 24,
  borderRadius: 1000,
  border: selected ? "1.5px solid #1a237e" : "1.5px solid #bbb",
  background: "#fff",
  cursor: "pointer",
  padding: 0,
  flexShrink: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
});

type View = "list" | "detail" | "compare";

export function HistoryPanel() {
  const [view, setView] = useState<View>("list");
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [detail, setDetail] = useState<DetailItem | null>(null);
  const [compareItems, setCompareItems] = useState<DetailItem[]>([]);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<AgentError | null>(null);

  const fetchList = async () => {
    setLoading(true);
    try {
      const res = await agentApi.history();
      setItems(res.items || []);
      setErr(null);
    } catch (e) {
      setItems([]);
      setErr(toAgentError(e));
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
      setErr(null);
      setView("detail");
    } catch (e) {
      setErr(toAgentError(e));
    }
    setLoading(false);
  };

  const toggleCompare = (id: string) => {
    setCompareIds((prev) =>
      prev.includes(id)
        ? prev.filter((x) => x !== id)
        : [...prev, id].slice(0, 2),
    );
  };

  /** 点击"对比分析"按钮才真正开始对比操作 */
  const startCompare = async () => {
    if (compareIds.length < 2) return;
    setLoading(true);
    try {
      const [a, b] = await Promise.all(
        compareIds.map((id) => agentApi.historyDetail(id)),
      );
      setCompareItems([a, b]);
      setErr(null);
      setView("compare");
    } catch (e) {
      setErr(toAgentError(e));
    }
    setLoading(false);
  };

  const renderCompareCard = (d: DetailItem, tag: string) => (
    <div
      style={{
        marginTop: 10,
        background: "#fff",
        borderRadius: 8,
        padding: 12,
        border: "1px solid #e8e8e8",
      }}
    >
      <div
        style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}
      >
        <span style={{ fontWeight: 600, fontSize: 13, color: COLORS.heading }}>
          {tag} {d.query.slice(0, 40)}
        </span>
        <span style={{ fontSize: 11, color: "#999" }}>
          {d.created_at?.slice(0, 16).replace("T", " ")}
        </span>
      </div>
      {d.intent && (
        <div style={{ margin: "6px 0" }}>
          <span style={STYLE.badge}>{d.intent.task_type}</span>
          {d.intent.location && (
            <span style={STYLE.badge}>{d.intent.location}</span>
          )}
        </div>
      )}
      <ReportContent>{d.report || "无报告"}</ReportContent>
    </div>
  );

  if (view === "detail" && detail) {
    return (
      <div style={STYLE.container}>
        <button
          style={STYLE.backBtn}
          onClick={() => {
            setView("list");
            setDetail(null);
          }}
        >
          ← 返回列表
        </button>
        {err && <ErrorCard error={err} onRetry={() => detail && openDetail(detail.id)} />}
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
        <div
          style={{
            background: "#fff",
            borderRadius: 8,
            padding: 12,
            border: "1px solid #e8e8e8",
          }}
        >
          <ReportContent>{detail.report || "无报告"}</ReportContent>
        </div>
      </div>
    );
  }

  if (view === "compare" && compareItems.length === 2) {
    return (
      <div style={STYLE.container}>
        <button style={STYLE.backBtn} onClick={() => setView("list")}>
          ← 返回列表
        </button>
        {err && <ErrorCard error={err} onRetry={startCompare} />}
        {renderCompareCard(compareItems[0], "🅰")}
        {renderCompareCard(compareItems[1], "🅱")}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={STYLE.container}>
        <div
          style={{
            fontWeight: 600,
            fontSize: 14,
            marginBottom: 8,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>📁 分析历史</span>
          <button style={STYLE.btn} onClick={fetchList} disabled={loading}>
            {loading ? "..." : "刷新"}
          </button>
        </div>

        {err && <ErrorCard error={err} onRetry={fetchList} />}

        {items.length === 0 && !loading && (
          <div
            style={{
              color: "#bbb",
              textAlign: "center",
              padding: 20,
              fontSize: 13,
            }}
          >
            暂无历史分析，开始一次空间分析后自动保存
          </div>
        )}

        {items.map((item) => {
          const selected = compareIds.includes(item.id);
          return (
            <div
              key={item.id}
              style={{
                ...STYLE.listItem,
                background: selected ? "#f0f4ff" : "transparent",
              }}
              onClick={() => openDetail(item.id)}
            >
              {/* 左侧容器：标题 + 底部工具/时间 row */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontWeight: 500,
                    color: COLORS.heading,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {item.query}
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    marginTop: 5,
                  }}
                >
                  {item.intent && (
                    <span style={STYLE.badge}>{item.intent.task_type}</span>
                  )}
                  {item.intent?.location && (
                    <span style={STYLE.badge}>{item.intent.location}</span>
                  )}
                  <span style={{ fontSize: 11, color: "#999" }}>
                    {item.created_at?.slice(0, 16).replace("T", " ")}
                  </span>
                </div>
              </div>
              {/* 圆形对比按钮：中空白色，选中后中心实心圆点，垂直居中 */}
              <button
                style={circleBtn(selected)}
                title={selected ? "取消对比" : "加入对比"}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleCompare(item.id);
                }}
              >
                {selected && (
                  <span
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: "50%",
                      background: "#1a237e",
                    }}
                  />
                )}
              </button>
            </div>
          );
        })}
      </div>

      {/* 底部对比抽屉：选中任意项后升起；点击"对比分析"才开始对比 */}
      {compareIds.length > 0 && (
        <div
          style={{
            flexShrink: 0,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "10px 14px",
            background: "#fff",
            borderTop: "1px solid #e0e0e0",
            boxShadow: "0 -2px 8px rgba(0,0,0,0.08)",
            fontSize: 13,
          }}
        >
          <span>
            已选中{" "}
            <strong style={{ color: "#1a237e" }}>{compareIds.length}</strong>/2 项
          </span>
          <button
            onClick={startCompare}
            disabled={compareIds.length < 2}
            style={{
              padding: "6px 16px",
              borderRadius: 1000,
              border: "none",
              background: compareIds.length >= 2 ? "#1a237e" : "#ccc",
              color: "#fff",
              cursor: compareIds.length >= 2 ? "pointer" : "not-allowed",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            对比分析
          </button>
        </div>
      )}
    </div>
  );
}
