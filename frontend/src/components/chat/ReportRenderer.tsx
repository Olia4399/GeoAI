/**
 * 报告渲染共享模块 — MessageList + HistoryPanel 共用
 * 统一配色、表格、标题、代码块、分数徽标等样式
 */

import ReactMarkdown from "react-markdown";

/* ================================================================
   配色系统
   ================================================================ */

export const COLORS = {
  primary: "#1a237e",
  accent: "#0d47a1",
  success: "#2e7d32",
  warning: "#e65100",
  danger: "#c62828",
  text: "#333",
  textLight: "#666",
  heading: "#1a1a1a",
  bg: "#fff",
  bgAlt: "#f8f9fa",
  border: "#e0e0e0",
  code: "#f5f5f5",
  tableHeader: "#e8eaf6",
  blockquoteBorder: "#1a237e",
};

/* ================================================================
   分数徽标
   ================================================================ */

export function ScoreBadge({ score }: { score: number }) {
  let bg = COLORS.success;
  let label = "优秀";
  if (score < 40) { bg = COLORS.danger; label = "较差"; }
  else if (score < 60) { bg = COLORS.warning; label = "一般"; }
  else if (score < 80) { bg = COLORS.accent; label = "良好"; }

  return (
    <span style={{
      display: "inline-block",
      padding: "1px 8px",
      borderRadius: 10,
      background: bg,
      color: "#fff",
      fontSize: 11,
      fontWeight: 600,
      marginLeft: 4,
    }}>
      {score} · {label}
    </span>
  );
}

/* ================================================================
   Markdown 组件覆写
   ================================================================ */

export const markdownComponents: any = {
  table: ({ children }: any) => (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, margin: "10px 0" }}>
      {children}
    </table>
  ),
  thead: ({ children }: any) => (
    <thead style={{ background: COLORS.tableHeader }}>{children}</thead>
  ),
  th: ({ children }: any) => (
    <th style={{
      padding: "6px 10px", textAlign: "left", fontWeight: 600,
      borderBottom: `2px solid ${COLORS.primary}`, color: COLORS.primary, fontSize: 12,
    }}>
      {children}
    </th>
  ),
  td: ({ children }: any) => (
    <td style={{
      padding: "6px 10px", borderBottom: `1px solid ${COLORS.border}`, verticalAlign: "top",
    }}>
      {children}
    </td>
  ),
  h2: ({ children }: any) => (
    <h2 style={{
      fontSize: 16, fontWeight: 700, color: COLORS.heading,
      margin: "16px 0 8px", paddingBottom: 6, borderBottom: `2px solid ${COLORS.border}`,
    }}>
      {children}
    </h2>
  ),
  h3: ({ children }: any) => (
    <h3 style={{ fontSize: 14, fontWeight: 600, color: COLORS.accent, margin: "12px 0 6px" }}>
      {children}
    </h3>
  ),
  p: ({ children }: any) => {
    const text = String(children);
    const scoreMatch = text.match(/(?:得分|score|评分)[:：]?\s*(\d{1,3})/i);
    if (scoreMatch) {
      const score = parseInt(scoreMatch[1]);
      return (
        <p style={{ margin: "4px 0", color: COLORS.text, lineHeight: 1.7, fontSize: 13 }}>
          {children}
          {score >= 0 && score <= 100 && <ScoreBadge score={score} />}
        </p>
      );
    }
    return (
      <p style={{ margin: "4px 0", color: COLORS.text, lineHeight: 1.7, fontSize: 13 }}>
        {children}
      </p>
    );
  },
  // 注意：react-markdown v10 不再传 inline prop（实测行内 code 只有 {node, children}）。
  // 用 className（language-xxx）或内容含换行（围栏代码块文本末尾必带 \n）区分块级与行内，
  // 否则行内代码会全部误渲染成深色块，把列表文字切成"一词一框"。
  code: ({ className, children }: any) => {
    const isBlock =
      Boolean(className) || (typeof children === "string" && children.includes("\n"));
    if (isBlock) {
      // 块级代码的深色盒样式统一由 pre 承载，这里只保留等宽字体
      return (
        <code style={{
          background: "transparent", color: "inherit",
          fontFamily: "Consolas, Monaco, monospace", fontSize: 12,
        }}>
          {children}
        </code>
      );
    }
    return (
      <code style={{
        background: COLORS.code, padding: "1px 5px", borderRadius: 3,
        fontSize: 12, fontFamily: "Consolas, Monaco, monospace", color: "#d32f2f",
      }}>
        {children}
      </code>
    );
  },
  pre: ({ children }: any) => (
    <pre style={{
      background: "#263238", color: "#aed581", padding: "10px 14px",
      borderRadius: 6, fontSize: 12, fontFamily: "Consolas, Monaco, monospace",
      overflow: "auto", margin: "8px 0", lineHeight: 1.6,
    }}>
      {children}
    </pre>
  ),
  ul: ({ children }: any) => (
    <ul style={{ margin: "4px 0", paddingLeft: 20, color: COLORS.text, fontSize: 13, lineHeight: 1.8 }}>
      {children}
    </ul>
  ),
  ol: ({ children }: any) => (
    <ol style={{ margin: "4px 0", paddingLeft: 20, color: COLORS.text, fontSize: 13, lineHeight: 1.8 }}>
      {children}
    </ol>
  ),
  li: ({ children }: any) => {
    const text = String(children);
    const isRisk = /风险|警告|注意|缺点|不足/.test(text);
    return <li style={{ color: isRisk ? COLORS.danger : COLORS.text }}>{children}</li>;
  },
  blockquote: ({ children }: any) => (
    <blockquote style={{
      margin: "8px 0", padding: "8px 14px", borderLeft: `4px solid ${COLORS.blockquoteBorder}`,
      background: COLORS.bgAlt, borderRadius: "0 4px 4px 0",
      color: COLORS.textLight, fontSize: 13, fontStyle: "italic",
    }}>
      {children}
    </blockquote>
  ),
  hr: () => (
    <hr style={{ border: "none", borderTop: `1px solid ${COLORS.border}`, margin: "14px 0" }} />
  ),
  a: ({ children, href }: any) => (
    <a href={href} style={{ color: COLORS.accent, textDecoration: "underline", fontWeight: 500 }}>
      {children}
    </a>
  ),
  strong: ({ children }: any) => (
    <strong style={{ fontWeight: 700, color: COLORS.heading }}>{children}</strong>
  ),
  em: ({ children }: any) => (
    <em style={{ fontStyle: "italic", color: COLORS.accent }}>{children}</em>
  ),
};

/* ================================================================
   统一报告组件
   ================================================================ */

export function ReportContent({ children }: { children: string }) {
  return (
    <div style={{ color: COLORS.text }}>
      <ReactMarkdown components={markdownComponents}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
