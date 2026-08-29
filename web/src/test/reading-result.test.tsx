import { readFileSync } from "node:fs";
import { join } from "node:path";

import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReadingResult } from "@/components/readings/reading-result";
import { VerificationForm } from "@/components/readings/verification-form";
import { BAZI_EVIDENCE_RESULT_VIEW_MODEL } from "@/fixtures/bazi-evidence-result";
import { resetApiCache } from "@/lib/api";
import type { ReadingResultResponse } from "@/lib/api/contracts";

const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: routerPush,
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

function problemResponse(title: string, status: number) {
  return jsonResponse({ title, status, request_id: "request-1" }, status);
}

function guestSession() {
  return jsonResponse(
    {
      status: "active",
      expires_at: "2026-08-11T00:00:00Z",
      csrf_token: "csrf-token-with-at-least-thirty-two-characters",
    },
    201,
  );
}

function readingSummary(
  status: string,
  overrides: Partial<Record<string, unknown>> = {},
) {
  return {
    reading_version_id: VERSION_ID,
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    capability_id: "fortune",
    version: 1,
    status,
    object_id: "near_time_personal",
    dimension_ids: [],
    horizon: {
      kind_id: "week",
      start: "2026-08-10",
      end: "2026-08-16",
    },
    prior_answer: null,
    input_request: null,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

const acceptedCopy = "先给结论。\n\n再说明依据，原字原序。";
const acceptedCopyQuery = acceptedCopy.replace(/\s+/g, " ");

const baziCapabilityA = {
  capability_id: "bazi",
  label: "八字",
  tier: "A" as const,
  source_system: "bazi",
  runtime_active_rule_count: 24,
  judgment_rule_count: 19,
  source_status: "available" as const,
};

const baziTimeLayerEntitlement = {
  schema_version: "time-layer-entitlement/v1",
  capability_id: "bazi",
  resolution: "granted",
  free_boundary_layer_id: "year",
  paid_layer_ids: ["month", "day", "hour"],
  free_year_set: [2026],
  capability: {
    time_layers: [
      { layer_id: "life", label: "本命", available: true, unavailable_reason: null },
      { layer_id: "year", label: "流年", available: true, unavailable_reason: null },
      { layer_id: "month", label: "流月", available: true, unavailable_reason: null },
      { layer_id: "day", label: "流日", available: true, unavailable_reason: null },
      { layer_id: "hour", label: "流时", available: false, unavailable_reason: "本次结果尚未返回逐时盘面。" },
    ],
  },
  layers: [
    { layer_id: "life", tier: "free", access: "readable", upgrade_cta: null },
    { layer_id: "luck_cycles", tier: "free", access: "readable", upgrade_cta: null },
    { layer_id: "year", tier: "free", access: "readable", upgrade_cta: null },
    { layer_id: "month", tier: "paid", access: "readable", upgrade_cta: null },
    { layer_id: "day", tier: "paid", access: "readable", upgrade_cta: null },
    { layer_id: "hour", tier: "paid", access: "unavailable", upgrade_cta: null },
  ],
} satisfies NonNullable<ReadingResultResponse["time_layer_entitlement"]>;

const ziweiTimeLayerEntitlement = {
  schema_version: "time-layer-entitlement/v1",
  capability_id: "ziwei",
  resolution: "granted",
  free_boundary_layer_id: "year",
  paid_layer_ids: ["month", "day", "hour"],
  free_year_set: [2026],
  capability: {
    time_layers: [
      { layer_id: "life", label: "原局", available: true, unavailable_reason: null },
      { layer_id: "year", label: "流年", available: true, unavailable_reason: null },
      { layer_id: "month", label: "流月", available: true, unavailable_reason: null },
      { layer_id: "day", label: "流日", available: false, unavailable_reason: "本次结果未返回逐日盘面。" },
      { layer_id: "hour", label: "流时", available: false, unavailable_reason: "本次结果未返回逐时盘面。" },
    ],
  },
  layers: [
    { layer_id: "life", tier: "free", access: "readable", upgrade_cta: null },
    { layer_id: "major_limits", tier: "free", access: "readable", upgrade_cta: null },
    { layer_id: "year", tier: "free", access: "readable", upgrade_cta: null },
    { layer_id: "month", tier: "paid", access: "readable", upgrade_cta: null },
    { layer_id: "day", tier: "paid", access: "unavailable", upgrade_cta: null },
    { layer_id: "hour", tier: "paid", access: "unavailable", upgrade_cta: null },
  ],
} satisfies NonNullable<ReadingResultResponse["time_layer_entitlement"]>;

const ziweiMonthViewModel = {
  schema_version: "ziwei-chart/v1",
  subject_ref: "profile-version:ziwei-entitlement-fixture",
  life_palace_id: "0",
  body_palace_id: "6",
  palaces: ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"].map(
    (branch, index) => ({
      palace_id: String(index),
      label: index === 0 ? "命宫" : index === 6 ? "官禄" : `宫${index}`,
      heavenly_stem: "甲",
      earthly_branch: branch,
      major_stars: index === 0 ? ["紫微"] : [],
    }),
  ),
  time_layers: [
    { layer_id: "month", label: "流月", available: true, unavailable_reason: null },
  ],
  core_facts: {
    five_elements_class: "水二局",
    source_conditioned_patterns: [],
    ming_shen: null,
    major_limit_direction: null,
    major_limit_starting_age: null,
    major_limit_sequence: null,
    major_limits: null,
    transformations: null,
    star_facts: null,
    monthly_layers: [
      {
        year: 2026,
        month: 8,
        liu_yue: { life_palace: "申" },
        segments: [
          {
            start_inclusive: "2026-08-01",
            end_exclusive: "2026-09-01",
            liu_yue: {
              palace_assignments: [
                "子", "丑", "寅", "卯", "辰", "巳",
                "午", "未", "申", "酉", "戌", "亥",
              ].map((branch, index) => ({
                index,
                natal_branch: branch,
                natal_palace:
                  index === 0 ? "命宫" : index === 6 ? "官禄" : `宫${index}`,
                temporal_palace:
                  branch === "申"
                    ? "命宫"
                    : index === 0
                      ? "迁移"
                      : index === 6
                        ? "官禄"
                        : `宫${index}`,
                dynamic_stars: [],
                chart_palace: {
                  branch,
                  name:
                    index === 0 ? "命宫" : index === 6 ? "官禄" : `宫${index}`,
                },
              })),
              transformation_facts: [],
            },
          },
        ],
        representative_scope: "monthly",
      },
    ],
  },
} as const;

const meihuaCapabilityB = {
  capability_id: "meihua",
  label: "梅花易数",
  tier: "B" as const,
  source_system: "divination",
  runtime_active_rule_count: 3,
  judgment_rule_count: 3,
  source_status: "available" as const,
  user_decision_pending: true,
};

function factPanel() {
  return {
    question: "近七日最值得关注什么？",
    vocabulary: [
      { id: "term:steady", label: "稳中求进", description: "先守住节奏" },
    ],
    facts: [
      {
        ref: "fact:opaque-1",
        subject_ref: "profile-version:secret-profile-id",
        kind_id: "fact:career-structure",
        value: {
          birth_datetime: "1994-04-30T05:55:00+08:00",
          state_token: "opaque-runtime-token",
          candidate: "模型草稿",
          prompt: "内部提示词",
        },
        display_text: "当前结构更支持持续积累。",
      },
    ],
    evidence: [
      {
        ref: "evidence:opaque-classic-1",
        source_title: "滴天髓",
        locator: "卷一",
        excerpt: "顺势而为，先定其基。",
        supports_fact_refs: ["fact:opaque-1"],
      },
    ],
    findings: [
      {
        ref: "finding:opaque-1",
        subject_ref: "profile-version:secret-profile-id",
        dimension_ids: ["career"],
        kind_id: "finding:trend",
        data: { candidate: "不要显示" },
        fact_refs: ["fact:opaque-1"],
        evidence_refs: ["evidence:opaque-classic-1"],
        limit_kind_ids: ["limit:traditional"],
        support_mode: "exact",
      },
    ],
    claim_scopes: [
      {
        subject_ref: "profile-version:secret-profile-id",
        dimension_id: "career",
        allowed_kind_ids: ["finding:trend"],
        certainty_ceiling_id: "moderate",
        fact_refs: ["fact:opaque-1"],
        evidence_refs: ["evidence:opaque-classic-1"],
      },
    ],
    limits: [
      {
        kind_id: "limit:traditional",
        public_text: "仅供传统文化参考，不构成现实决策保证。",
        scope_refs: ["profile-version:secret-profile-id"],
        detail_ids: [],
      },
    ],
    prior_answer: "上一版已接纳正文。",
    request_view: {
      subject_refs: ["profile-version:secret-profile-id"],
      capability_ids: ["fortune"],
      object_id: "near_time_personal",
      dimension_ids: ["career"],
      horizon: {
        kind_id: "week",
        start: "2026-08-10",
        end: "2026-08-16",
      },
    },
  };
}

function readingResult(
  overrides: Partial<Record<string, unknown>> = {},
) {
  return {
    reading_version_id: VERSION_ID,
    status: "accepted",
    accepted_copy: acceptedCopy,
    fact_panel: factPanel(),
    verification: null,
    input_request: null,
    ...overrides,
  };
}

function readingDocument() {
  return {
    schema_version: "reading-document/v1",
    document_id: "reading-version:document-1",
    reading_version_id: VERSION_ID,
    accepted_copy_ref: "accepted-copy:document-1",
    product_version: "fortune-reading/v1",
    presentation_contract_version: "fortune-presentation/v1",
    view_model: { schema_version: "bazi-chart/v1" },
    answer_summary: "先稳住节奏。",
    subject_summaries: [{ subject_ref: "profile-version:test", label: "本人" }],
    themes: [],
    claims: [],
    evidence: [],
    boundaries: [{ limit_ref: "contract:disclosure", text: "仅供参考。" }],
    actions: {
      correction: { enabled: false },
      follow_up: { enabled: true },
      export: { enabled: false },
      share: { enabled: true },
    },
    versions: {
      runtime_release: "runtime:test",
      view_model_schema: "bazi-chart/v1",
      reading_document_schema: "reading-document/v1",
    },
  };
}

function getHeader(init: RequestInit | undefined, name: string): string | null {
  return new Headers(init?.headers).get(name);
}

function callsTo(fetchMock: ReturnType<typeof vi.fn>, suffix: string) {
  return fetchMock.mock.calls.filter(([url]) => String(url).endsWith(suffix));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  routerPush.mockReset();
});

