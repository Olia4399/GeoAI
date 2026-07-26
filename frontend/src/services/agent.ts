import axios from "axios";
import type { AgentResponse } from "../types";

/** Axios 实例 — 对接 Spatial Agent (代理到 :8001) */
const agentClient = axios.create({
  baseURL: "/api/agent",
  timeout: 300000, // Agent 多步推理最长 5 分钟
  headers: { "Content-Type": "application/json" },
});

export const agentApi = {
  /** 发送自然语言空间查询 */
  async query(text: string, context?: Record<string, unknown>): Promise<AgentResponse> {
    const { data } = await agentClient.post<AgentResponse>("/query", {
      query: text,
      context: context || null,
    });
    return data;
  },

  /** 健康检查 */
  async health(): Promise<{ status: string }> {
    const { data } = await agentClient.get("/health");
    return data;
  },
};
