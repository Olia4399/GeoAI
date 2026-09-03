import type { AgentError } from "../../types";

/* ================================================================
   统一报错组件：分类展示错误 + 友好标题 + 技术细节 + 排查提示 + 重试
   各调用方只需把任意错误交给 toAgentError() 归一化后传入即可
   ================================================================ */

const TYPE_META: Record<
  AgentError["type"],
  { icon: string; color: string; defaultTitle: string }
> = {
  network: { icon: "🌐", color: "#c62828", defaultTitle: "无法连接后端服务" },
  http: { icon: "🖥️", color: "#c62828", defaultTitle: "请求失败" },
  sse: { icon: "⚡", color: "#e65100", defaultTitle: "分析流程中断" },
  timeout: { icon: "⏱️", color: "#e65100", defaultTitle: "请求超时" },
  llm: { icon: "🤖", color: "#c62828", defaultTitle: "大模型调用失败" },
  spatial: { icon: "🗺️", color: "#c62828", defaultTitle: "空间服务调用失败" },
  unknown: { icon: "⚠️", color: "#c62828", defaultTitle: "请求出错" },
};

interface ErrorCardProps {
  error: AgentError;
  /** 可选：重试回调（不传则不显示重试按钮） */
  onRetry?: () => void;
}

export function ErrorCard({ error, onRetry }: ErrorCardProps) {
  const meta = TYPE_META[error.type] || TYPE_META.unknown;
  return (
    <div
      style={{
        background: "#fff5f5",
        border: "1px solid #ffcdd2",
        borderRadius: 8,
        padding: 14,
        marginBottom: 10,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          color: meta.color,
          fontWeight: 600,
          fontSize: 13,
        }}
      >
        <span style={{ fontSize: 16 }}>{meta.icon}</span>
        <span>{error.title || meta.defaultTitle}</span>
        {error.status != null && (
          <span style={{ fontSize: 11, fontWeight: 400, color: "#999" }}>
            HTTP {error.status}
          </span>
        )}
      </div>
      {error.detail && (
        <div
          style={{
            marginTop: 8,
            fontSize: 12,
            color: "#666",
            background: "#fff",
            border: "1px solid #f0d0d0",
            borderRadius: 6,
            padding: "8px 10px",
            wordBreak: "break-all",
            maxHeight: 120,
            overflow: "auto",
            fontFamily: "Consolas, Monaco, monospace",
            lineHeight: 1.5,
          }}
        >
          {error.detail}
        </div>
      )}
      {error.hint && (
        <div style={{ marginTop: 8, fontSize: 12, color: "#555", lineHeight: 1.5 }}>
          💡 {error.hint}
        </div>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            marginTop: 10,
            padding: "5px 14px",
            borderRadius: 6,
            border: "1px solid #1a237e",
            background: "#fff",
            color: "#1a237e",
            cursor: "pointer",
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          🔄 重试
        </button>
      )}
    </div>
  );
}
