import { useEffect, useState } from "react";
import { useAppStore } from "../../store";
import { ReportContent, COLORS } from "./ReportRenderer";
import { ErrorCard } from "./ErrorCard";

/* ================================================================
   组件 — 样式系统从 ReportRenderer 共享
   ================================================================ */

/** 截断步骤中的原始 Markdown：
 *  - 含 --- 分隔线时，其后是完整报告正文，只保留分隔线前的总结全文
 *    （如"分析完成。以下是…报告。"）；
 *  - 无分隔线时，只保留第一句话。 */
function truncateStep(text: string): string {
  const parts = text.split(/\n\s*[-*]{3,}/);
  const cleaned = parts[0]
    .replace(/^#{1,4}\s+.*$/gm, "")
    .replace(/\|.*\|/g, "")
    .replace(/\n+/g, " ")
    .trim();
  if (parts.length > 1) return cleaned || "分析完成";
  const match = cleaned.match(/^(.+?[。.！!？?])/);
  return match ? match[1] : cleaned.slice(0, 120);
}

function fmtSec(s?: number): string {
  if (s == null || Number.isNaN(s)) return "";
  return s < 10 ? `${s.toFixed(2)}s` : `${s.toFixed(1)}s`;
}

function stepTitle(s: any): string {
  if (s.kind === "tool_result" || s.action === "tool_result") {
    return s.content || `${s.tool || "tool"} 返回`;
  }
  if (s.tool) return `${s.tool} — 调用`;
  if (s.action === "reasoning")
    return truncateStep(String(s.content || "推理"));
  return truncateStep(String(s.content || s.action || ""));
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
  empty: {
    color: "#bbb",
    textAlign: "center" as const,
    padding: 40,
    fontSize: 14,
  },
  time: {
    marginLeft: "auto",
    fontSize: 11,
    color: COLORS.textLight,
    fontVariantNumeric: "tabular-nums",
    flexShrink: 0,
  },
  stepRow: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "4px 0",
    fontSize: 12,
    color: COLORS.textLight,
  },
};

const PHASE_HINT: Record<string, string> = {
  intent: "解析意图",
  planning: "执行分析（心流）",
  report: "生成报告",
};

