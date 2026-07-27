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
  kind?: string;
  /** 自请求开始累计耗时（秒） */
  elapsed_s?: number;
  /** 本步相对上一步耗时（秒） */
  step_elapsed_s?: number;
  feature_count?: number;
  node?: string;
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
  timings?: {
    intent_s?: number;
    planning_s?: number;
    report_s?: number;
    total_s?: number;
  };
}

// 地图模式
export type MapMode = "2d" | "3d";

// 地图绘制
export type DrawMode = "rectangle" | null;
