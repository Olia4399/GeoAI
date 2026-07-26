import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import cesium from "vite-plugin-cesium";

export default defineConfig({
  plugins: [react(), cesium()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api/agent": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
      "/api/spatial": {
        target: "http://localhost:8002",
        changeOrigin: true,
      },
    },
  },
});
