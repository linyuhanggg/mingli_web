import { accessSync, constants } from "node:fs";
import { delimiter, join } from "node:path";
import { defineConfig } from "@playwright/test";

function findSystemChrome(): string | undefined {
  const executableNames =
    process.platform === "win32"
      ? ["chrome.exe", "msedge.exe"]
      : ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"];
  const candidates = [
    process.env.CHROME_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    process.env.PROGRAMFILES
      ? join(process.env.PROGRAMFILES, "Google/Chrome/Application/chrome.exe")
      : undefined,
    process.env["PROGRAMFILES(X86)"]
      ? join(
          process.env["PROGRAMFILES(X86)"],
          "Google/Chrome/Application/chrome.exe",
        )
      : undefined,
    ...((process.env.PATH ?? "").split(delimiter).flatMap((directory) =>
      executableNames.map((name) => join(directory, name)),
    )),
  ];

  return candidates.find((candidate) => {
    if (!candidate) return false;
    try {
      accessSync(candidate, constants.X_OK);
      return true;
    } catch {
      return false;
    }
  });
}

const suppliedBaseUrl = process.env.BASE_URL;
const baseURL = suppliedBaseUrl ?? "http://127.0.0.1:3000";
const chromeExecutable = findSystemChrome();

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./e2e/test-results",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { outputFolder: "e2e/report", open: "never" }]],
  use: {
    baseURL,
    browserName: "chromium",
    launchOptions: chromeExecutable
      ? { executablePath: chromeExecutable }
      : undefined,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "360", use: { viewport: { width: 360, height: 800 } } },
    { name: "768", use: { viewport: { width: 768, height: 1024 } } },
    { name: "1024", use: { viewport: { width: 1024, height: 768 } } },
    { name: "1440", use: { viewport: { width: 1440, height: 900 } } },
  ],
  webServer: suppliedBaseUrl
    ? undefined
    : {
        command: "npm run build && npm run start",
        env: { HOSTNAME: "127.0.0.1", PORT: "3000" },
        url: baseURL,
        reuseExistingServer: false,
        timeout: 120_000,
      },
});
