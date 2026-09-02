import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    projects: ["./vite.config.ts", "./vitest.integration.config.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text"],
      include: ["src/**"],
    },
  },
});