beforeEach(() => {
  resetApiCache();
});

describe("ReadingVersionSummary polling and explicit result fetch", () => {
  it("polls the summary, then GETs /result and renders the exact Accepted Copy", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === `/api/v1/readings/${VERSION_ID}`) {
        return jsonResponse(readingSummary("accepted"));
      }
      if (path === `/api/v1/readings/${VERSION_ID}/result`) {
        return jsonResponse(readingResult());
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const acceptedRegion = await screen.findByRole("region", { name: "判断" });
    const copy = within(acceptedRegion).getByText(acceptedCopyQuery);
    expect(copy.textContent).toBe(acceptedCopy);
    expect(screen.queryByRole("heading", { name: "分享" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("追问")).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([url]) => String(url)).slice(0, 2)).toEqual([
      `/api/v1/readings/${VERSION_ID}`,
      `/api/v1/readings/${VERSION_ID}/result`,
    ]);
  });

  it("refreshes a stale prepared summary when the result is already accepted", async () => {
    let summaryCount = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === `/api/v1/readings/${VERSION_ID}`) {
        summaryCount += 1;
        return jsonResponse(
          readingSummary(summaryCount === 1 ? "prepared" : "accepted"),
        );
      }
      if (path === `/api/v1/readings/${VERSION_ID}/result`) {
        return jsonResponse(
          readingResult({
            document: {
              ...readingDocument(),
              actions: {
                ...readingDocument().actions,
                export: { enabled: true },
              },
            },
          }),
        );
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText(acceptedCopyQuery)).toBeVisible();
    expect(screen.getByText("已交付")).toBeVisible();
    expect(screen.getByLabelText("追问")).toBeVisible();
    expect(screen.getByRole("heading", { name: "分享" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "导出报告" })).toBeVisible();
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      `/api/v1/readings/${VERSION_ID}`,
      `/api/v1/readings/${VERSION_ID}/result`,
      `/api/v1/readings/${VERSION_ID}`,
    ]);
  });

  it("keeps an accepted result visible while retrying a failed final summary refresh", async () => {
    let summaryCount = 0;
    let resolveRetrySummary!: (response: Response) => void;
    const retrySummary = new Promise<Response>((resolve) => {
      resolveRetrySummary = resolve;
    });
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === `/api/v1/readings/${VERSION_ID}`) {
        summaryCount += 1;
        if (summaryCount === 1) {
          return jsonResponse(
            readingSummary("prepared", { poll_after_seconds: 0 }),
          );
        }
        if (summaryCount === 2) {
          return problemResponse("Summary temporarily unavailable", 503);
        }
        return retrySummary;
      }
      if (path === `/api/v1/readings/${VERSION_ID}/result`) {
        return jsonResponse(
          readingResult({
            document: {
              ...readingDocument(),
              actions: {
                ...readingDocument().actions,
                export: { enabled: true },
              },
            },
          }),
        );
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText(acceptedCopyQuery)).toBeVisible();
    expect(screen.getByText("事实已准备")).toBeVisible();
    expect(screen.queryByText("读取失败，请重试")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("追问")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "分享" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "导出报告" })).not.toBeInTheDocument();
    await waitFor(() => expect(summaryCount).toBe(3));

    await act(async () => {
      resolveRetrySummary(jsonResponse(readingSummary("accepted")));
    });

    expect(await screen.findByText("已交付")).toBeVisible();
    expect(screen.getByLabelText("追问")).toBeVisible();
    expect(screen.getByRole("heading", { name: "分享" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "导出报告" })).toBeVisible();
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      `/api/v1/readings/${VERSION_ID}`,
      `/api/v1/readings/${VERSION_ID}/result`,
      `/api/v1/readings/${VERSION_ID}`,
      `/api/v1/readings/${VERSION_ID}`,
      `/api/v1/readings/${VERSION_ID}/result`,
    ]);
  });

  it("does not fall back to a Bazi chart when a relationship ViewModel is unavailable", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === `/api/v1/readings/${VERSION_ID}`) {
        return jsonResponse(
          readingSummary("accepted", {
            capability_id: "bazi",
            product_id: "bazi-relationship",
          }),
        );
      }
      if (path === `/api/v1/readings/${VERSION_ID}/result`) {
        return jsonResponse(
          readingResult({
            view_model: null,
            document: null,
          }),
        );
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("heading", { name: "事实" })).toBeInTheDocument();
    expect(screen.queryByText("八字盘面")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "分享" })).not.toBeInTheDocument();
  });

  it("shows unavailable when GET /result 200 has no view_model or document", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === `/api/v1/readings/${VERSION_ID}`) {
        return jsonResponse(
          readingSummary("accepted", {
            capability_id: "bazi",
            product_id: "bazi-relationship",
          }),
        );
      }
      if (path === `/api/v1/readings/${VERSION_ID}/result`) {
        return jsonResponse(
          readingResult({
            accepted_copy: null,
            view_model: null,
            document: null,
            fact_panel: null,
            capability: {
              ...baziCapabilityA,
              source_status: "available",
            },
          }),
        );
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const unavailable = await screen.findByRole("status", {
      name: "结果服务暂时不可用，不会展示未确认内容",
    });
    expect(unavailable).toHaveAttribute("data-state", "unavailable");
    expect(screen.getByRole("button", { name: "重试" })).toBeEnabled();
    expect(screen.queryByText("八字盘面")).not.toBeInTheDocument();
    expect(screen.queryByText("relationship_signals")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "判断" })).not.toBeInTheDocument();
  });

  it("shows unavailable when GET /result 200 has no chart and capability source is unavailable", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            accepted_copy: null,
            view_model: null,
            document: null,
            fact_panel: null,
            capability: {
              ...baziCapabilityA,
              source_status: "unavailable",
            },
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "bazi",
          product_id: "bazi-relationship",
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const unavailable = await screen.findByRole("status", {
      name: "结果服务暂时不可用，不会展示未确认内容",
    });
    expect(unavailable).toHaveAttribute("data-state", "unavailable");
    expect(screen.queryByText("八字盘面")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeEnabled();
  });

  it("shows unavailable when GET /result 200 is tier C with no chart payload", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            accepted_copy: null,
            view_model: null,
            document: null,
            fact_panel: null,
            capability: {
              ...baziCapabilityA,
              tier: "C",
              source_status: "available",
            },
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "bazi",
          product_id: "bazi",
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const unavailable = await screen.findByRole("status", {
      name: "结果服务暂时不可用，不会展示未确认内容",
    });
    expect(unavailable).toHaveAttribute("data-state", "unavailable");
    expect(screen.queryByRole("region", { name: "排盘工作台" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeEnabled();
  });

  it("renders a typed Runtime chart while the narrative is still prepared", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            status: "prepared",
            accepted_copy: null,
            capability: meihuaCapabilityB,
            view_model: {
              schema_version: "meihua-chart/v1",
              subject_ref: "meihua:test",
              question: "这件事如何推进？",
              casting_method: "time",
              primary_hexagram: {
                name: "水雷屯",
                upper_trigram: "坎",
                lower_trigram: "震",
              },
              mutual_hexagram: {
                name: "山地剥",
                upper_trigram: "艮",
                lower_trigram: "坤",
              },
              changed_hexagram: null,
              moving_lines: [3],
              body_use: {
                body: { position: "lower", trigram: "震", element: "木" },
                use: { position: "upper", trigram: "坎", element: "水" },
                relation: "生",
                status: "calculated_relation_not_verdict",
              },
            },
          }),
        );
      }
      return jsonResponse(
        readingSummary("prepared", {
          capability_id: "meihua",
          object_id: "concrete_event",
          horizon: { kind_id: "instant", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText("按时间起卦")).toBeVisible();
    expect(screen.getByText("水雷屯")).toBeVisible();
    expect(screen.queryByText("calculated_relation_not_verdict")).not.toBeInTheDocument();
    expect(screen.getAllByText("已计算关系").length).toBeGreaterThan(0);
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/result"))).toBe(true);
    expect(screen.queryByText("复核与追问")).not.toBeInTheDocument();
    unmount();
  });

  it("renders Hecan as a cross-art view even when its Runtime primary is Bazi", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            status: "prepared",
            accepted_copy: null,
            capability: baziCapabilityA,
            view_model: {
              schema_version: "hecan-view/v1",
              subject_ref: "profile-version:test",
              selected_art_ids: ["bazi", "ziwei"],
              dimensions: [
                {
                  dimension_id: "career",
                  signals: [],
                  convergence: ["两术目前只声明共同事实范围。"],
                  disagreements: [],
                  missing_art_ids: [],
                },
              ],
            },
          }),
        );
      }
      return jsonResponse(
        readingSummary("prepared", {
          capability_id: "bazi",
          product_id: "hecan",
          object_id: "natal",
          horizon: { kind_id: "life", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText(/命盘合参/)).toBeVisible();
    expect(screen.getAllByText(/共同事实范围/).length).toBeGreaterThan(0);
    expect(screen.queryByText("八字命盘")).not.toBeInTheDocument();
  });

  it("renders structured facts, evidence, limits, prior answer, and server horizon without opaque refs", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) return jsonResponse(readingResult());
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText("当前结构更支持持续积累。")).toBeVisible();
    expect(screen.getByText("滴天髓")).toBeVisible();
    expect(screen.getByText("顺势而为，先定其基。")).toBeVisible();
    expect(
      screen.getByText("支持事实：当前结构更支持持续积累。"),
    ).toBeVisible();
    expect(screen.getByText("仅供传统文化参考，不构成现实决策保证。")).toBeVisible();
    expect(screen.getByText("上一版已接纳正文。")).toBeVisible();
    expect(screen.getAllByText(/2026年8月10日/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/2026年8月16日/).length).toBeGreaterThan(0);

    const visible = document.body.textContent ?? "";
    expect(visible).not.toMatch(
      /fact:opaque|evidence:opaque|finding:opaque|profile-version:secret|1994-04-30|opaque-runtime-token|模型草稿|内部提示词|不要显示/i,
    );
    expect(visible).not.toContain("state_token");
  });

  it("keeps polling after 15 seconds, offers a preserved restart after 60 seconds, and caps automatic polling at 10 minutes", async () => {
    vi.useFakeTimers();
    const startedAt = Date.parse("2026-08-29T12:00:00Z");
    vi.setSystemTime(startedAt);
    const onRestart = vi.fn();
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async () => (
      jsonResponse(readingSummary("input_ready", {
        created_at: new Date(startedAt).toISOString(),
        poll_after_seconds: 30,
        poll_required: true,
      }))
    ));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <ReadingResult
        onRestart={onRestart}
        readingId={VERSION_ID}
        startedAt={startedAt}
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });
    expect(screen.getByRole("link", { name: "稍后查看" })).toHaveAttribute(
      "href",
      "/account/history",
    );
    expect(screen.queryByRole("button", { name: "重试（保留原资料）" }))
      .not.toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(45_000);
    });
    act(() => {
      screen.getByRole("button", { name: "重试（保留原资料）" }).click();
    });
    expect(onRestart).toHaveBeenCalledTimes(1);
    const callsAtOneMinute = fetchMock.mock.calls.length;
    expect(callsAtOneMinute).toBeGreaterThan(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(9 * 60_000);
    });
    expect(screen.getByText("自动检查已暂停")).toBeVisible();
    const callsAtCap = fetchMock.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2 * 60_000);
    });
    expect(fetchMock).toHaveBeenCalledTimes(callsAtCap);

    act(() => {
      screen.getByRole("button", { name: "重新检查状态" }).click();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(fetchMock).toHaveBeenCalledTimes(callsAtCap + 1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2 * 60_000);
    });
    expect(fetchMock).toHaveBeenCalledTimes(callsAtCap + 1);
  });

  it("aborts an in-flight automatic request at the cap and gives a manual check a fresh controller", async () => {
    vi.useFakeTimers();
    const startedAt = Date.parse("2026-08-29T12:00:00Z");
    vi.setSystemTime(startedAt + 599_000);
    let requestCount = 0;
    let automaticSignal: AbortSignal | undefined;
    let manualSignal: AbortSignal | undefined;
    let resolveAutomatic!: (response: Response) => void;
    const automaticResponse = new Promise<Response>((resolve) => {
      resolveAutomatic = resolve;
    });
    const onPollError = vi.fn();
    const onSummary = vi.fn();
    const summary = readingSummary("runtime_unknown", {
      created_at: new Date(startedAt).toISOString(),
      poll_after_seconds: 30,
      poll_required: true,
    });
    const fetchMock = vi.fn<typeof fetch>((_url, init) => {
      requestCount += 1;
      if (requestCount === 1) {
        automaticSignal = init?.signal ?? undefined;
        return automaticResponse;
      }
      manualSignal = init?.signal ?? undefined;
      return Promise.resolve(jsonResponse(summary));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <ReadingResult
        onPollError={onPollError}
        onSummary={onSummary}
        readingId={VERSION_ID}
        startedAt={startedAt}
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(automaticSignal).toBeDefined();
    expect(automaticSignal?.aborted).toBe(false);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(screen.getByText("自动检查已暂停")).toBeVisible();
    expect(automaticSignal?.aborted).toBe(true);

    await act(async () => {
      resolveAutomatic(jsonResponse(summary));
      await Promise.resolve();
    });
    expect(onSummary).not.toHaveBeenCalled();
    expect(onPollError).not.toHaveBeenCalled();

    act(() => {
      screen.getByRole("button", { name: "重新检查状态" }).click();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(manualSignal).toBeDefined();
    expect(manualSignal).not.toBe(automaticSignal);
    expect(manualSignal?.aborted).toBe(false);
    expect(onSummary).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2 * 60_000);
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("reports typed summaries and poll failures to the parent owner", async () => {
    const onSummary = vi.fn();
    const onPollError = vi.fn();
    const fetchMock = vi.fn<typeof fetch>(async (url) => (
      String(url).includes("failed-version")
        ? problemResponse("暂时无法读取状态", 500)
        : jsonResponse(readingSummary("runtime_unknown"))
    ));
    vi.stubGlobal("fetch", fetchMock);

    const { rerender } = render(
      <ReadingResult
        onPollError={onPollError}
        onSummary={onSummary}
        readingId="summary-version"
      />,
    );
    await waitFor(() => expect(onSummary).toHaveBeenCalledTimes(1));
    expect(onSummary).toHaveBeenCalledWith(
      expect.objectContaining({ status: "runtime_unknown" }),
    );

    rerender(
      <ReadingResult
        onPollError={onPollError}
        onSummary={onSummary}
        readingId="failed-version"
      />,
    );
    await waitFor(() => expect(onPollError).toHaveBeenCalledTimes(1));
    expect(onPollError.mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({ message: "暂时无法读取状态" }),
    );
  });

  it("keeps one owner across same-id rerenders and aborts the old request when the id changes", async () => {
    let oldSignal: AbortSignal | undefined;
    const fetchMock = vi.fn<typeof fetch>((url, init) => {
      if (String(url).includes("old-version")) {
        oldSignal = init?.signal ?? undefined;
        return new Promise<Response>((_resolve, reject) => {
          oldSignal?.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        });
      }
      return Promise.resolve(jsonResponse(readingSummary("runtime_unknown")));
    });
    vi.stubGlobal("fetch", fetchMock);

    const firstSummary = vi.fn();
    const secondSummary = vi.fn();
    const { rerender } = render(
      <StrictMode>
        <ReadingResult onSummary={firstSummary} readingId="old-version" />
      </StrictMode>,
    );
    await waitFor(() => expect(oldSignal).toBeDefined());

    rerender(
      <StrictMode>
        <ReadingResult onSummary={secondSummary} readingId="old-version" />
      </StrictMode>,
    );
    await act(async () => {
      await Promise.resolve();
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(oldSignal?.aborted).toBe(false);

    rerender(
      <StrictMode>
        <ReadingResult onSummary={secondSummary} readingId="new-version" />
      </StrictMode>,
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(oldSignal?.aborted).toBe(true);
    await waitFor(() => expect(secondSummary).toHaveBeenCalledTimes(1));
    expect(firstSummary).not.toHaveBeenCalled();
  });

  it.each([
    ["input_ready", "准备解读"],
    ["prepared", "事实已准备"],
    ["completing", "正在接纳正文"],
    ["delayed", "交付延迟"],
  ])("shows the real %s state and the server-provided horizon", async (status, text) => {
    const fetchMock = vi.fn<typeof fetch>(async (url) =>
      String(url).endsWith("/result")
        ? jsonResponse(readingResult({ status }))
        : jsonResponse(readingSummary(status)),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const matches = await screen.findAllByText(text);
    expect(matches.length).toBeGreaterThan(0);
    expect(matches[0]).toBeVisible();
    const horizons = screen.getAllByText(/2026年8月10日.*2026年8月16日/);
    expect(horizons.length).toBeGreaterThan(0);
    expect(screen.queryByText(/排队中/)).not.toBeInTheDocument();
  });

  it("keeps runtime_unknown explicit and offers a manual state check", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse(readingSummary("runtime_unknown")));
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText(/运行状态暂时未知/)).toBeVisible();
    expect(screen.getByRole("button", { name: /重新检查状态/ })).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shows terminal_stopped as a terminal state with a restart path", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        jsonResponse(readingSummary("terminal_stopped")),
      ),
    );

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText(/本次解读已停止/)).toBeVisible();
    expect(screen.getByRole("link", { name: /重新发起/ })).toHaveAttribute(
      "href",
      "/app",
    );
  });

  it("maps a 401 poll error to an unauthorized state with a login action", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(problemResponse("登录状态已失效", 401)),
    );

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("status", { name: "需要登录才能看这份结果" })).toBeVisible();
    expect(screen.getByRole("link", { name: "登录后继续" })).toHaveAttribute("href", "/auth/login");
    expect(screen.queryByRole("button", { name: "重试" })).not.toBeInTheDocument();
  });

  it("maps a 503 poll error to an unavailable pending state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(problemResponse("结果服务暂不可用", 503)),
    );

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("status", { name: "结果服务暂时不可用，不会展示未确认内容" })).toBeVisible();
    expect(screen.getByText("结果服务暂不可用")).toBeVisible();
    expect(screen.getByRole("button", { name: "重试" })).toBeVisible();
  });

  it("maps a 404 result fetch to empty with a clickable retry, not error", async () => {
    let resultCount = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        resultCount += 1;
        return resultCount === 1
          ? problemResponse("Reading not found", 404)
          : jsonResponse(readingResult());
      }
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);

    const empty = await screen.findByRole("status", { name: "还没有可展示的盘面" });
    expect(empty).toBeVisible();
    expect(empty).toHaveAttribute("data-state", "empty");
    expect(empty).toHaveTextContent("这份结果不存在或不属于当前会话，不会用演示数据填满。");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "读取失败，请重试" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "待接入" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Reading not found" })).not.toBeInTheDocument();
    const retry = screen.getByRole("button", { name: "重试" });
    expect(retry).toBeEnabled();
    await user.click(retry);
    expect(await screen.findByText(acceptedCopyQuery)).toBeVisible();
    expect(resultCount).toBe(2);
  });

  it("maps a 404 poll error to empty instead of unavailable or error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(problemResponse("Reading not found", 404)),
    );

    render(<ReadingResult readingId={VERSION_ID} />);

    const empty = await screen.findByRole("status", { name: "还没有可展示的盘面" });
    expect(empty).toHaveAttribute("data-state", "empty");
    expect(empty).toHaveTextContent("这份结果不存在或不属于当前会话，不会用演示数据填满。");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "结果服务暂时不可用，不会展示未确认内容" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeEnabled();
  });

  it("turns a transient poll error into a manual retry and then fetches the result", async () => {
    let pollCount = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) return jsonResponse(readingResult());
      pollCount += 1;
      return pollCount === 1
        ? problemResponse("暂时无法读取状态", 500)
        : jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/暂时无法读取状态/);
    await user.click(screen.getByRole("button", { name: /重试/ }));

    expect(await screen.findByText(acceptedCopyQuery)).toBeVisible();
    expect(pollCount).toBe(2);
  });

  it("shows an accepted-result fetch error instead of getting stuck in loading", async () => {
    let resultCount = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        resultCount += 1;
        return resultCount === 1
          ? problemResponse("正文暂时读取失败", 500)
          : jsonResponse(readingResult());
      }
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("正文暂时读取失败");
    await user.click(screen.getByRole("button", { name: "重试" }));
    expect(await screen.findByText(acceptedCopyQuery)).toBeVisible();
    expect(resultCount).toBe(2);
  });

  it("renders the returned Liuyao plate as six accessible lines with moving and shi-ying labels", async () => {
    const liuyaoFacts = [
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
          {
            line: 1,
            state: "少阴",
            yin_yang: "阴",
            moving: false,
            najia: { ganzhi: "戊辰" },
            six_relative: "父母",
            six_spirit: "青龙",
            roles: ["应"],
          },
          {
            line: 2,
            state: "老阳",
            yin_yang: "阳",
            moving: true,
            najia: { ganzhi: "戊午" },
            six_relative: "官鬼",
            six_spirit: "朱雀",
            roles: [],
            changed_line: {
              yin_yang: "阴",
              najia: { ganzhi: "辛亥" },
              six_relative: "子孙",
            },
          },
          {
            line: 3,
            state: "少阳",
            yin_yang: "阳",
            moving: false,
            najia: { ganzhi: "戊申" },
            six_relative: "兄弟",
            six_spirit: "勾陈",
            roles: [],
          },
          {
            line: 4,
            state: "少阴",
            yin_yang: "阴",
            moving: false,
            najia: { ganzhi: "戊戌" },
            six_relative: "兄弟",
            six_spirit: "螣蛇",
            roles: ["世"],
          },
          {
            line: 5,
            state: "少阳",
            yin_yang: "阳",
            moving: false,
            najia: { ganzhi: "戊子" },
            six_relative: "子孙",
            six_spirit: "白虎",
            roles: [],
          },
          {
            line: 6,
            state: "少阴",
            yin_yang: "阴",
            moving: false,
            najia: { ganzhi: "戊寅" },
            six_relative: "妻财",
            six_spirit: "玄武",
            roles: [],
          },
        ],
        display_text: "六爻：服务端公开盘面",
      },
    ];
    const liuyaoEvidence = [
      {
        ref: "evidence:liuyao-plate",
        source_title: "卜筮正宗",
        locator: "世应章",
        excerpt: "世为己，应为彼。",
        supports_fact_refs: [
          "fact:cast/calculated/liuyao/primary_hexagram",
          "fact:cast/calculated/liuyao/lines",
        ],
      },
    ];
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            fact_panel: {
              ...factPanel(),
              question: "这次岗位面试能否进入下一轮？",
              facts: liuyaoFacts,
              evidence: liuyaoEvidence,
              request_view: {
                subject_refs: ["liuyao:public-cast"],
                capability_ids: ["liuyao"],
                object_id: "concrete_event",
                dimension_ids: ["career", "outcome"],
                horizon: {
                  kind_id: "instant",
                  start: null,
                  end: null,
                },
              },
            },
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "liuyao",
          object_id: "concrete_event",
          dimension_ids: ["career", "outcome"],
          horizon: { kind_id: "instant", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const plate = await screen.findByRole("region", { name: "六爻卦象" });
    expect(within(plate).getByText("水山蹇")).toBeVisible();
    expect(within(plate).getByText("水风井")).toBeVisible();
    const lines = within(plate).getAllByRole("listitem");
    expect(lines).toHaveLength(6);
    expect(within(lines[0]).getByText("上爻")).toBeVisible();
    expect(within(lines[4]).getByText("二爻")).toBeVisible();
    expect(within(lines[4]).getByText("动爻")).toBeVisible();
    expect(within(lines[2]).getByText("世")).toBeVisible();
    expect(within(lines[5]).getByText("应")).toBeVisible();
    expect(within(plate).getByText(/1 条依据与卦象事实相连/)).toBeVisible();
    expect(within(plate).getByRole("link", { name: "查看依据" })).toHaveAttribute(
      "href",
      "#reading-evidence-title",
    );
  });

  it("keeps a dedicated Liuyao surface but refuses to invent a plate from unknown facts", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            fact_panel: {
              ...factPanel(),
              facts: [
                {
                  ref: "fact:opaque-1",
                  subject_ref: "liuyao:public-cast",
                  kind_id: "kind.unknown",
                  value: { internal_shape: true },
                  display_text: "服务端返回了一项暂未识别的公开事实。",
                },
              ],
              evidence: [],
            },
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "liuyao",
          object_id: "concrete_event",
          horizon: { kind_id: "instant", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const plate = await screen.findByRole("region", { name: "六爻卦象" });
    expect(within(plate).getByText(/服务端未返回可解析的公开卦象结构/)).toBeVisible();
    expect(within(plate).getByText(/不会自行补算/)).toBeVisible();
    expect(within(plate).getAllByRole("listitem")).toHaveLength(6);
  });

  it("warns when the server names a hexagram but returns an incomplete line set", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            fact_panel: {
              ...factPanel(),
              facts: [
                {
                  ref: "fact:cast/calculated/liuyao/primary_hexagram",
                  subject_ref: "liuyao:public-cast",
                  kind_id: "fact:calculation",
                  value: { name: "水山蹇" },
                  display_text: "本卦：水山蹇",
                },
                {
                  ref: "fact:cast/calculated/liuyao/lines",
                  subject_ref: "liuyao:public-cast",
                  kind_id: "fact:calculation",
                  value: [
                    { line: 1, yin_yang: "阳" },
                    { line: 2, yin_yang: "阴" },
                  ],
                  display_text: "六爻：仅返回部分爻位",
                },
              ],
              evidence: [],
            },
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "liuyao",
          object_id: "concrete_event",
          horizon: { kind_id: "instant", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const plate = await screen.findByRole("region", { name: "六爻卦象" });
    expect(within(plate).getByText("水山蹇")).toBeVisible();
    expect(within(plate).getByText(/仅返回 2\/6 个可解析爻位/)).toBeVisible();
    expect(within(plate).getAllByRole("listitem")).toHaveLength(6);
  });
});

