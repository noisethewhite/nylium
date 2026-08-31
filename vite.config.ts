import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const WEB_ROOT = "web";
const API_PROXY_TARGET = "http://127.0.0.1:8000";

export default defineConfig({
  root: WEB_ROOT,
  plugins: [react()],
  server: {
    proxy: {
      "/api": { target: API_PROXY_TARGET, changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
