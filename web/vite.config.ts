// Written with AI assistance (Claude Code). See AI_USE.md.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  // Relative asset paths, so the build works at the GitHub Pages project URL and in preview.
  base: "./",
  plugins: [react()],
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.{ts,tsx}"],
  },
});