describe("fortune period timeline", () => {
  it("renders every server period marker as an ordered timeline before general facts", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            fact_panel: {
              ...factPanel(),
              facts: [
                {
                  ref: "fact:weekly-markers-1",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:period_markers",
                  display_text: "周期确定性标记：已由服务端计算",
                  value: [
                    {
                      date: "2026-08-10",
                      day_pillar: "甲子",
                      day_role: "正财",
                      active_luck_cycle: "戊子",
                    },
                    {
                      date: "2026-08-11",
                      day_pillar: "乙丑",
                      day_role: "偏财",
                    },
                  ],
                },
                {
                  ref: "fact:weekly-markers-2",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:runtime-display",
                  display_text: "period_markers: 已由服务端计算",
                  value: [
                    {
                      date: "2026-08-12",
                      day_pillar: "丙寅",
                      active_luck_cycle: "戊子",
                    },
                  ],
                },
                {
                  ref: "fact:general",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:career-structure",
                  display_text: "这一周宜先稳住手头节奏。",
                  value: null,
                },
              ],
            },
          }),
        );
      }
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const timeline = await screen.findByRole("region", { name: "近七日周期" });
    const list = within(timeline).getByRole("list");
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(3);

    expect(within(items[0]).getByText("2026年8月10日")).toBeVisible();
    expect(within(items[0]).getByText("甲子")).toBeVisible();
    expect(within(items[0]).getByText("正财")).toBeVisible();
    expect(within(items[0]).getByText("戊子")).toBeVisible();
    expect(within(items[1]).getByText("2026年8月11日")).toBeVisible();
    expect(within(items[1]).getByText("乙丑")).toBeVisible();
    expect(within(items[1]).getByText("偏财")).toBeVisible();
    expect(within(items[1]).queryByText("当前大运")).not.toBeInTheDocument();
    expect(within(items[2]).getByText("2026年8月12日")).toBeVisible();
    expect(within(items[2]).getByText("丙寅")).toBeVisible();
    expect(within(items[2]).queryByText("日主关系")).not.toBeInTheDocument();

    const judgment = screen.getByRole("heading", { name: "判断" });
    const timelineHeading = within(timeline).getByRole("heading", {
      name: "近七日周期",
    });
    const facts = screen.getByRole("heading", { name: "事实" });
    expect(
      timelineHeading.compareDocumentPosition(facts) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      facts.compareDocumentPosition(judgment) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    const notes = screen.getByRole("heading", { name: "阅读说明" });
    expect(
      judgment.compareDocumentPosition(notes) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByRole("heading", { name: "依据与边界" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "复核与追问" })).toBeVisible();
    expect(screen.getByText("这一周宜先稳住手头节奏。")).toBeVisible();
    expect(screen.getAllByText("甲子")).toHaveLength(1);
  });

  it("omits an empty or unparseable marker payload without inventing dates", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            fact_panel: {
              ...factPanel(),
              facts: [
                {
                  ref: "fact:empty-markers",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:period_markers",
                  display_text: "周期确定性标记：已由服务端计算",
                  value: [null, 12, {}, { date: " ", day_pillar: "" }],
                },
              ],
            },
          }),
        );
      }
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("heading", { level: 1, name: "运势" })).toBeVisible();
    expect(screen.queryByRole("region", { name: "近七日周期" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "事实" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/第 1 日|第 1 项|公开标记已就绪/);
  });
});

