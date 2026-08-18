import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, type Page, type Route } from "@playwright/test";

import {
  BAZI_EVIDENCE_RESULT_EVIDENCE,
  BAZI_EVIDENCE_RESULT_VIEW_MODEL,
} from "../src/fixtures/bazi-evidence-result";


const PREVIEW_READING_ID = "preview-reading-1";
const DEEP_READING_ID = "deep-reading-1";

function readingSummary(
  readingId: string,
  overrides: Record<string, unknown> = {},
) {
  return {
    reading_version_id: readingId,
    reading_root_id: `${readingId}-root`,
    profile_version_id: "profile-version-1",
    capability_id: "bazi",
    product_id: readingId === DEEP_READING_ID ? "bazi-deep" : "bazi",
    runtime_capability_ids: ["bazi"],
    version: 1,
    status: "accepted",
    object_id: "natal",
    dimension_ids: ["career"],
    horizon: { kind_id: "life", start: null, end: null },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-18T00:00:00Z",
    ...overrides,
  };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function fillBaziInput(page: Page) {
  await page.getByLabel("受测对象").fill("本人");
  await page.getByLabel("出生年份").selectOption("1990");
  await page.getByLabel("出生月份").selectOption("05");
  await page.getByLabel("出生日期").selectOption("06");
  await page.getByLabel("出生小时").selectOption("08");
  await page.getByLabel("出生分钟").selectOption("30");
  await page.getByLabel("出生省份").selectOption("江苏省");
  await page.getByLabel("出生城市").selectOption("常州市");
  await page.getByLabel("出生区县").selectOption("金坛区");
  await page.getByRole("radio", { name: "男" }).check();
}

test("bazi deep checkout stays fail-closed at the unavailable gateway", async ({ page }, testInfo) => {
  const checkoutBodies: unknown[] = [];
  const fulfillmentRequests: string[] = [];
  const deepResultRequests: string[] = [];

  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.context().addCookies([
    {
      name: "mingli_csrf",
      value: "bazi-deep-e2e-csrf",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    const path = url.pathname;

    if (method === "GET" && path === "/api/v1/account") {
      await json(route, {
        user_id: "e2e-user-1",
        identities: [{
          id: "e2e-identity-1",
          provider: "email",
          masked_destination: "e2e***@example.com",
          verified_at: "2026-08-18T00:00:00Z",
        }],
      });
      return;
    }
    if (method === "GET" && path === "/api/v1/profiles") {
      await json(route, { profiles: [] });
      return;
    }
    if (method === "POST" && path === "/api/v1/profiles/drafts") {
      await json(route, { draft_id: "draft-1", status: "draft" }, 201);
      return;
    }
    if (method === "POST" && path === "/api/v1/profiles/drafts/draft-1/confirm") {
      await json(route, {
        profile_id: "profile-1",
        profile_version_id: "profile-version-1",
        subject_ref: "subject:e2e",
        version: 1,
        created_at: "2026-08-18T00:00:00Z",
      }, 201);
      return;
    }
    if (method === "POST" && path === "/api/v1/readings/preview") {
      await json(route, readingSummary(PREVIEW_READING_ID), 201);
      return;
    }
    if (method === "GET" && path === `/api/v1/readings/${PREVIEW_READING_ID}`) {
      await json(route, readingSummary(PREVIEW_READING_ID));
      return;
    }
    if (method === "GET" && path === `/api/v1/readings/${PREVIEW_READING_ID}/result`) {
      await json(route, {
        reading_version_id: PREVIEW_READING_ID,
        status: "accepted",
        accepted_copy: "免费确定性盘面已由服务端固定。",
        fact_panel: {
          question: "请核对免费八字盘面。",
          vocabulary: [],
          facts: [
            {
              ref: "fact:bazi-ui-lab/day-master",
              subject_ref: "subject:e2e",
              kind_id: "bazi.day-master",
              value: "丙火",
              display_text: "日主为丙火。",
            },
            {
              ref: "fact:bazi-ui-lab/month-order",
              subject_ref: "subject:e2e",
              kind_id: "bazi.month-order",
              value: "午月",
              display_text: "月令为午火；全局强弱与喜用神未裁定。",
            },
          ],
          evidence: [...BAZI_EVIDENCE_RESULT_EVIDENCE],
          findings: [],
          claim_scopes: [],
          limits: [{
            kind_id: "limit.unadjudicated-strength",
            public_text: "当前只展示月令事实，不输出全局身强身弱或喜用神结论。",
            scope_refs: ["career"],
            detail_ids: [],
          }],
          prior_answer: null,
          request_view: {
            subject_refs: ["subject:e2e"],
            capability_ids: ["bazi"],
            object_id: "natal",
            dimension_ids: ["career"],
            horizon: { kind_id: "life", start: null, end: null },
          },
        },
        view_model: BAZI_EVIDENCE_RESULT_VIEW_MODEL,
        verification: null,
        input_request: null,
        document: null,
      });
      return;
    }
    if (method === "POST" && path === "/api/v1/readings/bazi-deep") {
      await json(route, readingSummary(DEEP_READING_ID, {
        status: "input_ready",
        delivery_state: "payment_required",
      }), 201);
      return;
    }
    if (method === "POST" && path === "/api/v1/commerce/checkout") {
      checkoutBodies.push(request.postDataJSON());
      await json(route, {
        order: {
          order_id: "server-owned-order-1",
          reading_version_id: DEEP_READING_ID,
          product_id: "bazi-deep",
          product_version: "v1",
          amount_minor: 9900,
          currency: "CNY",
          status: "payment_pending",
          created_at: "2026-08-18T00:00:00Z",
          paid_at: null,
        },
        attempt: {
          attempt_id: "server-owned-attempt-1",
          channel: "fake",
          status: "pending",
          created_at: "2026-08-18T00:00:00Z",
        },
        gateway_status: "unavailable",
        redirect_url: null,
        created: true,
      }, 201);
      return;
    }
    if (method === "POST" && path.endsWith("/fulfillment")) {
      fulfillmentRequests.push(path);
    }
    if (method === "GET" && path === `/api/v1/readings/${DEEP_READING_ID}/result`) {
      deepResultRequests.push(path);
    }
    await json(route, { title: "Unhandled e2e API", detail: `${method} ${path}` }, 599);
  });

  await page.goto("/bazi", { waitUntil: "domcontentloaded" });
  await fillBaziInput(page);
  await page.getByRole("button", { name: /^立即排盘（免费）/ }).click();

  await expect(page.getByRole("heading", { name: "八字工作台" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "免费确定性盘面" })).toBeVisible();
  await expect(page.getByText("尚未确认付费")).toBeVisible();
  await page.getByRole("button", { name: "开始安全结账" }).click();

  await expect(page.getByRole("heading", { name: "支付入口暂不可用" }).first()).toBeVisible();
  expect(checkoutBodies).toEqual([{ reading_version_id: DEEP_READING_ID }]);
  expect(fulfillmentRequests).toEqual([]);
  expect(deepResultRequests).toEqual([]);
  await expect(page.getByText("server-owned-order-1")).toHaveCount(0);
  await expect(page.getByText("server-owned-attempt-1")).toHaveCount(0);
  await expect(page.getByText("八字深读结果")).toHaveCount(0);

  const readingArticle = page.getByRole("article", { name: "解读正文" });
  const readingSections = await readingArticle
    .locator(":scope > section")
    .evaluateAll((sections) => sections.map((section) => {
      const box = section.getBoundingClientRect();
      const contentBottom = Math.max(
        ...Array.from(section.children, (child) => child.getBoundingClientRect().bottom),
      );
      return {
        title: section.querySelector("h2")?.textContent ?? "",
        top: Math.round(box.top),
        bottom: Math.round(box.bottom),
        height: Math.round(box.height),
        trailingSpace: Math.round(box.bottom - contentBottom),
      };
    }));
  expect(readingSections.map((section) => section.title)).toEqual([
    "排盘结果",
    "阅读说明",
    "复核与追问",
  ]);
  expect(
    Math.max(...readingSections.map((section) => section.trailingSpace)),
    `${testInfo.project.name}px reading section dead space`,
  ).toBeLessThanOrEqual(96);
  expect(
    Math.max(
      0,
      ...readingSections.slice(1).map((section, index) => (
        section.top - readingSections[index]!.bottom
      )),
    ),
    `${testInfo.project.name}px gap between reading sections`,
  ).toBeLessThanOrEqual(1);
  const articleTail = await readingArticle.evaluate((article) => {
    const box = article.getBoundingClientRect();
    const contentBottom = Math.max(
      ...Array.from(article.children, (child) => child.getBoundingClientRect().bottom),
    );
    return Math.round(box.bottom - contentBottom);
  });
  expect(articleTail, `${testInfo.project.name}px reading article dead space`).toBeLessThanOrEqual(96);

  const width = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));
  expect(width.document, `${testInfo.project.name}px horizontal overflow`).toBeLessThanOrEqual(
    width.viewport,
  );

  const directory = resolve(
    process.env.BROWSER_EVIDENCE_DIR
      ?? resolve(process.cwd(), "e2e/screenshots/2026-08-18-bazi-deep-authority"),
    testInfo.project.name,
  );
  await mkdir(directory, { recursive: true });
  await page.screenshot({
    path: resolve(directory, "checkout-unavailable.png"),
    fullPage: true,
  });
});