export function MessageList() {
  const agentResponse = useAppStore((s) => s.agentResponse);
  const loading = useAppStore((s) => s.loading);
  const error = useAppStore((s) => s.error);
  const streamProgress = useAppStore((s) => s.streamProgress);
  const query = useAppStore((s) => s.query);
  const submitQuery = useAppStore((s) => s.submitQuery);
  // 报告生成后默认折叠执行步骤，用户点击标题行才展开
  const [stepsCollapsed, setStepsCollapsed] = useState(true);

  // 每次新分析完成时重置为折叠态
  useEffect(() => {
    if (agentResponse) setStepsCollapsed(true);
  }, [agentResponse]);

  // if (!agentResponse && !loading && !error && !streamProgress) {
  //   return (
  //     <div style={LIST_STYLE.container}>
  //       <div style={LIST_STYLE.empty}>
  //         👆 输入空间分析问题
  //         <br />
  //         <span style={{ fontSize: 12 }}>AI Agent 自动规划并执行分析</span>
  //       </div>
  //     </div>
  //   );
  // }

  return (
    <div style={LIST_STYLE.container}>
      {/* 流式心流：报告生成前即可看到每一步 + 耗时 */}
      {loading && streamProgress && (
        <div style={LIST_STYLE.card}>
          <div
            style={{
              fontWeight: 600,
              marginBottom: 8,
              color: COLORS.heading,
              fontSize: 14,
            }}
          >
            🧠 {PHASE_HINT[streamProgress.phase] || "分析中"}…
          </div>
          {(["intent", "planning", "report"] as const).map((phase) => {
            const elapsed = streamProgress.phaseElapsed[phase];
            const isCurrent =
              streamProgress.phase === phase &&
              streamProgress.status === "running";
            return (
              <div key={phase} style={LIST_STYLE.stepRow}>
                <span
                  style={{
                    width: 14,
                    textAlign: "center",
                    color: isCurrent
                      ? "#ff9800"
                      : elapsed != null
                        ? "#4caf50"
                        : "#ccc",
                  }}
                >
                  {elapsed != null ? "✓" : isCurrent ? "●" : "○"}
                </span>
                <span
                  style={{
                    color: isCurrent ? COLORS.heading : COLORS.textLight,
                    fontWeight: isCurrent ? 600 : 400,
                  }}
                >
                  {PHASE_HINT[phase]}
                </span>
                {elapsed != null && (
                  <span style={LIST_STYLE.time}>{fmtSec(elapsed)}</span>
                )}
              </div>
            );
          })}
          {streamProgress.steps.length > 0 && (
            <div
              style={{
                marginTop: 8,
                borderTop: `1px solid ${COLORS.border}`,
                paddingTop: 8,
              }}
            >
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: COLORS.heading,
                  marginBottom: 4,
                }}
              >
                心流步骤
              </div>
              {streamProgress.steps.map((s, i) => (
                <div key={i} style={LIST_STYLE.stepRow}>
                  <span
                    style={{
                      display: "inline-block",
                      width: 18,
                      height: 18,
                      borderRadius: 9,
                      background: COLORS.primary,
                      color: "#fff",
                      textAlign: "center",
                      lineHeight: "18px",
                      fontSize: 10,
                      flexShrink: 0,
                    }}
                  >
                    {i + 1}
                  </span>
                  <span
                    style={{
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {stepTitle(s.data)}
                  </span>
                  <span
                    style={LIST_STYLE.time}
                    title={`累计 ${fmtSec(s.elapsed_s)}`}
                  >
                    {s.step_elapsed_s != null
                      ? `+${fmtSec(s.step_elapsed_s)}`
                      : fmtSec(s.elapsed_s)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {error && (
        <ErrorCard
          error={error}
          onRetry={query ? () => submitQuery(query) : undefined}
        />
      )}

      {agentResponse && (
        <>
          {/* 意图卡片 */}
          <div style={LIST_STYLE.card}>
            <div
              style={{
                fontWeight: 600,
                marginBottom: 8,
                color: COLORS.heading,
                fontSize: 14,
              }}
            >
              🎯 意图识别
            </div>
            <div style={LIST_STYLE.intent}>
              <strong>任务:</strong> {agentResponse.intent.task_type}
              &nbsp;|&nbsp;
              <strong>位置:</strong> {agentResponse.intent.location}
              {agentResponse.timings?.intent_s != null && (
                <>
                  &nbsp;|&nbsp;
                  <strong>耗时:</strong>{" "}
                  {fmtSec(agentResponse.timings.intent_s)}
                </>
              )}
            </div>
            {agentResponse.intent.criteria?.length > 0 && (
              <div style={{ marginTop: 4 }}>
                {agentResponse.intent.criteria.map((c: string) => (
                  <span key={c} style={LIST_STYLE.badge}>
                    {c}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* 执行步骤卡片 — 默认折叠，点击标题行展开/收起 */}
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
                <span>
                  📋 执行步骤 ({agentResponse.steps.length})
                  {agentResponse.timings?.planning_s != null && (
                    <span
                      style={{
                        fontWeight: 400,
                        color: COLORS.textLight,
                        marginLeft: 8,
                        fontSize: 12,
                      }}
                    >
                      规划合计 {fmtSec(agentResponse.timings.planning_s)}
                    </span>
                  )}
                </span>
                <span
                  style={{
                    fontSize: 16,
                    color: COLORS.textLight,
                    transition: "transform 0.2s",
                    transform: stepsCollapsed
                      ? "rotate(0deg)"
                      : "rotate(90deg)",
                  }}
                >
                  ▶
                </span>
              </div>
              {!stepsCollapsed && (
                <div style={{ marginTop: 8 }}>
                  {agentResponse.steps.map((s: any, i: number) => (
                    <div key={i} style={LIST_STYLE.stepRow}>
                      <span
                        style={{
                          display: "inline-block",
                          width: 20,
                          height: 20,
                          borderRadius: 10,
                          background: COLORS.primary,
                          color: "#fff",
                          textAlign: "center",
                          lineHeight: "20px",
                          fontSize: 11,
                          flexShrink: 0,
                        }}
                      >
                        {i + 1}
                      </span>
                      <span style={{ flex: 1, minWidth: 0 }}>
                        {s.tool || s.kind === "tool_result" ? (
                          <span>
                            <strong>{s.tool || "tool"}</strong> —{" "}
                            {s.kind === "tool_result" ? "返回" : "调用"}
                          </span>
                        ) : (
                          <span style={{ color: COLORS.textLight }}>
                            {stepTitle(s)}
                          </span>
                        )}
                      </span>
                      <span
                        style={LIST_STYLE.time}
                        title={`累计 ${fmtSec(s.elapsed_s)}`}
                      >
                        {s.step_elapsed_s != null
                          ? `+${fmtSec(s.step_elapsed_s)}`
                          : fmtSec(s.elapsed_s)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 结果摘要 */}
          {agentResponse.results?.length > 0 && (
            <div style={LIST_STYLE.card}>
              <div
                style={{
                  fontWeight: 600,
                  marginBottom: 8,
                  color: COLORS.heading,
                  fontSize: 14,
                }}
              >
                📊 分析结果
              </div>
              <div style={{ fontSize: 12, color: COLORS.textLight }}>
                共{" "}
                {
                  agentResponse.results.flatMap((r: any) => r?.features || [])
                    .length
                }{" "}
                个空间要素已加载到地图
              </div>
            </div>
          )}

          {/* 报告卡片 */}
          {agentResponse.report && (
            <div
              style={{
                ...LIST_STYLE.card,
                padding: 18,
                borderLeft: `3px solid ${COLORS.primary}`,
              }}
            >
              <div
                style={{
                  fontWeight: 700,
                  marginBottom: 12,
                  color: COLORS.primary,
                  fontSize: 15,
                  letterSpacing: 0.5,
                  display: "flex",
                  alignItems: "baseline",
                  gap: 10,
                }}
              >
                <span>📝 空间分析报告</span>
                {(agentResponse.timings?.report_s != null ||
                  agentResponse.timings?.total_s != null) && (
                  <span
                    style={{
                      fontWeight: 400,
                      fontSize: 12,
                      color: COLORS.textLight,
                    }}
                  >
                    {agentResponse.timings.report_s != null &&
                      `报告 ${fmtSec(agentResponse.timings.report_s)}`}
                    {agentResponse.timings.total_s != null &&
                      ` · 总计 ${fmtSec(agentResponse.timings.total_s)}`}
                  </span>
                )}
              </div>
              <ReportContent>{agentResponse.report}</ReportContent>
            </div>
          )}
        </>
      )}
    </div>
  );
}
