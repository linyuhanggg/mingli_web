import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { resolve } from "node:path";

const repositoryRoot = resolve(import.meta.dirname, "../..");

for (const app of [
  { name: "web", envName: "BASE_URL", defaultPort: "3000" },
  { name: "admin", envName: "ADMIN_BASE_URL", defaultPort: "3001" },
]) {
  test(`${app.name} exposes the P1-008 smoke contract`, async () => {
    const appRoot = resolve(repositoryRoot, app.name);
    const packageJson = JSON.parse(
      await readFile(resolve(appRoot, "package.json"), "utf8"),
    );
    const config = await readFile(
      resolve(appRoot, "playwright.config.ts"),
      "utf8",
    );
    const smoke = await readFile(
      resolve(appRoot, "e2e/smoke.spec.ts"),
      "utf8",
    );
    const vitestConfig = await readFile(
      resolve(appRoot, "vitest.config.ts"),
      "utf8",
    );

    assert.equal(packageJson.scripts["e2e:smoke"], "playwright test");
    assert.match(packageJson.scripts["e2e:install"], /playwright install/);
    assert.ok(packageJson.devDependencies["@playwright/test"]);
    assert.match(vitestConfig, /e2e\/\*\*/);

    assert.match(config, new RegExp(`process\\.env\\.${app.envName}`));
    assert.match(config, new RegExp(`127\\.0\\.0\\.1:${app.defaultPort}`));
    assert.match(`${config}\n${smoke}`, /e2e\/screenshots/);
    for (const width of [360, 768, 1024, 1440]) {
      assert.match(config, new RegExp(`width:\\s*${width}`));
    }

    assert.match(smoke, /pageerror/);
    assert.match(smoke, /console/);
    assert.match(smoke, /response\.ok\(\)/);
    assert.match(smoke, /waitUntil:\s*["']domcontentloaded["']/);
    assert.match(smoke, /resourceType\(\)/);
    assert.match(smoke, /http-errors/);
    assert.match(smoke, /screenshot/);

    if (app.name === "admin") {
      await assert.rejects(
        readFile(resolve(appRoot, "src/app/[[...segments]]/page.tsx")),
      );
      await readFile(resolve(appRoot, "src/app/[...segments]/page.tsx"));
    }
  });
}
