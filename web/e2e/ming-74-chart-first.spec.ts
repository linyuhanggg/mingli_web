import { expect, test, type Route } from "@playwright/test";

import {
  BAZI_EVIDENCE_RESULT_EVIDENCE,
  BAZI_EVIDENCE_RESULT_VIEW_MODEL,
} from "../src/fixtures/bazi-evidence-result";

const READING_ID = "ming-74-synthetic-preview";
const PROFILE_ID = "ming-74-synthetic-profile";
const VIEWPORTS = [
  { width: 360, height: 800 },
  { width: 1024, height: 768 },
  { width: 1279, height: 900 },
  { width: 1440, height: 900 },
] as const;

const CAPABILITY_A = {
  capability_id: "bazi",
  label: "八字",
  tier: "A" as const,
  source_system: "bazi",
  runtime_active_rule_count: 24,
  judgment_rule_count: 19,
  source_status: "available" as const,
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function summary() {
  return {
    reading_version_id: READING_ID,
    reading_root_id: `${READING_ID}-root`,
    profile_version_id: PROFILE_ID,
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
    created_at: "2026-08-31T00:00:00Z",
  };
}

function result() {
  return {
    reading_version_id: READING_ID,
    status: "accepted",
    accepted_copy: "合成资料的免费盘面。",
    capability: { current: CAPABILITY_A },
    fact_panel: {
      question: "请核对合成八字盘面。",
      vocabulary: [],
      facts: [
        {
          ref: "fact:synthetic/day-master",
          subject_ref: "subject:synthetic",
          kind_id: "bazi.day-master",
          value: "丙火",
          display_text: "日主为丙火。",
        },
        {
          ref: "fact:synthetic/month-order",
          subject_ref: "subject:synthetic",
          kind_id: "bazi.month-order",
          value: "午月",
          display_text: "月令为午火；全局强弱与喜用神未裁定。",
        },
      ],
      evidence: [...BAZI_EVIDENCE_RESULT_EVIDENCE],
      findings: [
        {
          kind_id: "kind.tendency",
          support_mode: "exact",
          public_text: "月令状态只确定季节层，整盘旺衰仍未裁定。",
          fact_refs: ["fact:synthetic/month-order"],
          evidence_refs: ["evidence:bazi-ui-lab-r02-04"],
          data: {
            claim_unit_id: "bazi.month-order-state-v1",
            hard_verdict: null,
          },
        },
        {
          kind_id: "kind.tendency",
          support_mode: "exact",
          public_text: "未知单元不应显示。",
          fact_refs: ["fact:synthetic/unknown"],
          evidence_refs: ["evidence:synthetic/unknown"],
          data: {
            claim_unit_id: "bazi.unknown-synthetic-unit-v1",
            hard_verdict: null,
          },
        },
      ],
      claim_scopes: [],
      limits: [],
      prior_answer: null,
      request_view: {
        subject_refs: ["subject:synthetic"],
        capability_ids: ["bazi"],
        object_id: "natal",
        dimension_ids: ["career"],
        horizon: { kind_id: "life", start: null, end: null },
      },
    },
    view_model: BAZI_EVIDENCE_RESULT_VIEW_MODEL,
    verification: null,
    input_request: null,
    document: {
      schema_version: "reading-document/v1",
      document_id: "reading-version:ming-74-synthetic-document",
      reading_version_id: READING_ID,
      accepted_copy_ref: "accepted-copy:ming-74-synthetic",
      product_version: "bazi/v1",
      presentation_contract_version: "bazi-presentation/v1",
      view_model: BAZI_EVIDENCE_RESULT_VIEW_MODEL,
      answer_summary: "合成资料的免费盘面。",
      subject_summaries: [{ subject_ref: "subject:synthetic", label: "合成受测对象" }],
      themes: [],
      claims: [],
      evidence: [],
      boundaries: [],
      actions: {
        correction: { enabled: false },
        follow_up: { enabled: false },
        export: { enabled: true },
        share: { enabled: true },
      },
      versions: {
        runtime_release: "runtime:synthetic",
        view_model_schema: "bazi-chart/v1",
        reading_document_schema: "reading-document/v1",
      },
    },
  };
}

test("MING-74 keeps the synthetic free chart first across required widths", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "1024", "One project loops through the exact acceptance widths.");

  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(({ profileId, readingId }) => {
    window.sessionStorage.setItem(
      `mingli.bazi-preview-recovery:${readingId}`,
      JSON.stringify({
        version: 1,
        readingId,
        profileVersionId: profileId,
        question: "请核对合成八字盘面。",
      }),
    );
  }, { profileId: PROFILE_ID, readingId: READING_ID });
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === "GET" && path === "/api/v1/account") {
      await json(route, {
        user_id: "synthetic-user",
        identities: [],
      });
      return;
    }
    if (request.method() === "GET" && path === "/api/v1/profiles") {
      await json(route, { profiles: [] });
      return;
    }
    if (request.method() === "GET" && path === `/api/v1/readings/${READING_ID}`) {
      await json(route, summary());
      return;
    }
    if (request.method() === "GET" && path === `/api/v1/readings/${READING_ID}/result`) {
      await json(route, result());
      return;
    }
    await json(route, { title: "Unhandled synthetic API", detail: path }, 599);
  });

  for (const viewport of VIEWPORTS) {
    await page.setViewportSize(viewport);
    await page.goto(`/bazi?reading=${READING_ID}&profile=${PROFILE_ID}`, {
      waitUntil: "domcontentloaded",
    });

    const workspace = page.getByRole("region", { name: "排盘工作台" });
    const dayMaster = workspace.getByText(/^日主 丙/);
    const pillars = workspace.getByRole("group", { name: "四柱" });
    const backButton = page.getByRole("button", { name: "返回录入" });

    await expect(workspace).toBeVisible();
    await expect(dayMaster).toBeInViewport();
    await expect(pillars).toBeInViewport();
    await expect(workspace.getByRole("heading", { name: "月令状态" })).toBeVisible();
    await expect(page.getByText("未知单元不应显示。")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "分享" })).toBeVisible();
    await expect(page.getByRole("button", { name: "创建 24 小时分享" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "导出报告" })).toBeVisible();
    await expect(page.getByRole("button", { name: "高清 PNG" })).toBeVisible();
    await expect(page.getByRole("button", { name: "报告 PDF" })).toBeVisible();

    const metrics = await page.evaluate(() => {
      const workspaceElement = document.querySelector<HTMLElement>("[aria-label='排盘工作台']")!;
      const chartHost = document.querySelector<HTMLElement>("[data-bazi-chart-host='true']")!;
      const chartPaneElement = workspaceElement.querySelector<HTMLElement>("[role='tabpanel']")!;
      const readingPaneElement = workspaceElement.querySelector<HTMLElement>("[aria-label='连续阅读面']")!;
      const dayMasterElement = Array.from(workspaceElement.querySelectorAll<HTMLElement>("p"))
        .find((element) => element.textContent?.startsWith("日主 丙"))!;
      const pillarGroup = workspaceElement.querySelector<HTMLElement>("[role='group'][aria-label='四柱']")!;
      const toolbarHeading = Array.from(document.querySelectorAll<HTMLElement>("h2"))
        .find((element) => element.textContent === "八字工作台")!;
      const back = Array.from(document.querySelectorAll<HTMLButtonElement>("button"))
        .find((element) => element.textContent?.includes("返回录入"))!;
      const firstPillar = pillarGroup.querySelector<HTMLButtonElement>("button")!;
      const focusables = Array.from(document.querySelectorAll<HTMLElement>(
        "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]",
      )).filter((element) => element.tabIndex >= 0);
      const chartRect = chartHost.getBoundingClientRect();
      const chartPaneRect = chartPaneElement.getBoundingClientRect();
      const readingPaneRect = readingPaneElement.getBoundingClientRect();
      const dayMasterRect = dayMasterElement.getBoundingClientRect();
      const pillarRect = pillarGroup.getBoundingClientRect();
      const backRect = back.getBoundingClientRect();
      const keyControlHeights = Array.from(chartHost.querySelectorAll<HTMLElement>("button:not([disabled])"))
        .map((element) => element.getBoundingClientRect().height);
      return {
        viewportWidth: document.documentElement.clientWidth,
        viewportHeight: window.innerHeight,
        documentWidth: document.documentElement.scrollWidth,
        chartLeft: chartRect.left,
        chartRight: chartRect.right,
        chartWidth: chartRect.width,
        chartPaneBottom: chartPaneRect.bottom,
        readingPaneTop: readingPaneRect.top,
        dayMasterTop: dayMasterRect.top,
        pillarBottom: pillarRect.bottom,
        chartBeforeToolbar: Boolean(
          workspaceElement.compareDocumentPosition(toolbarHeading)
          & Node.DOCUMENT_POSITION_FOLLOWING
        ),
        chartBeforeBackInKeyboardOrder:
          focusables.indexOf(firstPillar) >= 0
          && focusables.indexOf(firstPillar) < focusables.indexOf(back),
        backHeight: backRect.height,
        minimumChartControlHeight: Math.min(...keyControlHeights),
        reducedMotionTransition: getComputedStyle(firstPillar).transitionDuration,
        hasUnknownIdentifier: document.body.innerText.includes(
          "bazi.unknown-synthetic-unit-v1",
        ),
      };
    });

    expect(metrics.documentWidth, `${viewport.width}px page overflow`).toBeLessThanOrEqual(
      metrics.viewportWidth,
    );
    expect(metrics.chartLeft, `${viewport.width}px chart left clipping`).toBeGreaterThanOrEqual(0);
    expect(metrics.chartRight, `${viewport.width}px chart right clipping`).toBeLessThanOrEqual(
      metrics.viewportWidth,
    );
    expect(metrics.dayMasterTop, `${viewport.width}px day master is below the first screen`)
      .toBeLessThan(metrics.viewportHeight);
    expect(metrics.pillarBottom, `${viewport.width}px four pillars fit in the first screen`)
      .toBeLessThanOrEqual(metrics.viewportHeight);
    expect(metrics.readingPaneTop, `${viewport.width}px empty split column remains`)
      .toBeGreaterThanOrEqual(metrics.chartPaneBottom - 1);
    expect(metrics.chartBeforeToolbar).toBe(true);
    expect(metrics.chartBeforeBackInKeyboardOrder).toBe(true);
    expect(metrics.backHeight).toBeGreaterThanOrEqual(44);
    expect(metrics.minimumChartControlHeight).toBeGreaterThanOrEqual(44);
    expect(Number.parseFloat(metrics.reducedMotionTransition)).toBeLessThanOrEqual(0.001);
    expect(metrics.hasUnknownIdentifier).toBe(false);

    await page.screenshot({
      path: testInfo.outputPath(`ming-74-${viewport.width}.png`),
      fullPage: false,
    });

    await backButton.focus();
    const focusStyle = await backButton.evaluate((element) => {
      const style = getComputedStyle(element);
      return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth };
    });
    expect(focusStyle.outlineStyle).not.toBe("none");
    expect(Number.parseFloat(focusStyle.outlineWidth)).toBeGreaterThanOrEqual(2);

    console.log(`MING74_BROWSER ${JSON.stringify({ width: viewport.width, ...metrics })}`);
  }
});
