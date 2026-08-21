import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReadingResult } from "@/components/readings/reading-result";
import { resetApiCache } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

const VERSION_ID = "33333333-3333-4333-8333-333333333333";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function summary(capabilityId: "fortune" | "liuyao") {
  return {
    reading_version_id: VERSION_ID,
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    capability_id: capabilityId,
    product_id: capabilityId,
    version: 1,
    status: "accepted",
    object_id: capabilityId === "fortune" ? "near_time_personal" : "concrete_event",
    dimension_ids: ["career"],
    horizon:
      capabilityId === "fortune"
        ? { kind_id: "week", start: "2026-08-10", end: "2026-08-16" }
        : { kind_id: "instant", start: null, end: null },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-10T01:00:00Z",
  };
}

function capability(capabilityId: "fortune" | "liuyao") {
  return {
    capability_id: capabilityId,
    label: capabilityId === "fortune" ? "运势" : "六爻",
    tier: "B" as const,
    source_system: capabilityId,
    runtime_active_rule_count: 2,
    judgment_rule_count: 0,
    source_status: "available" as const,
  };
}

function verifiedEvidence() {
  return {
    ref: "evidence:classic-1",
    evidence_ref: "evidence:classic-1",
    rule_id: "rule:classic-1",
    source_title: "经典摘句",
    locator: "卷一",
    excerpt: "先定其基，再观其用。",
    verbatim_excerpt: "先定其基，再观其用。",
    verification_status: "verified_exact",
    supports_fact_refs: [],
    verbatim_citations: [
      {
        source_title: "经典摘句",
        locator: "卷一",
        verbatim_excerpt: "先定其基，再观其用。",
        verification_status: "verified_exact",
      },
    ],
  };
}

function fortuneView() {
  return {
    schema_version: "fortune-facts-view/v1",
    subject_ref: "fortune:fixture",
    natal_pillars: { year: "甲戌", month: "戊辰", day: "丙戌", hour: "辛卯" },
    day_master: { stem: "丙", element: "fire", polarity: "阳" },
    month_command: {
      branch: "辰",
      label: "辰月",
      main_qi: "戊",
      main_qi_element: "earth",
    },
    active_luck_cycle: "乙丑",
    target_day: "2026-08-14",
    target_period: { kind: "day", start: "2026-08-14", end: "2026-08-14" },
    available_periods: ["2026-08-14"],
    period_markers: [],
    calendar_normalization: {
      status: "calculated",
      algorithm_version: "fixture-v1",
      time_basis: {
        policy: "local_apparent_solar-v1",
        standard_meridian_degrees: 120,
        longitude_correction_seconds: 0,
        equation_of_time_seconds: 0,
        total_correction_seconds: 0,
        algorithm: { id: null, version: null, source: null, uncertainty_seconds: null },
        boundary: {
          distance_seconds: null,
          correction_changes_hour_branch: false,
          within_uncertainty: null,
        },
      },
      true_solar_time: {
        status: "apparent_solar_applied",
        policy: "local_apparent_solar-v1",
        longitude_correction_seconds: 0,
        equation_of_time_seconds: 0,
        total_correction_seconds: 0,
      },
      calendar_convention: {
        id: null,
        version: null,
        year_boundary: null,
        month_boundary: null,
        day_rollover: null,
        hour_basis: "true_solar",
        zi_hour_policy: null,
      },
    },
  };
}

function liuyaoFacts() {
  return [
    {
      ref: "fact:cast/calculated/liuyao/primary_hexagram",
      subject_ref: "liuyao:public-cast",
      kind_id: "kind.liuyao-structure",
      value: { name: "水山蹇", shi_line: 4, ying_line: 1 },
      display_text: "本卦：水山蹇",
    },
    {
      ref: "fact:cast/calculated/liuyao/changed_hexagram",
      subject_ref: "liuyao:public-cast",
      kind_id: "kind.liuyao-structure",
      value: { name: "水风井" },
      display_text: "变卦：水风井",
    },
    {
      ref: "fact:cast/calculated/liuyao/moving_lines",
      subject_ref: "liuyao:public-cast",
      kind_id: "kind.liuyao-structure",
      value: [2],
      display_text: "动爻：[2]",
    },
    {
      ref: "fact:cast/calculated/liuyao/shi_ying",
      subject_ref: "liuyao:public-cast",
      kind_id: "kind.liuyao-structure",
      value: { shi: 4, ying: 1 },
      display_text: "世应：世四应一",
    },
    {
      ref: "fact:cast/calculated/liuyao/lines",
      subject_ref: "liuyao:public-cast",
      kind_id: "kind.liuyao-structure",
      value: [
        { line: 1, state: "少阴", yin_yang: "阴", moving: false, roles: ["应"] },
        { line: 2, state: "老阳", yin_yang: "阳", moving: true, roles: [] },
        { line: 3, state: "少阳", yin_yang: "阳", moving: false, roles: [] },
        { line: 4, state: "少阴", yin_yang: "阴", moving: false, roles: ["世"] },
        { line: 5, state: "少阳", yin_yang: "阳", moving: false, roles: [] },
        { line: 6, state: "少阴", yin_yang: "阴", moving: false, roles: [] },
      ],
      display_text: "六爻：服务端公开盘面",
    },
  ];
}