describe("waiting_input requirements[].any_of[]", () => {
  it("renders real runtime fields, focuses the first error, and posts only typed values", async () => {
    const inputRequest = {
      requirements: [
        {
          any_of: [
            {
              id: "cast_1",
              label: "初爻",
              type_id: "integer",
              description: "请输入 6、7、8 或 9",
              choices: [],
            },
          ],
        },
        {
          any_of: [
            {
              id: "zi_policy",
              label: "子时口径",
              type_id: "choice",
              description: null,
              choices: [
                { id: "midnight", label: "午夜换日", description: null },
                { id: "solar", label: "太阳时", description: null },
              ],
            },
          ],
        },
      ],
    };
    let pollCount = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return guestSession();
      if (path.endsWith("/input")) {
        return jsonResponse(readingSummary("input_ready"), 201);
      }
      if (path.endsWith("/result")) return jsonResponse(readingResult());
      pollCount += 1;
      return pollCount === 1
        ? jsonResponse(
            readingSummary("waiting_input", { input_request: inputRequest }),
          )
        : jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);
    await screen.findByText("补充资料");
    const submit = screen.getByRole("button", { name: /提交补充资料/ });
    await user.click(submit);

    const firstField = screen.getByLabelText("初爻");
    await waitFor(() => expect(firstField).toHaveFocus());
    expect(firstField).toHaveAttribute("aria-required", "true");
    expect(firstField).toHaveAttribute("aria-invalid", "true");
    expect(firstField).toHaveAttribute("aria-describedby");
    expect(screen.getByRole("alert")).toHaveTextContent(/必填/);

    await user.type(firstField, "8");
    await user.selectOptions(screen.getByLabelText("子时口径"), "midnight");
    await user.click(submit);

    const inputCall = callsTo(fetchMock, "/input")[0];
    expect(inputCall[0]).toBe(`/api/v1/readings/${VERSION_ID}/input`);
    expect(JSON.parse(String(inputCall[1]?.body))).toEqual({
      values: { cast_1: 8, zi_policy: "midnight" },
    });
    expect(String(inputCall[1]?.body)).not.toMatch(
      /state_token|candidate|prompt|birth_datetime/i,
    );
    expect(await screen.findByText(acceptedCopyQuery)).toBeVisible();
  });

  it("keeps the submit label visible and blocks duplicate input submissions while busy", async () => {
    const inputRequest = {
      requirements: [
        {
          any_of: [
            {
              id: "fixture_input",
              label: "合同测试输入",
              type_id: "text",
              description: null,
              choices: [],
            },
          ],
        },
      ],
    };
    let releaseInput: (response: Response) => void = () => {};
    const pendingInput = new Promise<Response>((resolve) => {
      releaseInput = resolve;
    });
    const fetchMock = vi.fn<typeof fetch>((url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return Promise.resolve(guestSession());
      if (path.endsWith("/input")) return pendingInput;
      return Promise.resolve(
        jsonResponse(
          readingSummary("waiting_input", { input_request: inputRequest }),
        ),
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);
    await user.type(await screen.findByLabelText("合同测试输入"), "已补充");
    const submit = screen.getByRole("button", { name: /提交补充资料/ });
    await user.click(submit);
    await waitFor(() => expect(callsTo(fetchMock, "/input")).toHaveLength(1));

    expect(submit).toHaveAccessibleName(/提交补充资料.*正在提交/);
    expect(submit).toHaveAttribute("aria-busy", "true");
    expect(submit).toBeDisabled();
    submit.closest("form")?.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    expect(callsTo(fetchMock, "/input")).toHaveLength(1);

    releaseInput(jsonResponse(readingSummary("input_ready"), 201));
  });

  it("requires exactly one value from each any_of group", async () => {
    const inputRequest = {
      requirements: [
        {
          any_of: [
            {
              id: "known_time",
              label: "已知时刻",
              type_id: "text",
              description: null,
              choices: [],
            },
            {
              id: "time_range",
              label: "大致时段",
              type_id: "text",
              description: null,
              choices: [],
            },
          ],
        },
      ],
    };
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return guestSession();
      return jsonResponse(
        readingSummary("waiting_input", { input_request: inputRequest }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);
    const knownTime = await screen.findByLabelText("已知时刻");
    await user.type(knownTime, "09:30");
    await user.type(screen.getByLabelText("大致时段"), "上午");
    await user.click(screen.getByRole("button", { name: /提交补充资料/ }));

    await waitFor(() => expect(knownTime).toHaveFocus());
    expect(screen.getAllByText("本组只能填写一项")).toHaveLength(2);
    expect(callsTo(fetchMock, "/input")).toHaveLength(0);
  });
});

describe("verification and follow-up", () => {
  it("submits the product-authoritative four-outcome verification with optional note", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(guestSession())
      .mockResolvedValueOnce(
        jsonResponse(
          {
            verification_id: "66666666-6666-4666-8666-666666666666",
            reading_version_id: VERSION_ID,
            outcome: "partial",
            note: "出生地点有出入",
            created_at: "2026-08-10T02:00:00Z",
          },
          201,
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<VerificationForm readingId={VERSION_ID} />);
    expect(screen.getAllByRole("radio")).toHaveLength(4);
    await user.click(screen.getByRole("radio", { name: "部分符合" }));
    await user.type(screen.getByLabelText(/补充说明/), "出生地点有出入");
    await user.click(screen.getByRole("button", { name: /提交核对结果/ }));

    expect(await screen.findByText(/已保存核对结果/)).toBeVisible();
    const verificationCall = callsTo(fetchMock, "/verification")[0];
    expect(verificationCall[0]).toBe(
      `/api/v1/readings/${VERSION_ID}/verification`,
    );
    expect(JSON.parse(String(verificationCall[1]?.body))).toEqual({
      outcome: "partial",
      note: "出生地点有出入",
    });
  });

  it("renders an existing verification from the result instead of asking again", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) {
        return jsonResponse(
          readingResult({
            verification: {
              verification_id: "66666666-6666-4666-8666-666666666666",
              reading_version_id: VERSION_ID,
              outcome: "partial",
              note: "部分时间不确定",
              created_at: "2026-08-10T02:00:00Z",
            },
          }),
        );
      }
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText(/已保存：部分符合/)).toBeVisible();
    expect(screen.getByText("部分时间不确定")).toBeVisible();
    expect(screen.queryByRole("button", { name: /提交核对结果/ })).not.toBeInTheDocument();
  });

  it("uses a native Enter-submit form, singular /follow-up, stable key, and new Reading Version id", async () => {
    let followUpAttempts = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return guestSession();
      if (path.endsWith("/result")) {
        return jsonResponse(readingResult({ document: readingDocument() }));
      }
      if (path.endsWith("/follow-up")) {
        followUpAttempts += 1;
        return followUpAttempts === 1
          ? problemResponse("追问暂时失败，请重试", 500)
          : jsonResponse(
              readingSummary("input_ready", {
                reading_version_id: "77777777-7777-4777-8777-777777777777",
                version: 2,
                prior_answer: acceptedCopy,
              }),
              201,
            );
      }
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);
    const query = await screen.findByLabelText("追问");
    expect(query.tagName).toBe("INPUT");
    await user.type(query, "换工作方向呢？{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(/重试/);
    await user.type(query, "{Enter}");

    await waitFor(() =>
      expect(routerPush).toHaveBeenCalledWith(
        "/app/readings/77777777-7777-4777-8777-777777777777",
      ),
    );
    const calls = callsTo(fetchMock, "/follow-up");
    expect(calls).toHaveLength(2);
    expect(calls[0][0]).toBe(`/api/v1/readings/${VERSION_ID}/follow-up`);
    expect(JSON.parse(String(calls[0][1]?.body))).toEqual({
      query: "换工作方向呢？",
    });
    expect(getHeader(calls[0][1], "Idempotency-Key")).toMatch(/^.{8,128}$/);
    expect(getHeader(calls[0][1], "Idempotency-Key")).toBe(
      getHeader(calls[1][1], "Idempotency-Key"),
    );
    expect(String(calls[0][1]?.body)).not.toMatch(/state_token|candidate|prompt/i);
  });
});

