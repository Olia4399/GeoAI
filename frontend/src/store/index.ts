import { create } from "zustand";
import type { AgentResponse, GeoJSONFeatureCollection, MapMode, DrawMode } from "../types";
import { agentApi } from "../services/agent";

interface StreamProgress {
  phase: string;
  status: string;
  steps: Array<{ index: number; total: number; data: any }>;
}

interface AppState {
  // 地图状态
  mapBounds: [number, number, number, number] | null;
  selectedGeometry: GeoJSONFeatureCollection | null;
  drawGeometry: GeoJSONFeatureCollection | null;
  mapMode: MapMode;
  drawMode: DrawMode;

  // Agent 交互
  query: string;
  loading: boolean;
  agentResponse: AgentResponse | null;
  error: string | null;
  streamProgress: StreamProgress | null;
  streamAbort: AbortController | null;

  // Actions
  setMapBounds: (bounds: [number, number, number, number]) => void;
  setSelectedGeometry: (geo: GeoJSONFeatureCollection | null) => void;
  setDrawGeometry: (geo: GeoJSONFeatureCollection | null) => void;
  setDrawMode: (mode: DrawMode) => void;
  setMapMode: (mode: MapMode) => void;
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

  submitQuery: (query: string) => {
    // 取消之前的流
    get().streamAbort?.abort();

    set({
      query,
      loading: true,
      error: null,
      agentResponse: null,
      streamProgress: { phase: "intent", status: "running", steps: [] },
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
          set((s) => ({
            streamProgress: { ...s.streamProgress!, phase: data.phase, status: data.status },
          }));
        } else if (type === "step") {
          set((s) => ({
            streamProgress: {
              ...s.streamProgress!,
              steps: [...s.streamProgress!.steps, data],
            },
          }));
        } else if (type === "done") {
          const response: AgentResponse = {
            intent: data.intent || {},
            steps: get().streamProgress?.steps.map((s) => s.data) || [],
            results: data.results || [],
            report: data.report || "",
          };
          set({ agentResponse: response, loading: false, streamProgress: null });
        } else if (type === "error") {
          set({ error: data.detail || String(data), loading: false, streamProgress: null });
        }
      },
      (err) => {
        set({ error: err, loading: false, streamProgress: null });
      },
      () => {
        // stream ended — if still loading (no "done" event), mark done
        set((s) => {
          if (s.loading) return { loading: false };
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
