import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/integration_tests/setup.ts"],
    include: ["tests/integration_tests/**/*.test.{ts,tsx}"],
    css: true,
    name: "integration",
  },
});