describe("Web interface regression guards", () => {
  it("keeps 48px inputs, mobile-safe input text, reduced motion, and bounded pre overflow", () => {
    const root = process.cwd();
    const globals = readFileSync(join(root, "src/app/globals.css"), "utf8");
    const sharedBase = readFileSync(join(root, "../ui/base.css"), "utf8");
    expect(globals).toContain('@import "../../../ui/base.css"');
    expect(sharedBase).toContain("@media (prefers-reduced-motion: reduce)");

    const formCssFiles = [
      "src/components/readings/need-input-form.module.css",
      "src/components/readings/follow-up-form.module.css",
      "src/components/readings/verification-form.module.css",
    ];
    for (const file of formCssFiles) {
      const css = readFileSync(join(root, file), "utf8");
      expect(css).toMatch(/min-height:\s*3rem/);
      expect(css).toMatch(/font-size:\s*(1rem|var\(--font-size-body\))/);
      expect(css).not.toMatch(/transition:\s*all/i);
      expect(css).not.toMatch(/animation-[a-z-]+:\s*[^;]*infinite/i);
      expect(css).not.toContain("999px");
    }

    const factCss = readFileSync(
      join(root, "src/components/readings/fact-panel.module.css"),
      "utf8",
    );
    expect(factCss).toMatch(/overflow-x:\s*auto/);
    expect(factCss).toMatch(/max-width:\s*100%/);

    const surfaceCss = readFileSync(
      join(root, "src/components/app-surface.module.css"),
      "utf8",
    );
    expect(surfaceCss).toMatch(
      /\.readingSection\[data-layout="full-width-reading-section"\]\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/s,
    );
  });

  it("does not disable paste or browser zoom in the touched surfaces", () => {
    const root = process.cwd();
    const sources = [
      "src/app/layout.tsx",
      "src/components/profile-form.tsx",
      "src/components/fortune-flow.tsx",
      "src/components/liuyao-form.tsx",
      "src/components/readings/need-input-form.tsx",
      "src/components/readings/follow-up-form.tsx",
      "src/components/readings/verification-form.tsx",
    ]
      .map((file) => readFileSync(join(root, file), "utf8"))
      .join("\n");

    expect(sources).not.toMatch(/onPaste/);
    expect(sources).not.toMatch(/user-scalable\s*=\s*no|maximum-scale\s*=\s*1/i);
  });
});

