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

function summary(capabilityId: "qimen" | "daliuren") {
  return {
    reading_version_id: VERSION_ID,
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    capability_id: capabilityId,
    product_id: capabilityId,
    version: 1,
    status: "accepted",
    object_id: "concrete_event",
    dimension_ids: ["career"],
    horizon: { kind_id: "instant", start: null, end: null },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-10T01:00:00Z",
  };
}

function capability(capabilityId: "qimen" | "daliuren") {
  return {
    capability_id: capabilityId,
    label: capabilityId === "qimen" ? "奇门" : "大六壬",
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

function qimenView() {
  return {
    schema_version: "qimen-chart/v1",
    subject_ref: "qimen:fixture",
    question: "这次合作能否推进？",
    dun_type: "yang",
    ju_number: 3,
    palaces: Array.from({ length: 9 }, (_, index) => ({
      palace_id: String(index + 1),
      stem: "戊",
      heaven_stems: index === 0 ? ["乙", "戊"] : [],
      stars: index === 0 ? ["天辅", "天禽"] : [],
      star: index === 0 ? "天辅" : null,
      door: index === 0 ? "生门" : null,
      deity: index === 0 ? "九天" : null,
    })),
    chief: {
      star: "天辅",
      door: "生门",
      hidden_instrument: "戊",
      xun_palace: 1,
      hosted_xun_palace: 1,
      destination_palace: 1,
    },
    director: {
      door: "生门",
      xun_palace: 1,
      destination_palace: 1,
      hour_offset_in_xun: 0,
    },
    instruments_wonders: {
      six_instruments: ["戊"],
      three_wonders: ["乙"],
      earth_plate: [],
      heaven_plate: [],
      hidden_jia: { xun: "甲子", instrument: "戊" },
    },
    xunkong: { xun: "甲子", branches: ["戌", "亥"], palaces: [6, 7] },
    horse: { hour_branch: "子", branch: "寅", palace: 8 },
    named_patterns: [],
  };
}

function daliurenView() {
  return {
    schema_version: "daliuren-chart/v1",
    subject_ref: "liuren:fixture",
    question: "这件事何时可能出现回应？",
    lessons: [
      { lesson_id: "1", upper: "酉", lower: "庚" },
      { lesson_id: "2", upper: "戌", lower: "酉" },
      { lesson_id: "3", upper: "子", lower: "申" },
      { lesson_id: "4", upper: "丑", lower: "子" },
    ],
    transmissions: [
      { stage: "initial", branch: "酉", general: "朱雀" },
      { stage: "middle", branch: "戌", general: "六合" },
      { stage: "final", branch: "亥", general: "勾陈" },
    ],
    core_facts: null,
  };
}

function stubReady(
  capabilityId: "qimen" | "daliuren",
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
          question: capabilityId === "qimen" ? "这次合作能否推进？" : "这件事何时可能出现回应？",
          vocabulary: [],
          facts: [],
          evidence: [verifiedEvidence()],
          findings: [],
          claim_scopes: [],
          limits: [],
        },
        view_model: capabilityId === "qimen" ? qimenView() : daliurenView(),
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

describe("qimen + daliuren result shell", () => {
  it("puts qimen plate and a verified citation before notes, without construction copy", async () => {
    stubReady("qimen");
    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("heading", { level: 1, name: "奇门" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "排盘结果" })).toBeVisible();
    expect(screen.getByText("九宫盘面")).toBeVisible();
    expect(screen.getByText("阳遁")).toBeVisible();
    expect(screen.getByText("天辅、天禽")).toBeVisible();
    expect(screen.getAllByText("先定其基，再观其用。").length).toBeGreaterThan(0);
    const plate = screen.getByText("九宫盘面");
    expect(
      plate.compareDocumentPosition(screen.getByRole("heading", { name: "阅读说明" })) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText(/Runtime|Provider|适配器/)).not.toBeInTheDocument();
  });

  it("puts daliuren lessons first and does not invent a plate", async () => {
    stubReady("daliuren");
    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("heading", { level: 1, name: "大六壬" })).toBeVisible();
    expect(screen.getByText("四课")).toBeVisible();
    expect(screen.getByText("三传")).toBeVisible();
    expect(screen.getByText("朱雀")).toBeVisible();
    expect(
      screen.getByText("四课").compareDocumentPosition(screen.getByRole("heading", { name: "阅读说明" })) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText(/Runtime|Provider|适配器/)).not.toBeInTheDocument();
  });

  it("stays empty when the server has no qimen plate or copy", async () => {
    stubReady("qimen", {
      fact_panel: {
        question: "这次合作能否推进？",
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
    expect(screen.queryByText("九宫盘面")).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
  });

  it("locks the result header to --font-size-page", () => {
    const css = readFileSync(resolve(process.cwd(), "src/components/app-surface.module.css"), "utf8");
    expect(css).toMatch(/\.readingHeader h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
  });

  it("does not put construction chrome on the production files", () => {
    for (const file of [
      "src/app/qimen/page.tsx",
      "src/app/daliuren/page.tsx",
      "src/components/readings/reading-result.tsx",
      "src/components/readings/runtime-chart.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/§10|§6\.2|SecondarySurfaceFrame|AppPageHeader/);
    }
    expect(readFileSync(resolve(process.cwd(), "src/app/qimen/page.tsx"), "utf8")).not.toMatch(
      /工作台|待接入|Runtime|Provider|适配器/,
    );
    expect(readFileSync(resolve(process.cwd(), "src/app/daliuren/page.tsx"), "utf8")).not.toMatch(
      /工作台|待接入|Runtime|Provider|适配器/,
    );
    const natal = readFileSync(
      resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"),
      "utf8",
    );
    const qimen = natal.slice(natal.indexOf("function QimenChart"), natal.indexOf("function DaliurenChart"));
    expect(qimen).not.toMatch(/Runtime|Provider|适配器/);
    const daliuren = natal.slice(
      natal.indexOf("function DaliurenChart"),
      natal.indexOf("function PhysiognomyChart"),
    );
    expect(daliuren).not.toMatch(/Runtime|Provider|适配器/);
  });
});
