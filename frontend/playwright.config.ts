import { defineConfig, devices } from "@playwright/test";

// E2E runs against a dedicated Vite dev server (strict port 5199) whose /api
// proxy points at the local VERITY backend (see vite.config.ts). The backend
// must be reachable on 127.0.0.1:8015 with seeded data intact.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5199",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    locale: "en-US",
  },
  webServer: {
    command: "npm run dev -- --port 5199 --strictPort --host 127.0.0.1",
    url: "http://127.0.0.1:5199/",
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});