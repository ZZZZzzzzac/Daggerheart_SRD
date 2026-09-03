import { defineConfig } from "@playwright/test";


export default defineConfig({
  testDir: "./tests/browser",
  fullyParallel: true,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:8766",
    browserName: "chromium",
    channel: process.env.PLAYWRIGHT_CHANNEL || "chrome",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "python scripts/preview_server.py --no-build --port 8766 --admin-password playwright",
    url: "http://127.0.0.1:8766/SRD/",
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