describe("bazi chart workspace", () => {
  it("consumes the typed time-layer entitlement sibling from GET /result", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) {
        return jsonResponse(
          readingResult({
            capability: baziCapabilityA,
            view_model: BAZI_EVIDENCE_RESULT_VIEW_MODEL,
            time_layer_entitlement: baziTimeLayerEntitlement,
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "bazi",
          object_id: "natal",
          dimension_ids: ["career"],
          horizon: { kind_id: "life", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const monthly = await screen.findByRole("tab", { name: /流月/ });
    expect(within(monthly).getByText(/2026-08/)).toBeVisible();
    await user.click(monthly);
    expect(screen.getByRole("table", { name: "流月总览" })).toBeVisible();
  });

  it("carries the typed Ziwei entitlement sibling through to readable month facts", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) {
        return jsonResponse(
          readingResult({
            capability: {
              capability_id: "ziwei",
              label: "紫微",
              tier: "B",
              source_system: "ziwei",
              runtime_active_rule_count: 2,
              judgment_rule_count: 0,
              source_status: "available",
            },
            view_model: ziweiMonthViewModel,
            time_layer_entitlement: ziweiTimeLayerEntitlement,
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "ziwei",
          product_id: "ziwei",
          object_id: "natal",
          dimension_ids: [],
          horizon: { kind_id: "life", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const timeLayerLocator = await screen.findByRole("navigation", {
      name: "时间层定位",
    });
    const monthly = within(timeLayerLocator).getByRole("button", {
      name: /流月/,
    });
    const controlledPanelId = monthly.getAttribute("aria-controls");
    expect(controlledPanelId).toBeTruthy();
    expect(document.getElementById(controlledPanelId!)).toBeInTheDocument();
    await user.click(monthly);
    expect(monthly).toHaveAttribute("aria-current", "true");
    expect(document.getElementById(controlledPanelId!)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "流月盘面事实" })).toHaveTextContent(
      "2026-08",
    );
  });

  it("presents a Bazi preview as a Chinese chart instead of internal metadata or fake interpretation", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) {
        return jsonResponse(
          readingResult({
            accepted_copy: "这是合同测试候选稿，不是正式命理解读。",
            capability: baziCapabilityA,
            fact_panel: {
              ...factPanel(),
              question: "请预览我的本命格局。",
              facts: [
                {
                  ref: "fact:branch-relations",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:branch_relations",
                  value: null,
                  display_text:
                    'branch_relations: [{"branches":["辰","戌"],"positions":["year","month"],"type":"六冲"}]',
                },
              ],
            },
            view_model: {
              schema_version: "bazi-chart/v1",
              subject_ref: "profile-version:secret-profile-id",
              pillars: [
                { position: "year", stem: "庚", branch: "辰" },
                { position: "month", stem: "丙", branch: "戌" },
                { position: "day", stem: "己", branch: "酉" },
                { position: "hour", stem: "丁", branch: "卯" },
              ],
              element_balance: [],
              time_layers: [],
              core_facts: null,
            },
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "bazi",
          product_id: "bazi",
          object_id: "natal",
          dimension_ids: ["career"],
          horizon: { kind_id: "life", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const view = render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findAllByRole("heading", { name: "八字命盘" })).toHaveLength(2);
    const workspaceSection = screen.getByRole("heading", { name: "排盘结果" }).closest("section");
    expect(workspaceSection).toHaveAttribute("data-layout", "full-width-reading-section");
    expect(screen.getByRole("heading", { name: "阅读说明" }).closest("section"))
      .toHaveAttribute("data-layout", "full-width-reading-section");
    expect(screen.getByText(/免费排盘预览/)).toBeVisible();
    expect(screen.getByRole("heading", { name: "专业深读已锁定" })).toBeVisible();
    const visible = document.body.textContent ?? "";
    expect(visible).not.toContain("这是合同测试候选稿");
    expect(visible).not.toMatch(/branch relations|branch_relations|positions|year|month/i);
    expect(visible).not.toContain("命理档案");
    expect(visible).not.toContain("服务端目标日期");
    expect(visible).not.toContain("长期范围");
    expect(screen.queryByRole("heading", { name: "判断" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "事实" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "依据与边界" })).not.toBeInTheDocument();

    view.rerender(<ReadingResult baziDeepFulfilled readingId={VERSION_ID} />);
    expect(screen.getByText(/专业深读已交付；免费盘面继续保留/)).toBeVisible();
    expect(screen.queryByRole("heading", { name: "专业深读已锁定" }))
      .not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "了解专业版" })).not.toBeInTheDocument();
  });

  it("fails closed when the Bazi Runtime capability projection is missing", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            view_model: { schema_version: "bazi-chart/v1" },
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "bazi",
          object_id: "natal",
          dimension_ids: ["career"],
          horizon: { kind_id: "life", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(
      await screen.findByText("当前能力仍在适配中，暂不可用；未加载未确认的盘面或断法。"),
    ).toBeVisible();
    expect(screen.queryByRole("region", { name: "排盘工作台" })).not.toBeInTheDocument();
    expect(screen.queryByText("全局强弱证据（未裁定）")).not.toBeInTheDocument();
  });

  it("renders a left chart / right analysis layout for bazi readings", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            capability: baziCapabilityA,
            fact_panel: {
              ...factPanel(),
              question: "看一下这个八字",
              facts: [
                {
                  ref: "fact:pillars",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:natal_pillars",
                  value: null,
                  display_text:
                    'natal_pillars: {"day":"己酉","hour":"丁卯","month":"丙戌","year":"庚辰"}',
                },
                {
                  ref: "fact:day-master",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:day_master",
                  value: null,
                  display_text:
                    'day_master: {"element":"土","polarity":"阴","stem":"己"}',
                },
                {
                  ref: "fact:profile-version/input/location",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:location",
                  value: "杭州市西湖区",
                  display_text: "location: 杭州市西湖区",
                },
                {
                  ref: "fact:profile-version/input/timezone",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:timezone",
                  value: "Asia/Shanghai",
                  display_text: "timezone: Asia/Shanghai",
                },
                {
                  ref: "fact:profile-version/input/gender",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:gender",
                  value: "female",
                  display_text: "gender: female",
                },
                {
                  ref: "fact:luck",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:active_luck_cycle",
                  value: null,
                  display_text: "active_luck_cycle: 戊子",
                },
                {
                  ref: "fact:opaque-1",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:career-structure",
                  value: { state_token: "opaque-runtime-token" },
                  display_text: "当前结构更支持持续积累。",
                },
              ],
              request_view: {
                subject_refs: ["profile-version:secret-profile-id"],
                capability_ids: ["bazi"],
                object_id: "natal",
                dimension_ids: ["career"],
                horizon: {
                  kind_id: "life",
                  start: null,
                  end: null,
                },
              },
            },
            view_model: {
              schema_version: "bazi-chart/v1",
              subject_ref: "profile-version:secret-profile-id",
              pillars: [
                { position: "year", stem: "庚", branch: "辰" },
                { position: "month", stem: "丙", branch: "戌" },
                { position: "day", stem: "己", branch: "酉" },
                { position: "hour", stem: "丁", branch: "卯" },
              ],
              element_balance: [],
              time_layers: [],
              core_facts: {
                day_master: { stem: "己", element: "earth", polarity: "阴" },
                hidden_stems: null,
                ten_gods: null,
                nayin: null,
                twelve_growth_stages: [
                  {
                    position: "year",
                    stem: "庚",
                    branch: "辰",
                    stage: "养",
                    stage_index: 12,
                    direction: "reverse",
                    source_dependency_id: "bazi.chart.twelve-growth-stages-v1",
                    boundary: "十二长生位置事实；不能单独推出旺衰、格局、用神或事件结论",
                  },
                  {
                    position: "month",
                    stem: "丙",
                    branch: "戌",
                    stage: "冠带",
                    stage_index: 3,
                    direction: "forward",
                    source_dependency_id: "bazi.chart.twelve-growth-stages-v1",
                    boundary: "十二长生位置事实；不能单独推出旺衰、格局、用神或事件结论",
                  },
                ],
                xunkong: {
                  day_pillar: "己酉",
                  xun: "甲申",
                  branches: ["午", "未"],
                  source_dependency_id: "bazi.chart.xunkong-sexagenary-v1",
                  boundary: "按日柱所属旬计算旬空事实；不能单独推出吉凶、六亲或事件结论",
                },
                san_yuan: {
                  tai_yuan: "丁丑",
                  ming_gong: "庚卯",
                  shen_gong: "戊子",
                  source: "lunar-typescript-auxiliary",
                  source_dependency_id: "bazi.chart.san-yuan-lunar-typescript-v1",
                  boundary: "胎元、命宫、身宫位置事实；不能单独推出格局、旺衰、吉凶或事件结论",
                },
                month_command: null,
                seasonal_profile: null,
                tiaohou_markers: null,
                element_inventory: null,
                interpretive_candidates: {
                  strength: {
                    status: "evidence_only",
                    hard_verdict: null,
                    day_element: "earth",
                    month_command_element: "earth",
                    seasonal_state: "旺",
                    seasonal_state_source_rule_id: "bazi/sanming-tonghui#R-02-04",
                    same_element_occurrences: 5,
                    resource_element: "fire",
                    resource_occurrences: 3,
                    all_element_occurrences: [
                      { element: "wood", value: 0 },
                      { element: "fire", value: 3 },
                      { element: "earth", value: 5 },
                      { element: "metal", value: 1 },
                      { element: "water", value: 0 },
                    ],
                    month_order_adjudication: {
                      status: "adjudicated_month_order_state",
                      decision_scope: "bazi_month_order_seasonal_state",
                      day_master_element: "earth",
                      month_command_element: "earth",
                      seasonal_state: "旺",
                      whole_chart_strength_verdict: null,
                      useful_god_verdict: null,
                      source_ref: {
                        pack: "bazi/sanming-tonghui",
                        rule_id: "R-02-04",
                        source_anchor: "references/books/bazi/sanming-tonghui/rules.md#R-02-04",
                        verification_status: "verified",
                        binding_digest: "77b387e17e65b50c7cbcdba3cc8ef5b170499c6d5c07461856b710d5aa50759e",
                      },
                      unresolved_checks: ["全局根气、生扶、克泄与合化"],
                    },
                    boundary: "只展示五行出现次数，不等于旺衰定论。",
                  },
                  structure: {
                    status: "candidate_only",
                    hard_verdict: null,
                    month_main_qi: "戊",
                    month_main_qi_ten_god: "劫财",
                    main_qi_visible: false,
                    visible_positions: ["month"],
                    boundary: "只展示月令主气与透干候选，不完成格局裁定。",
                  },
                  following_and_transformation: {
                    status: "requires_classical_adjudication",
                    hard_verdict: null,
                    stem_combination_candidates: [],
                    branch_formation_candidates: [],
                    boundary: "合化、从格仍需经典裁决。",
                  },
                  salience_signals: [],
                },
                branch_relations: null,
                shensha_auxiliary: null,
                luck_cycles: null,
              },
            },
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "bazi",
          object_id: "natal",
          dimension_ids: ["career"],
          horizon: { kind_id: "life", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(
      await screen.findByRole("region", { name: "排盘工作台" }),
    ).toBeVisible();
    expect(screen.getByRole("article", { name: "解读正文" })).toBeVisible();
    expect(screen.getAllByText("八字命盘").length).toBeGreaterThan(0);
    expect(screen.getAllByText("年柱")[0]).toBeVisible();
    expect(screen.getAllByText("庚辰").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/日主.*己/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/当前大运|大运 戊子|戊子/).length).toBeGreaterThan(0);
    expect(screen.queryByText("全局结论：未裁定")).not.toBeInTheDocument();
    expect(screen.getByText("月令状态裁定")).toBeVisible();
    expect(screen.getByText(/月令状态 旺/)).toBeVisible();
    expect(screen.getByText(/同类 5 项；生扶 火 3 项/)).toBeVisible();
    expect(screen.getByText(/不等于旺衰定论/)).toBeVisible();
    expect(document.body.textContent?.match(/未裁定/gu)).toBeNull();
    expect(screen.getByText("十二长生")).toBeVisible();
    expect(screen.getByText(/年柱 庚辰：养；月柱 丙戌：冠带/)).toBeVisible();
    expect(screen.getByText("旬空")).toBeVisible();
    expect(screen.getByText(/己酉 属 甲申 旬：午、未/)).toBeVisible();
    expect(screen.queryByText("当前结构更支持持续积累。")).not.toBeInTheDocument();
    expect(screen.queryByText("杭州市西湖区")).not.toBeInTheDocument();
    expect(screen.queryByText("Asia/Shanghai")).not.toBeInTheDocument();
    expect(screen.queryByText("女")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "排盘结果" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "阅读说明" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "判断" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "事实" })).not.toBeInTheDocument();

    const year = screen.getByRole("button", { name: /年柱/ });
    const month = screen.getByRole("button", { name: /月柱/ });
    expect(year).toHaveAttribute("tabindex", "0");
    expect(month).toHaveAttribute("tabindex", "-1");

    year.focus();
    await user.keyboard("{ArrowRight}");
    expect(month).toHaveFocus();
    expect(month).toHaveAttribute("tabindex", "0");
    expect(year).toHaveAttribute("tabindex", "-1");
    expect(month).toHaveAttribute("aria-expanded", "false");

    await user.keyboard("{Enter}");
    expect(month).toHaveAttribute("aria-expanded", "true");
    expect(month).toHaveAttribute("aria-controls");
    expect(screen.getByRole("region", { name: "聚焦详情" })).toHaveAttribute(
      "id",
      month.getAttribute("aria-controls"),
    );
  });

  it("opens focus detail from a pillar click using server-backed facts only", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            capability: baziCapabilityA,
            fact_panel: {
              ...factPanel(),
              question: "看一下这个八字",
              facts: [
                {
                  ref: "fact:pillars",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:natal_pillars",
                  value: null,
                  display_text:
                    'natal_pillars: {"day":"己酉","hour":"丁卯","month":"丙戌","year":"庚辰"}',
                },
                {
                  ref: "fact:timezone",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:timezone",
                  value: null,
                  display_text: "timezone: Asia/Shanghai",
                },
                {
                  ref: "fact:time-basis",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:time_basis",
                  value: null,
                  display_text: "time_basis: civil",
                },
              ],
              request_view: {
                subject_refs: ["profile-version:secret-profile-id"],
                capability_ids: ["bazi"],
                object_id: "natal",
                dimension_ids: ["career"],
                horizon: {
                  kind_id: "life",
                  start: null,
                  end: null,
                },
              },
            },
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "bazi",
          object_id: "natal",
          dimension_ids: ["career"],
          horizon: { kind_id: "life", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("heading", { name: "排盘结果" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /年柱/ }));

    const drawer = screen.getByRole("region", { name: "聚焦详情" });
    expect(within(drawer).getByText(/年柱/)).toBeVisible();
    expect(within(drawer).getByText("Asia/Shanghai")).toBeVisible();
    expect(within(drawer).getByText(/民用时|civil/)).toBeVisible();
    expect(within(drawer).getByText(/前端不进行本地排盘/)).toBeVisible();
    expect(screen.queryByText(acceptedCopyQuery)).not.toBeInTheDocument();
  });

  it("keeps the chart workspace before its reading note in document order", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        return jsonResponse(
          readingResult({
            capability: baziCapabilityA,
            fact_panel: {
              ...factPanel(),
              question: "看一下这个八字",
              facts: [
                {
                  ref: "fact:pillars",
                  subject_ref: "profile-version:secret-profile-id",
                  kind_id: "fact:natal_pillars",
                  value: null,
                  display_text:
                    'natal_pillars: {"day":"己酉","hour":"丁卯","month":"丙戌","year":"庚辰"}',
                },
              ],
              request_view: {
                subject_refs: ["profile-version:secret-profile-id"],
                capability_ids: ["bazi"],
                object_id: "natal",
                dimension_ids: ["career"],
                horizon: {
                  kind_id: "life",
                  start: null,
                  end: null,
                },
              },
            },
          }),
        );
      }
      return jsonResponse(
        readingSummary("accepted", {
          capability_id: "bazi",
          object_id: "natal",
          dimension_ids: ["career"],
          horizon: { kind_id: "life", start: null, end: null },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const workspaceNode = await screen.findByLabelText("排盘工作台");
    const note = screen.getByRole("heading", { name: "阅读说明" });
    expect(
      workspaceNode.compareDocumentPosition(note) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.queryByText(acceptedCopyQuery)).not.toBeInTheDocument();
  });

});
