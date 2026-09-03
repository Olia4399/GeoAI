/** 共享类型定义 */

// GeoJSON 类型 (简化)：按几何类型判别联合，`geom.type === "Point"` 等
// 运行时类型守卫即可让 TS 自动收窄 coordinates 的具体形状
export type GeoJSONGeometry =
  | { type: "Point"; coordinates: number[] }
  | { type: "LineString"; coordinates: number[][] }
  | { type: "Polygon"; coordinates: number[][][] };

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

// 统一错误结构：分类 + 友好标题 + 排查提示
export interface AgentError {
  type: "network" | "http" | "sse" | "timeout" | "llm" | "spatial" | "unknown";
  /** 用户可读的标题 */
  title: string;
  /** 技术细节（后端 detail、异常消息等） */
  detail?: string;
  /** 排查提示（可操作建议） */
  hint?: string;
  /** HTTP 状态码 */
  status?: number;
}

// 地图模式
export type MapMode = "2d" | "3d";

// 地图绘制
export type DrawMode = "rectangle" | null;
