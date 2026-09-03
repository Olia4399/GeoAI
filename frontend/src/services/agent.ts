import axios from "axios";
import type { AgentError, AgentResponse } from "../types";

const agentClient = axios.create({
  baseURL: "/api/agent",
  timeout: 300000,
  headers: { "Content-Type": "application/json" },
});

/** 将任意错误归一化为统一的 AgentError（分类 + 提示语），供各组件展示 */
export function toAgentError(err: unknown, status?: number): AgentError {
  const msg =
    typeof err === "string"
      ? err
      : err instanceof Error
        ? err.message
        : String(err);

  if (status) {
    if (status === 401 || status === 403) {
      return { type: "llm", title: "大模型认证失败", detail: msg, status, hint: "检查 agent/.env 的 OPENAI_API_KEY 是否有效" };
    }
    if (status === 422) {
      return { type: "http", title: "请求参数校验失败", detail: msg, status, hint: "检查请求体是否符合后端 Pydantic 模型" };
    }
    if (status >= 500) {
      return { type: "http", title: `服务端处理失败 (${status})`, detail: msg, status, hint: "查看 agent 服务 (8001) 控制台日志（已打印 traceback）" };
    }
    return { type: "http", title: `请求失败 (${status})`, detail: msg, status };
  }

  if (/Failed to fetch|NetworkError|ERR_/i.test(msg)) {
    return { type: "network", title: "无法连接后端服务", detail: msg, hint: "确认 agent (8001) 与 spatial (8002) 服务已启动，前端代理正常" };
  }
  if (/timeout|timed out/i.test(msg)) {
    return { type: "timeout", title: "请求超时", detail: msg, hint: "LLM 响应较慢或网络不稳定，稍后重试" };
  }
  if (/api key|401|unauthorized|authentication/i.test(msg)) {
    return { type: "llm", title: "大模型认证失败", detail: msg, hint: "检查 agent/.env 的 OPENAI_API_KEY / OPENAI_BASE_URL" };
  }
  return { type: "unknown", title: "请求出错", detail: msg, hint: "查看浏览器 Network 面板与后端日志定位" };
}

export const agentApi = {
  /** 普通查询 */
  async query(text: string, context?: Record<string, unknown>): Promise<AgentResponse> {
    const { data } = await agentClient.post<AgentResponse>("/query", {
      query: text,
      context: context || null,
    });
    return data;
  },

  /** SSE 流式查询 */
  queryStream(
    text: string,
    context: Record<string, unknown> | undefined,
    onEvent: (event: { type: string; data: any }) => void,
    onError: (err: AgentError) => void,
    onDone: () => void,
  ): AbortController {
    const controller = new AbortController();
    // 看门狗：后端 LLM 调用挂死时主动中断并报错（后端自身已有 120s 超时，此处兜底）
    let timedOut = false;
    const timeoutId = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
      onError({
        type: "timeout",
        title: "请求超时（前端兜底）",
        detail: "等待超过 10 分钟仍未完成，已主动中断",
        hint: "后端 LLM 调用可能挂起，查看 agent 服务 (8001) 日志；稍后重试",
      });
    }, 10 * 60 * 1000);

    fetch("/api/agent/query/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: text, context: context || null }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          clearTimeout(timeoutId);
          // 后端直接返回非流式错误（如 500/422）：提取 detail 并分类展示
          let detail = await response.text();
          try {
            const parsed = JSON.parse(detail);
            if (parsed?.detail != null) {
              // FastAPI 422 的 detail 是校验错误数组，需序列化；其余为字符串
              detail =
                typeof parsed.detail === "string"
                  ? parsed.detail
                  : JSON.stringify(parsed.detail);
            }
          } catch { /* 保留原始文本 */ }
          onError(toAgentError(detail, response.status));
          return;
        }
        const reader = response.body?.getReader();
        if (!reader) {
          clearTimeout(timeoutId);
          onError({
            type: "network",
            title: "响应体为空",
            detail: "后端未返回流式内容",
            hint: "确认 agent 服务 (8001) 正常",
          });
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const parsed = JSON.parse(line.slice(6));
                onEvent({ type: parsed.type || "unknown", data: parsed });
              } catch { /* skip malformed */ }
            }
          }
        }
        clearTimeout(timeoutId);
        onDone();
      })
      .catch((err) => {
        clearTimeout(timeoutId);
        if (timedOut) return; // 看门狗已上报超时
        if (err.name !== "AbortError") onError(toAgentError(err));
      });

    return controller;
  },

  /** 健康检查 */
  async health(): Promise<{ status: string }> {
    const { data } = await agentClient.get("/health");
    return data;
  },

  /** 历史列表 */
  async history(limit = 20, offset = 0): Promise<{ total: number; items: any[] }> {
    const { data } = await agentClient.get("/history", { params: { limit, offset } });
    return data;
  },

  /** 历史详情 */
  async historyDetail(id: string): Promise<any> {
    const { data } = await agentClient.get(`/history/${id}`);
    return data;
  },

  /** 删除历史 */
  async historyDelete(id: string): Promise<void> {
    await agentClient.delete(`/history/${id}`);
  },
};
