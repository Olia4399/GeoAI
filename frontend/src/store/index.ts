import { create } from "zustand";
import type { AgentError, AgentResponse, GeoJSONFeatureCollection, MapMode, DrawMode } from "../types";
import { agentApi } from "../services/agent";

interface StreamProgress {
  phase: string;
  status: string;
  steps: Array<{
    index: number;
    total: number;
    data: any;
    elapsed_s?: number;
    step_elapsed_s?: number;
  }>;
  /** 各 phase 完成时的耗时（秒） */
  phaseElapsed: Record<string, number>;
  timings?: AgentResponse["timings"];
}

interface AppState {
  // 地图状态
  mapBounds: [number, number, number, number] | null;
  selectedGeometry: GeoJSONFeatureCollection | null;
  drawGeometry: GeoJSONFeatureCollection | null;
  mapMode: MapMode;
  drawMode: DrawMode;
  layerVisibility: Record<string, boolean>;

  // Agent 交互
  query: string;
  loading: boolean;
  agentResponse: AgentResponse | null;
  error: AgentError | null;
  streamProgress: StreamProgress | null;
  streamAbort: AbortController | null;

  // Actions
  setMapBounds: (bounds: [number, number, number, number]) => void;
  setSelectedGeometry: (geo: GeoJSONFeatureCollection | null) => void;
  setDrawGeometry: (geo: GeoJSONFeatureCollection | null) => void;
  setDrawMode: (mode: DrawMode) => void;
  setMapMode: (mode: MapMode) => void;
  setLayerVisibility: (id: string, visible: boolean) => void;
  toggleLayerVisibility: (id: string) => void;
  submitQuery: (query: string) => void;
  cancelQuery: () => void;
  clearResults: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  mapBounds: null,
  selectedGeometry: null,
  drawGeometry: null,
  mapMode: "2d",
  drawMode: null,
  layerVisibility: { poi: true, roads: true, buildings: true, districts: true, analysis: true, draw: true },
  query: "",
  loading: false,
  agentResponse: null,
  error: null,
  streamProgress: null,
  streamAbort: null,

  setMapBounds: (bounds) => set({ mapBounds: bounds }),
  setSelectedGeometry: (geo) => set({ selectedGeometry: geo }),
  setDrawGeometry: (geo) => set({ drawGeometry: geo }),
  setDrawMode: (mode) => set({ drawMode: mode }),
  setMapMode: (mode) => set({ mapMode: mode }),
  setLayerVisibility: (id, visible) =>
    set((s) => ({ layerVisibility: { ...s.layerVisibility, [id]: visible } })),
  toggleLayerVisibility: (id) =>
    set((s) => ({ layerVisibility: { ...s.layerVisibility, [id]: !s.layerVisibility[id] } })),

  submitQuery: (query: string) => {
    // 取消之前的流
    get().streamAbort?.abort();

    set({
      query,
      loading: true,
      error: null,
      agentResponse: null,
      streamProgress: { phase: "intent", status: "running", steps: [], phaseElapsed: {} },
    });

    const { mapBounds, selectedGeometry, drawGeometry } = get();
    const context = {
      map_bounds: mapBounds,
      selected_geometry: selectedGeometry || drawGeometry,
    };

    const controller = agentApi.queryStream(
      query,
      context,
      (event) => {
        const { type, data } = event;
        if (type === "phase") {
          set((s) => {
            const phaseElapsed = { ...s.streamProgress!.phaseElapsed };
            if (data.status === "done" && data.phase_elapsed_s != null) {
              phaseElapsed[data.phase] = data.phase_elapsed_s;
            }
            return {
              streamProgress: {
                ...s.streamProgress!,
                phase: data.phase,
                status: data.status,
                phaseElapsed,
              },
            };
          });
        } else if (type === "step") {
          set((s) => ({
            streamProgress: {
              ...s.streamProgress!,
              phase: "planning",
              status: "running",
              steps: [
                ...s.streamProgress!.steps,
                {
                  index: data.index,
                  total: data.total,
                  data: data.data,
                  elapsed_s: data.elapsed_s ?? data.data?.elapsed_s,
                  step_elapsed_s: data.step_elapsed_s ?? data.data?.step_elapsed_s,
                },
              ],
            },
          }));
        } else if (type === "done") {
          const streamedSteps = get().streamProgress?.steps.map((s) => s.data) || [];
          const response: AgentResponse = {
            intent: data.intent || {},
            steps: (data.steps?.length ? data.steps : streamedSteps) || [],
            results: data.results || [],
            report: data.report || "",
            timings: data.timings,
          };
          set({ agentResponse: response, loading: false, streamProgress: null });
        } else if (type === "error") {
          // 后端 SSE error 事件：规范化 detail，透传后端分类的 title/hint
          set({
            error: {
              type: data.error_type || "sse",
              title: data.title || "分析执行失败",
              detail:
                (data.phase ? `[失败阶段: ${data.phase}] ` : "") +
                (typeof data.detail === "string"
                  ? data.detail
                  : JSON.stringify(data.detail ?? data)),
              hint: data.hint,
            },
            loading: false,
            streamProgress: null,
          });
        }
      },
      (err) => {
        set({ error: err, loading: false, streamProgress: null });
      },
      () => {
        // 流已结束但未收到 done 事件：视为异常中断，给出可见错误而非静默结束
        set((s) => {
          if (s.loading) {
            return {
              loading: false,
              error: s.agentResponse
                ? null
                : {
                    type: "sse",
                    title: "响应流意外中断",
                    detail: "连接已结束，但未收到完成（done）事件",
                    hint: "可能后端异常或网络中断，查看 agent 服务 (8001) 控制台日志后重试",
                  },
            };
          }
          return {};
        });
      }
    );

    set({ streamAbort: controller });
  },

  cancelQuery: () => {
    get().streamAbort?.abort();
    set({ loading: false, streamProgress: null, streamAbort: null });
  },

  clearResults: () =>
    set({
      agentResponse: null, error: null, query: "",
      loading: false, drawGeometry: null, streamProgress: null,
    }),
}));
