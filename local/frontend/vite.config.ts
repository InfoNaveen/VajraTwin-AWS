import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,   // 5174 to avoid colliding with the AWS frontend on 5173
    proxy: {
      // Forward /api/* → FastAPI on 8000 (strips the /api prefix)
      "/api": {
        target:      "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite:     (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  build: { outDir: "dist", sourcemap: true },
});
