/** 共享类型定义 */

// GeoJSON 类型 (简化)
export interface GeoJSONGeometry {
  type: string;
  coordinates: number[] | number[][] | number[][][];
}

export interface GeoJSONFeature {
  type: "Feature";
  properties: Record<string, unknown>;
  geometry: GeoJSONGeometry;
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
}

// Agent 交互类型
export interface AgentStep {
  tool?: string;
  arguments?: Record<string, unknown>;
  action?: string;
  content?: string;
}

export interface AgentIntent {
  task_type: string;
  location: string;
  industry?: string;
  criteria: string[];
  geometry_needed: boolean;
}

export interface AgentResponse {
  intent: AgentIntent;
  steps: AgentStep[];
  results: GeoJSONFeatureCollection[];
  report: string;
}

// 地图模式
export type MapMode = "2d" | "3d";

// 地图绘制
export type DrawMode = "rectangle" | null;
