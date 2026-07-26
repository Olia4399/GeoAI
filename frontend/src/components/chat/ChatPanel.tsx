import { useState, type FormEvent } from "react";
import { useAppStore } from "../../store";

const S: Record<string, React.CSSProperties> = {
  container: { padding: 12, borderBottom: "1px solid #e0e0e0", background: "#fff" },
  title: { fontSize: 14, fontWeight: 600, marginBottom: 8, color: "#333" },
  form: { display: "flex", gap: 8 },
  input: { flex: 1, padding: "8px 12px", borderRadius: 6, border: "1px solid #d0d0d0", fontSize: 13, outline: "none" },
  btn: { padding: "8px 16px", borderRadius: 6, border: "none", background: "#1a237e", color: "#fff", fontSize: 13, cursor: "pointer", whiteSpace: "nowrap" as const },
  cancelBtn: { padding: "8px 16px", borderRadius: 6, border: "1px solid #d32f2f", background: "#fff", color: "#d32f2f", fontSize: 13, cursor: "pointer", whiteSpace: "nowrap" as const },
  hint: { fontSize: 11, color: "#999", marginTop: 6 },
  progress: { marginTop: 8, padding: "8px 10px", background: "#f5f5f5", borderRadius: 6, fontSize: 12 },
  step: { padding: "2px 0", color: "#666", display: "flex", alignItems: "center", gap: 6 },
  dot: { width: 6, height: 6, borderRadius: 3, background: "#4caf50", display: "inline-block" },
  dotPending: { width: 6, height: 6, borderRadius: 3, background: "#ccc", display: "inline-block" },
};

const PHASE_LABELS: Record<string, string> = {
  intent: "🎯 意图解析",
  planning: "🧠 任务规划",
  report: "📝 生成报告",
};

export function ChatPanel() {
  const [input, setInput] = useState("");
  const submitQuery = useAppStore((s) => s.submitQuery);
  const cancelQuery = useAppStore((s) => s.cancelQuery);
  const loading = useAppStore((s) => s.loading);
  const streamProgress = useAppStore((s) => s.streamProgress);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    submitQuery(text);
    setInput("");
  };

  return (
    <div style={S.container}>
      <div style={S.title}>💬 自然语言空间分析</div>
      <form style={S.form} onSubmit={handleSubmit}>
        <input
          style={S.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder='例如: "朝阳区哪里适合开咖啡店"'
          disabled={loading}
        />
        {loading ? (
          <button style={S.cancelBtn} type="button" onClick={cancelQuery}>
            取消
          </button>
        ) : (
          <button style={S.btn} type="submit" disabled={loading}>
            发送
          </button>
        )}
      </form>

      {/* SSE 实时进度 */}
      {streamProgress && (
        <div style={S.progress}>
          {["intent", "planning", "report"].map((phase) => {
            const isCurrent = streamProgress.phase === phase;
            const isDone = (
              (phase === "intent" && streamProgress.steps.length > 0) ||
              (phase === "planning" && (streamProgress.phase === "report" || streamProgress.phase === "done")) ||
              (phase === "report" && streamProgress.phase === "done")
            );
            return (
              <div key={phase} style={S.step}>
                <span style={isDone ? S.dot : isCurrent ? { ...S.dot, background: "#ff9800" } : S.dotPending} />
                <span style={{ color: isCurrent ? "#333" : "#999", fontWeight: isCurrent ? 600 : 400 }}>
                  {PHASE_LABELS[phase]}
                  {isCurrent && streamProgress.status === "running" ? "..." : ""}
                  {isDone ? " ✓" : ""}
                </span>
              </div>
            );
          })}
          {streamProgress.steps.map((s, i) => (
            <div key={i} style={{ ...S.step, paddingLeft: 18, fontSize: 11 }}>
              <span style={S.dot} />
              <span>
                {s.data?.tool ? `调用: ${s.data.tool}` : s.data?.action || `步骤 ${i + 1}`}
              </span>
            </div>
          ))}
        </div>
      )}

      <div style={S.hint}>
        选址分析 · 缓冲区 · 距离 · 密度 · 路径规划 · 适宜性评价
      </div>
    </div>
  );
}
