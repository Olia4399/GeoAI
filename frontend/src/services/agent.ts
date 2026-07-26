import axios from "axios";
import type { AgentResponse } from "../types";

const agentClient = axios.create({
  baseURL: "/api/agent",
  timeout: 300000,
  headers: { "Content-Type": "application/json" },
});

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
    onError: (err: string) => void,
    onDone: () => void,
  ): AbortController {
    const controller = new AbortController();

    fetch("/api/agent/query/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: text, context: context || null }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const err = await response.text();
          onError(err);
          return;
        }
        const reader = response.body?.getReader();
        if (!reader) { onDone(); return; }

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
        onDone();
      })
      .catch((err) => {
        if (err.name !== "AbortError") onError(String(err));
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
