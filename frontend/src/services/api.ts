import axios from "axios";

/** Axios 实例 — 对接 Spatial Service (代理到 :8002) */
export const spatialApi = axios.create({
  baseURL: "/api/spatial",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

/** 缓冲区分析 */
export async function bufferAnalysis(geometry: object, distance: number) {
  const { data } = await spatialApi.post("/buffer", { geometry, distance });
  return data;
}

/** 距离计算 */
export async function distanceAnalysis(source: object, target: object) {
  const { data } = await spatialApi.post("/distance", { source, target });
  return data;
}
