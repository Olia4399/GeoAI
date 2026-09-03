import { useState, type FormEvent } from "react";
import { useAppStore } from "../../store";

const S: Record<string, React.CSSProperties> = {
  container: {
    padding: 12,
    borderBottom: "1px solid #e0e0e0",
    background: "#fff",
  },
  title: { fontSize: 14, fontWeight: 600, marginBottom: 8, color: "#333" },
  form: { display: "flex", gap: 8 },
  input: {
    flex: 1,
    padding: "8px 12px",
    borderRadius: 6,
    border: "1px solid #d0d0d0",
    fontSize: 13,
    outline: "none",
  },
  btn: {
    padding: "8px 16px",
    borderRadius: 6,
    border: "none",
    background: "#1a237e",
    color: "#fff",
    fontSize: 13,
    cursor: "pointer",
    whiteSpace: "nowrap" as const,
  },
  cancelBtn: {
    padding: "8px 16px",
    borderRadius: 6,
    border: "1px solid #d32f2f",
    background: "#fff",
    color: "#d32f2f",
    fontSize: 13,
    cursor: "pointer",
    whiteSpace: "nowrap" as const,
  },
  hint: { fontSize: 11, color: "#999", marginTop: 6 },
  suggestions: {
    display: "flex",
    flexDirection: "column" as const,
    gap: 6,
    marginTop: 10,
  },
  pill: {
    display: "inline-block",
    width: "fit-content",
    padding: "6px 14px",
    borderRadius: 20,
    border: "1px solid #d0d0d0",
    background: "#fafafa",
    color: "#444",
    fontSize: 12,
    cursor: "pointer",
    textAlign: "left" as const,
    transition: "all 0.15s",
    whiteSpace: "nowrap" as const,
  },
};

const RECOMMENDED_QUERIES = [
  "朝阳区哪里适合开咖啡店",
  "国贸周边 500 米内有哪些银行",
  "三里屯到望京最近路线",
  "朝阳区咖啡店核密度热力",
  "国贸与望京的商业设施对比",
];

export function ChatPanel() {
  const [input, setInput] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(true);
  const submitQuery = useAppStore((s) => s.submitQuery);
  const cancelQuery = useAppStore((s) => s.cancelQuery);
  const loading = useAppStore((s) => s.loading);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    submitQuery(text);
    setInput("");
    setShowSuggestions(true);
  };

  const handlePillClick = (q: string) => {
    setInput(q);
    setShowSuggestions(false);
  };

  return (
    <div style={S.container}>
      <div style={S.title}>💬 自然语言空间分析</div>
      <form style={S.form} onSubmit={handleSubmit}>
        <input
          style={S.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="朝阳区哪里适合开咖啡店"
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
      {/* 推荐语句 */}
      {showSuggestions && (
        <div style={S.suggestions}>
          {RECOMMENDED_QUERIES.map((q) => (
            <button
              key={q}
              style={S.pill}
              type="submit"
              disabled={loading}
              onClick={() => handlePillClick(q)}
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
