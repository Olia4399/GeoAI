import { useAppStore } from "../../store";
import ReactMarkdown from "react-markdown";

const LIST_STYLE: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    overflow: "auto",
    padding: 12,
  },
  card: {
    background: "#fff",
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    border: "1px solid #e8e8e8",
    fontSize: 13,
    lineHeight: 1.6,
  },
  intent: {
    fontSize: 12,
    color: "#666",
    marginBottom: 6,
  },
  badge: {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: 10,
    fontSize: 11,
    background: "#e8eaf6",
    color: "#1a237e",
    marginRight: 6,
    marginBottom: 4,
  },
  report: {
    whiteSpace: "pre-wrap" as const,
    color: "#333",
    "& p": { margin: "4px 0" },
    "& h2": { fontSize: 15, fontWeight: 600, marginTop: 12 },
    "& table": { width: "100%", fontSize: 12, borderCollapse: "collapse" as const },
    "& th, & td": { border: "1px solid #ddd", padding: "4px 8px", textAlign: "left" as const },
  },
  error: {
    color: "#d32f2f",
    background: "#ffebee",
    borderColor: "#ffcdd2",
  },
  loading: {
    color: "#666",
    fontStyle: "italic",
  },
  empty: {
    color: "#bbb",
    textAlign: "center" as const,
    padding: 40,
    fontSize: 14,
  },
};

export function MessageList() {
  const agentResponse = useAppStore((s) => s.agentResponse);
  const loading = useAppStore((s) => s.loading);
  const error = useAppStore((s) => s.error);

  if (!agentResponse && !loading && !error) {
    return (
      <div style={LIST_STYLE.container}>
        <div style={LIST_STYLE.empty}>
          👆 在上方输入空间分析问题，<br />
          AI Agent 将自动规划并执行分析
        </div>
      </div>
    );
  }

  return (
    <div style={LIST_STYLE.container}>
      {loading && (
        <div style={{ ...LIST_STYLE.card, ...LIST_STYLE.loading }}>
          🧠 Spatial Agent 正在分析中...
        </div>
      )}

      {error && (
        <div style={{ ...LIST_STYLE.card, ...LIST_STYLE.error }}>
          ⚠️ {typeof error === "object" ? JSON.stringify(error) : String(error)}
        </div>
      )}

      {agentResponse && (
        <>
          {/* 意图卡片 */}
          <div style={LIST_STYLE.card}>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>🎯 意图识别</div>
            <div style={LIST_STYLE.intent}>
              任务: {agentResponse.intent.task_type} &nbsp;|&nbsp;
              位置: {agentResponse.intent.location}
            </div>
            {agentResponse.intent.criteria?.length > 0 && (
              <div>
                {agentResponse.intent.criteria.map((c) => (
                  <span key={c} style={LIST_STYLE.badge}>
                    {c}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* 执行步骤卡片 */}
          {agentResponse.steps?.length > 0 && (
            <div style={LIST_STYLE.card}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>📋 执行步骤</div>
              {agentResponse.steps.map((s, i) => (
                <div key={i} style={LIST_STYLE.intent}>
                  {i + 1}. {s.tool ? `调用: ${s.tool}` : s.content?.slice(0, 80) || s.action}
                </div>
              ))}
            </div>
          )}

          {/* 结果卡片 */}
          {agentResponse.results?.length > 0 && (
            <div style={LIST_STYLE.card}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>📊 空间分析结果</div>
              <div style={{ fontSize: 12, color: "#666" }}>
                已返回 {agentResponse.results.flatMap((r) => r?.features || []).length} 个空间要素 → 在地图上查看
              </div>
            </div>
          )}

          {/* 报告卡片 */}
          {agentResponse.report && (
            <div style={LIST_STYLE.card}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>📝 分析报告</div>
              <div style={LIST_STYLE.report}>
                <ReactMarkdown>{agentResponse.report}</ReactMarkdown>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
