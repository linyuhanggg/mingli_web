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

function summary(capabilityId: "ziwei" | "qizheng") {
  return {
    reading_version_id: VERSION_ID,
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    capability_id: capabilityId,
    product_id: capabilityId,
    version: 1,
    status: "accepted",
    object_id: "natal",
    dimension_ids: ["overview"],
    horizon: { kind_id: "day", start: "2026-08-10", end: "2026-08-10" },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-10T01:00:00Z",
  };
}

function capability(capabilityId: "ziwei" | "qizheng") {
  return {
    capability_id: capabilityId,
    label: capabilityId === "ziwei" ? "紫微" : "七政",
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

function ziweiView() {
  return {
    schema_version: "ziwei-chart/v1",
    subject_ref: "profile-version:fixture",
    life_palace_id: "0",
    body_palace_id: "1",
    palaces: Array.from({ length: 12 }, (_, index) => ({
      palace_id: String(index),
      label: index === 0 ? "命宫" : `宫${index}`,
      heavenly_stem: "甲",
      earthly_branch: "子",
      major_stars: index === 0 ? ["紫微"] : [],
      minor_stars: [],
      adjective_stars: [],
    })),
    time_layers: [],
    core_facts: {
      five_elements_class: "水二局",
      source_conditioned_patterns: [],
      transformations: [],
      major_limits: [],
    },
  };
}

function qizhengView() {
  return {
    schema_version: "qizheng-chart/v1",
    subject_ref: "profile-version:fixture",
    planets: [{ planet_id: "太阳", sign_id: "金牛", house_id: "1", longitude: 39.3 }],
    houses: Array.from({ length: 12 }, (_, index) => ({
      house_id: String(index + 1),
      sign_id: "白羊",
      cusp_longitude: index * 30,
    })),
    aspects: [],
    time_layers: [],
    core_facts: {
      source_conditioned_patterns: [],
      major_limits: [],
      transformations: [],
    },
  };
}

function stubReady(capabilityId: "ziwei" | "qizheng", viewModel: unknown, evidence: unknown[] = []) {
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
          question: "本命盘",
          vocabulary: [],
          facts: [],
          evidence,
          findings: [],
          claim_scopes: [],
          limits: [],
        },
        view_model: viewModel,
        capability: capability(capabilityId),
        verification: null,
        document: null,
        input_request: null,
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

describe("ziwei + qizheng result shell", () => {
  it("puts ziwei chart facts and a verified citation before notes, without construction copy", async () => {
    stubReady("ziwei", ziweiView(), [verifiedEvidence()]);
    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("heading", { level: 1, name: "紫微命盘" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "排盘结果" })).toBeVisible();
    expect(screen.getByText("水二局")).toBeVisible();
    expect(screen.getByText("先定其基，再观其用。")).toBeVisible();
    expect(screen.getByRole("heading", { name: "阅读说明" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "判断" })).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText(/Runtime|Provider|适配器/)).not.toBeInTheDocument();
  });

  it("puts qizheng chart facts first and does not invent aspects", async () => {
    stubReady("qizheng", qizhengView());
    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("heading", { level: 1, name: "七政命盘" })).toBeVisible();
    expect(screen.getByText("太阳")).toBeVisible();
    expect(screen.getByText("金牛")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "判断" })).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText(/Runtime|Provider|适配器/)).not.toBeInTheDocument();
    expect(screen.queryByRole("table", { name: /相位/ })).not.toBeInTheDocument();
  });

  it("stays empty when the server has no natal view_model", async () => {
    stubReady("ziwei", null);
    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("status", { name: "还没有可展示的盘面" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "判断" })).not.toBeInTheDocument();
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
    const ziwei = natal.slice(natal.indexOf("function ZiweiChart"), natal.indexOf("function LiuyaoChart"));
    expect(ziwei).not.toMatch(/Runtime|Provider|适配器/);
  });
});
