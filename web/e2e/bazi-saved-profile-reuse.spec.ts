import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, type Route } from "@playwright/test";

const SAVED_PROFILE_ID = "22222222-2222-4222-8222-222222222222";
const PREVIEW_READING_ID = "saved-profile-preview";

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function readingSummary() {
  return {
    reading_version_id: PREVIEW_READING_ID,
    reading_root_id: `${PREVIEW_READING_ID}-root`,
    profile_version_id: SAVED_PROFILE_ID,
    capability_id: "bazi",
    product_id: "bazi",
    runtime_capability_ids: ["bazi"],
    version: 1,
    status: "accepted",
    object_id: "natal",
    dimension_ids: ["career"],
    horizon: { kind_id: "life", start: null, end: null },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-19T02:00:00Z",
  };
}

test("signed-in bazi reuses the newest saved profile without asking for birth data", async ({
  page,
}, testInfo) => {
  const previewBodies: unknown[] = [];
  const profileWritePaths: string[] = [];

  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.context().addCookies([
    {
      name: "mingli_csrf",
      value: "saved-profile-e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname;

    if (method === "GET" && path === "/api/v1/account") {
      await json(route, {
        user_id: "saved-profile-e2e-user",
        identities: [{
          id: "saved-profile-e2e-identity",
          provider: "email",
          masked_destination: "saved***@example.com",
          verified_at: "2026-08-19T01:00:00Z",
        }],
      });
      return;
    }
    if (method === "GET" && path === "/api/v1/profiles") {
      await json(route, {
        profiles: [{
          profile_id: "11111111-1111-4111-8111-111111111111",
          profile_version_id: SAVED_PROFILE_ID,
          subject_ref: `profile-version:${SAVED_PROFILE_ID}`,
          version: 3,
          created_at: "2026-08-19T01:30:00Z",
        }],
      });
      return;
    }
    if (method === "GET" && path === "/api/v1/capabilities") {
      await json(route, {
        runtime_release_profile: "bazi-saved-profile-e2e",
        source_status: "available",
        capabilities: [{
          capability_id: "bazi",
          label: "八字",
          tier: "A",
          source_system: "bazi",
          runtime_active_rule_count: 19,
          judgment_rule_count: 19,
          source_status: "available",
        }],
      });
      return;
    }
    if (method === "POST" && path.startsWith("/api/v1/profiles")) {
      profileWritePaths.push(path);
      await json(route, { title: "Unexpected profile write" }, 500);
      return;
    }
    if (method === "POST" && path === "/api/v1/readings/preview") {
      previewBodies.push(request.postDataJSON());
      await json(route, readingSummary(), 201);
      return;
    }
    if (method === "GET" && path === `/api/v1/readings/${PREVIEW_READING_ID}`) {
      await json(route, readingSummary());
      return;
    }
    await json(route, { title: "Unhandled e2e API", detail: `${method} ${path}` }, 599);
  });

  const response = await page.goto("/bazi", { waitUntil: "domcontentloaded" });
  expect(response?.ok()).toBe(true);

  const profileSelect = page.getByRole("combobox", { name: "排盘资料" });
  await expect(profileSelect).toHaveValue(SAVED_PROFILE_ID);
  await expect(page.getByLabel("出生年份")).toHaveCount(0);
  await expect(page.getByText(/直接使用已保存的不可变档案版本/)).toBeVisible();

  await profileSelect.focus();
  await expect(profileSelect).toBeFocused();
  await page.keyboard.press("Home");
  await expect(profileSelect).toHaveValue(SAVED_PROFILE_ID);

  const width = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));
  expect(width.document, `${testInfo.project.name}px horizontal overflow`).toBeLessThanOrEqual(
    width.viewport,
  );

  const directory = resolve(
    process.env.BROWSER_EVIDENCE_DIR
      ?? resolve(process.cwd(), "e2e/screenshots/2026-08-19-bazi-saved-profile-reuse"),
    testInfo.project.name,
  );
  await mkdir(directory, { recursive: true });
  await page.screenshot({
    path: resolve(directory, "saved-profile-selected.png"),
    fullPage: true,
  });

  await page.getByRole("button", { name: /^立即排盘（免费）/ }).click();
  await expect.poll(() => previewBodies.length).toBe(1);
  expect(previewBodies).toEqual([
    expect.objectContaining({ profile_version_id: SAVED_PROFILE_ID }),
  ]);
  expect(profileWritePaths).toEqual([]);
});
