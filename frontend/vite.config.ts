import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/unit_tests/setup.ts"],
    include: ["tests/unit_tests/**/*.test.{ts,tsx}"],
    css: true,
  },
});
