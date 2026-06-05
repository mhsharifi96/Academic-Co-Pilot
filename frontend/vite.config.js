import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During development the React app runs on :5173 and the FastAPI backend on
// :8000.  Proxying /api avoids CORS issues and lets the frontend call the API
// with same-origin relative paths (see src/api.js).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
