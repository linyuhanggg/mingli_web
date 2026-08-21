import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReadingResult } from "@/components/readings/reading-result";
import { resetApiCache } from "@/lib/api";

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
const ACCEPTED_COPY = "先给结论。再说明依据，原字原序。";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function problemResponse(title: string, status: number) {
  return jsonResponse({ title, status, request_id: "request-1" }, status);
}

function capability(id: string, label: string, sourceStatus: "available" | "unavailable" = "available") {
  return {
    capability_id: id,
    label,
    tier: "B" as const,
    source_system: id,
    runtime_active_rule_count: 0,
    judgment_rule_count: 0,
    source_status: sourceStatus,
  };
}

function readingSummary(productId: string, capabilityId: string) {
  return {
    reading_version_id: VERSION_ID,
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    capability_id: capabilityId,
    product_id: productId,
    version: 1,
    status: "accepted",
    object_id: "natal",
    dimension_ids: [],
    horizon: { kind_id: "life", start: null, end: null },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-10T01:00:00Z",
  };
}

function emptyResult(capabilityId: string, label: string, sourceStatus: "available" | "unavailable" = "available") {
  return {
    reading_version_id: VERSION_ID,
    status: "accepted",
    accepted_copy: null,
    view_model: null,
    document: null,
    fact_panel: null,
    verification: null,
    input_request: null,
    capability: capability(capabilityId, label, sourceStatus),
  };
}

function acceptedResult(capabilityId: string, label: string) {
  return {
    reading_version_id: VERSION_ID,
    status: "accepted",
    accepted_copy: ACCEPTED_COPY,
    view_model: null,
    document: null,
    fact_panel: null,
    verification: null,
    input_request: null,
    capability: capability(capabilityId, label),
  };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  routerPush.mockReset();
});

beforeEach(() => {
  resetApiCache();
});

describe("fortune result six states", () => {

  it("maps a 401 poll error to unauthorized", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(problemResponse("登录状态已失效", 401)),
    );

    render(<ReadingResult readingId={VERSION_ID} />);

    const panel = await screen.findByRole("status", { name: "需要登录才能看这份结果" });
    expect(panel).toHaveAttribute("data-state", "unauthorized");
    expect(screen.getByRole("link", { name: "登录后继续" })).toHaveAttribute("href", "/auth/login");
  });

  it("maps a 404 result fetch to empty", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) {
        return problemResponse("Reading not found", 404);
      }
      return jsonResponse(readingSummary("fortune", "fortune"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const panel = await screen.findByRole("status", { name: "还没有可展示的盘面" });
    expect(panel).toHaveAttribute("data-state", "empty");
    expect(screen.getByRole("button", { name: "重试" })).toBeEnabled();
  });

  it("maps GET /result 200 empty body to unavailable", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) {
        return jsonResponse(emptyResult("fortune", "运势"));
      }
      return jsonResponse(readingSummary("fortune", "fortune"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const panel = await screen.findByRole("status", {
      name: "结果服务暂时不可用，不会展示未确认内容",
    });
    expect(panel).toHaveAttribute("data-state", "unavailable");
    expect(screen.getByRole("button", { name: "重试" })).toBeEnabled();
  });

  it("maps GET /result 200 source_status=unavailable to unavailable", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) {
        return jsonResponse(emptyResult("fortune", "运势", "unavailable"));
      }
      return jsonResponse(readingSummary("fortune", "fortune"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const panel = await screen.findByRole("status", {
      name: "结果服务暂时不可用，不会展示未确认内容",
    });
    expect(panel).toHaveAttribute("data-state", "unavailable");
  });

  it("keeps an accepted_copy result page instead of empty or unavailable", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) {
        return jsonResponse(acceptedResult("fortune", "运势"));
      }
      return jsonResponse(readingSummary("fortune", "fortune"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("region", { name: "判断" })).toHaveTextContent(ACCEPTED_COPY);
    expect(screen.queryByRole("status", { name: "还没有可展示的盘面" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("status", { name: "结果服务暂时不可用，不会展示未确认内容" }),
    ).not.toBeInTheDocument();
  });

});
