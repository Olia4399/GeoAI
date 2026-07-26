import { useState, type FormEvent } from "react";
import { useAppStore } from "../../store";

const PANEL_STYLE: Record<string, React.CSSProperties> = {
  container: {
    padding: 12,
    borderBottom: "1px solid #e0e0e0",
    background: "#fff",
  },
  title: {
    fontSize: 14,
    fontWeight: 600,
    marginBottom: 8,
    color: "#333",
  },
  form: {
    display: "flex",
    gap: 8,
  },
  input: {
    flex: 1,
    padding: "8px 12px",
    borderRadius: 6,
    border: "1px solid #d0d0d0",
    fontSize: 13,
    outline: "none",
  },
  button: {
    padding: "8px 16px",
    borderRadius: 6,
    border: "none",
    background: "#1a237e",
    color: "#fff",
    fontSize: 13,
    cursor: "pointer",
    whiteSpace: "nowrap" as const,
  },
  hint: {
    fontSize: 11,
    color: "#999",
    marginTop: 6,
  },
};

export function ChatPanel() {
  const [input, setInput] = useState("");
  const submitQuery = useAppStore((s) => s.submitQuery);
  const loading = useAppStore((s) => s.loading);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    submitQuery(text);
    setInput("");
  };

  return (
    <div style={PANEL_STYLE.container}>
      <div style={PANEL_STYLE.title}>💬 自然语言空间分析</div>
      <form style={PANEL_STYLE.form} onSubmit={handleSubmit}>
        <input
          style={PANEL_STYLE.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder='例如: "计算北京国贸周边500米的缓冲区"'
          disabled={loading}
        />
        <button style={PANEL_STYLE.button} type="submit" disabled={loading}>
          {loading ? "分析中..." : "发送"}
        </button>
      </form>
      <div style={PANEL_STYLE.hint}>
        支持: 选址分析 · 缓冲区分析 · 距离计算 · 适宜性评价
      </div>
    </div>
  );
}
