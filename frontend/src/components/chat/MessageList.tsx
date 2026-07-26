import { useState } from "react";
import { useAppStore } from "../../store";
import { ReportContent, COLORS } from "./ReportRenderer";

/* ================================================================
   组件 — 样式系统从 ReportRenderer 共享
   ================================================================ */

/** 截断步骤中的原始 Markdown —— 只保留第一句话 */
function truncateStep(text: string): string {
  const cleaned = text
    .replace(/^#{1,4}\s+.*$/gm, "")
    .replace(/\|.*\|/g, "")
    .replace(/[-*]{3,}/g, "")
    .replace(/\n+/g, " ")
    .trim();
  const match = cleaned.match(/^(.+?[。.！!？?])/);
  return match ? match[1] : cleaned.slice(0, 120);
}

const LIST_STYLE: Record<string, React.CSSProperties> = {
  container: { flex: 1, overflow: "auto", padding: 12 },
  card: {
    background: COLORS.bg,
    borderRadius: 8,
    padding: 14,
    marginBottom: 10,
    border: `1px solid ${COLORS.border}`,
    fontSize: 13,
    lineHeight: 1.6,
  },
  intent: { fontSize: 12, color: COLORS.textLight, marginBottom: 6 },
  badge: {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: 10,
    fontSize: 11,
    background: COLORS.tableHeader,
    color: COLORS.primary,
    marginRight: 6,
    marginBottom: 4,
  },
  empty: { color: "#bbb", textAlign: "center" as const, padding: 40, fontSize: 14 },
};

export function MessageList() {
  const agentResponse = useAppStore((s) => s.agentResponse);
  const loading = useAppStore((s) => s.loading);
  const error = useAppStore((s) => s.error);
  const streamProgress = useAppStore((s) => s.streamProgress);
  const [stepsCollapsed, setStepsCollapsed] = useState(true);

  if (!agentResponse && !loading && !error && !streamProgress) {
    return (
      <div style={LIST_STYLE.container}>
        <div style={LIST_STYLE.empty}>
          👆 输入空间分析问题<br />
          <span style={{ fontSize: 12 }}>AI Agent 自动规划并执行分析</span>
        </div>
      </div>
    );
  }

  return (
    <div style={LIST_STYLE.container}>
      {loading && streamProgress && (
        <div style={{ ...LIST_STYLE.card, fontSize: 12, color: COLORS.textLight }}>
          🧠 分析中 — {streamProgress.phase === "intent" ? "解析意图" : streamProgress.phase === "planning" ? "执行分析" : "生成报告"}...
        </div>
      )}

      {error && (
        <div style={{
          ...LIST_STYLE.card,
          borderColor: "#ffcdd2",
          background: "#fff5f5",
          color: COLORS.danger,
        }}>
          ⚠️ {typeof error === "object" ? JSON.stringify(error) : String(error)}
        </div>
      )}

      {agentResponse && (
        <>
          {/* 意图卡片 */}
          <div style={LIST_STYLE.card}>
            <div style={{ fontWeight: 600, marginBottom: 8, color: COLORS.heading, fontSize: 14 }}>
              🎯 意图识别
            </div>
            <div style={LIST_STYLE.intent}>
              <strong>任务:</strong> {agentResponse.intent.task_type}
              &nbsp;|&nbsp;
              <strong>位置:</strong> {agentResponse.intent.location}
            </div>
            {agentResponse.intent.criteria?.length > 0 && (
              <div style={{ marginTop: 4 }}>
                {agentResponse.intent.criteria.map((c: string) => (
                  <span key={c} style={LIST_STYLE.badge}>{c}</span>
                ))}
              </div>
            )}
          </div>

          {/* 执行步骤卡片 — 可折叠 */}
          {agentResponse.steps?.length > 0 && (
            <div style={LIST_STYLE.card}>
              <div
                onClick={() => setStepsCollapsed(!stepsCollapsed)}
                style={{
                  fontWeight: 600,
                  color: COLORS.heading,
                  fontSize: 14,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  cursor: "pointer",
                  userSelect: "none",
                }}
              >
                <span>📋 执行步骤 ({agentResponse.steps.length})</span>
                <span style={{ fontSize: 16, color: COLORS.textLight, transition: "transform 0.2s", transform: stepsCollapsed ? "rotate(0deg)" : "rotate(90deg)" }}>
                  ▶
                </span>
              </div>
              {!stepsCollapsed && (
                <div style={{ marginTop: 8 }}>
                  {agentResponse.steps.map((s: any, i: number) => (
                    <div key={i} style={{ ...LIST_STYLE.intent, paddingLeft: 4 }}>
                      <span style={{
                        display: "inline-block",
                        width: 20,
                        height: 20,
                        borderRadius: 10,
                        background: COLORS.primary,
                        color: "#fff",
                        textAlign: "center",
                        lineHeight: "20px",
                        fontSize: 11,
                        marginRight: 6,
                        flexShrink: 0,
                      }}>
                        {i + 1}
                      </span>
                      {s.tool
                        ? <span><strong>{s.tool}</strong> — 调用</span>
                        : <span style={{ color: COLORS.textLight }}>{truncateStep(String(s.content || s.action || ""))}</span>
                      }
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 结果摘要 */}
          {agentResponse.results?.length > 0 && (
            <div style={LIST_STYLE.card}>
              <div style={{ fontWeight: 600, marginBottom: 8, color: COLORS.heading, fontSize: 14 }}>
                📊 分析结果
              </div>
              <div style={{ fontSize: 12, color: COLORS.textLight }}>
                共 {agentResponse.results.flatMap((r: any) => r?.features || []).length} 个空间要素已加载到地图
              </div>
            </div>
          )}

          {/* 报告卡片 */}
          {agentResponse.report && (
            <div style={{
              ...LIST_STYLE.card,
              padding: 18,
              borderLeft: `3px solid ${COLORS.primary}`,
            }}>
              <div style={{
                fontWeight: 700,
                marginBottom: 12,
                color: COLORS.primary,
                fontSize: 15,
                letterSpacing: 0.5,
              }}>
                📝 空间分析报告
              </div>
              <ReportContent>{agentResponse.report}</ReportContent>
            </div>
          )}
        </>
      )}
    </div>
  );
}
