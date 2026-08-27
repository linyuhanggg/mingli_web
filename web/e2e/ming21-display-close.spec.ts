import { expect, test, type Page } from "@playwright/test";

async function installGuestRoutes(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    const json = (body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        headers: { "set-cookie": "mingli_csrf=csrf-e2e; Path=/" },
        body: JSON.stringify(body),
      });

    if (method === "POST" && path === "/api/v1/guest-sessions") {
      await json({ csrf_token: "csrf-e2e-token-with-enough-length", guest: true }, 201);
      return;
    }
    if (method === "GET" && path === "/api/v1/account") {
      await json({
        user_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        identities: [
          {
            id: "identity-1",
            provider: "email",
            masked_destination: "d***@example.com",
            verified_at: "2026-08-10T00:00:00Z",
          },
        ],
      });
      return;
    }
    if (method === "GET" && path === "/api/v1/capabilities") {
      await json({
        runtime_release_profile: "v51",
        source_status: "available",
        capabilities: [],
      });
      return;
    }
    if (method === "GET" && path === "/api/v1/profiles") {
      await json({
        profiles: [
          {
            profile_id: "11111111-1111-4111-8111-111111111111",
            profile_version_id: "22222222-2222-4222-8222-222222222222",
            subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
            version: 1,
            display_name: "档案 · 1992-07-08",
            created_at: "2026-08-10T00:00:00Z",
          },
        ],
      });
      return;
    }
    if (method === "PATCH" && path.startsWith("/api/v1/profiles/")) {
      await json({
        profile_id: "11111111-1111-4111-8111-111111111111",
        profile_version_id: "22222222-2222-4222-8222-222222222222",
        subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
        version: 1,
        display_name: "游客重命名档案",
        created_at: "2026-08-10T00:00:00Z",
      });
      return;
    }
    await json({ title: "not found" }, 404);
  });
}

async function assertNoOverflow(page: Page, label: string) {
  const measure = await page.evaluate(() => ({
    innerWidth: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(
    measure.scrollWidth,
    `${label}: scrollWidth ${measure.scrollWidth} > innerWidth ${measure.innerWidth}`,
  ).toBeLessThanOrEqual(measure.innerWidth + 1);
}

test("archive rename stays reachable without horizontal overflow", async ({ page }) => {
  await installGuestRoutes(page);
  await page.goto("/account/profiles", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "已保存的档案版本" })).toBeVisible();
  await expect(page.getByRole("button", { name: "重命名" })).toBeVisible();
  await page.getByRole("button", { name: "重命名" }).click();
  await page.getByLabel("档案名称").fill("游客重命名档案");
  await page.getByRole("button", { name: "保存名称" }).click();
  await expect(page.getByText("游客重命名档案")).toBeVisible();
  await assertNoOverflow(page, "profiles archive");
});
