import { create } from "zustand";
import type { AgentResponse, GeoJSONFeatureCollection, MapMode } from "../types";
import { agentApi } from "../services/agent";

interface AppState {
  // 地图状态
  mapBounds: [number, number, number, number] | null;
  selectedGeometry: GeoJSONFeatureCollection | null;
  mapMode: MapMode;

  // Agent 交互
  query: string;
  loading: boolean;
  agentResponse: AgentResponse | null;
  error: string | null;

  // Actions
  setMapBounds: (bounds: [number, number, number, number]) => void;
  setSelectedGeometry: (geo: GeoJSONFeatureCollection | null) => void;
  setMapMode: (mode: MapMode) => void;
  setQuery: (q: string) => void;
  submitQuery: (query: string) => Promise<void>;
  clearResults: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  mapBounds: null,
  selectedGeometry: null,
  mapMode: "2d",
  query: "",
  loading: false,
  agentResponse: null,
  error: null,

  setMapBounds: (bounds) => set({ mapBounds: bounds }),
  setSelectedGeometry: (geo) => set({ selectedGeometry: geo }),
  setMapMode: (mode) => set({ mapMode: mode }),
  setQuery: (q) => set({ query: q }),

  submitQuery: async (query: string) => {
    set({ query, loading: true, error: null });
    try {
      const { mapBounds, selectedGeometry } = get();
      const context = {
        map_bounds: mapBounds,
        selected_geometry: selectedGeometry,
      };
      const response = await agentApi.query(query, context);
      set({ agentResponse: response, loading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Agent 请求失败",
        loading: false,
      });
    }
  },

  clearResults: () =>
    set({ agentResponse: null, error: null, query: "", loading: false }),
}));