function stubReady(
  capabilityId: "fortune" | "liuyao",
  overrides: Record<string, unknown> = {},
) {
  const fetchMock = vi.fn<typeof fetch>(async (url) => {
    const path = String(url);
    if (path === `/api/v1/readings/${VERSION_ID}`) {
      return jsonResponse(summary(capabilityId));
    }
    if (path === `/api/v1/readings/${VERSION_ID}/result`) {
      return jsonResponse({
        reading_version_id: VERSION_ID,
        status: "accepted",
        accepted_copy: null,
        fact_panel: {
          question: capabilityId === "fortune" ? "近七日最值得关注什么？" : "这次岗位面试能否进入下一轮？",
          vocabulary: [],
          facts: capabilityId === "liuyao" ? liuyaoFacts() : [],
          evidence: [verifiedEvidence()],
          findings: [],
          claim_scopes: [],
          limits: [],
        },
        view_model: capabilityId === "fortune" ? fortuneView() : null,
        capability: capability(capabilityId),
        verification: null,
        document: null,
        input_request: null,
        ...overrides,
      });
    }
    return jsonResponse({ title: "Unexpected request" }, 500);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  resetApiCache();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fortune + liuyao result shell", () => {
  it("puts fortune facts and a verified citation before notes, without construction copy", async () => {
    stubReady("fortune");
    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("heading", { level: 1, name: "运势" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "排盘结果" })).toBeVisible();
    expect(screen.getByText("日运本命四柱事实")).toBeVisible();
    expect(screen.getAllByText("先定其基，再观其用。").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "阅读说明" })).toBeVisible();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText(/Runtime|Provider|适配器/)).not.toBeInTheDocument();
  });

  it("puts liuyao plate facts first and does not invent a hexagram", async () => {
    stubReady("liuyao");
    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("heading", { level: 1, name: "六爻" })).toBeVisible();
    const plate = screen.getByRole("region", { name: "六爻卦象" });
    expect(plate).toBeVisible();
    expect(plate.compareDocumentPosition(screen.getByRole("heading", { name: "阅读说明" })) &
      Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText("水山蹇")).toBeVisible();
    expect(screen.getByText("水风井")).toBeVisible();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText(/Runtime|Provider|适配器/)).not.toBeInTheDocument();
  });

  it("stays empty when the server has no fortune plate or copy", async () => {
    stubReady("fortune", {
      fact_panel: {
        question: "近七日最值得关注什么？",
        vocabulary: [],
        facts: [],
        evidence: [],
        findings: [],
        claim_scopes: [],
        limits: [],
      },
      view_model: null,
      accepted_copy: null,
    });
    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("status", { name: "还没有可展示的盘面" })).toBeVisible();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
  });

  it("locks the result header to --font-size-page", () => {
    const css = readFileSync(resolve(process.cwd(), "src/components/app-surface.module.css"), "utf8");
    expect(css).toMatch(/\.readingHeader h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
  });

  it("does not put construction chrome on the production files", () => {
    for (const file of [
      "src/components/readings/reading-result.tsx",
      "src/components/readings/runtime-chart.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/§10|§6\.2|SecondarySurfaceFrame|AppPageHeader/);
    }
    const natal = readFileSync(
      resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"),
      "utf8",
    );
    const fortune = natal.slice(
      natal.indexOf("function FortuneFactsChart"),
      natal.indexOf("function TaiyiChart"),
    );
    expect(fortune).not.toMatch(/Runtime|Provider|适配器/);
    const liuyao = natal.slice(
      natal.indexOf("function LiuyaoChart"),
      natal.indexOf("function MeihuaChart"),
    );
    expect(liuyao).not.toMatch(/Runtime|Provider|适配器/);
  });
});
