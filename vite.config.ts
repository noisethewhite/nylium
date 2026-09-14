import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const WEB_ROOT = "web";
/** Dev-proxy target. The canonical default lives in src/nylium/cli.py
 * (cli.DEFAULT_HOST / cli.DEFAULT_PORT) — keep them in sync; override
 * via NYLIUM_DEV_API when serving the backend on a non-default port. */
const API_PROXY_TARGET = process.env.NYLIUM_DEV_API ?? "http://127.0.0.1:8000";

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
