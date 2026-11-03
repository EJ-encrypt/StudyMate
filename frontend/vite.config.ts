/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // One .env at the repository root serves both the backend and this build.
  envDir: "..",
  server: {
    // Matches production, where Vercel serves the API from /api on the same
    // origin. Locally the API runs through the same entry point
    // (uvicorn api.index:app), so the path passes through unchanged.
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./vitest.setup.ts",
    globals: true,
    // Tests must not pick up real Supabase settings from the root .env.
    env: { VITE_SUPABASE_URL: "", VITE_SUPABASE_ANON_KEY: "" },
  },
});
