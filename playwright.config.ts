import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  testMatch: "**/*.spec.ts",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8123",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "python3 -m uvicorn tests.e2e.widget_static_app:app --host 127.0.0.1 --port 8123",
    url: "http://127.0.0.1:8123/widget.js",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
