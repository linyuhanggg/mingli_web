
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReadingResult } from "@/components/readings/reading-result";
import { WorkbenchShell } from "@/components/workbench/workbench-shell";
import { resetApiCache } from "@/lib/api";
import { getProductDefinition } from "@/products/catalog";

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

describe("liuyao workbench six states", () => {
  it("keeps fake workbench promises marked 待接入 and clickable", () => {
    render(
      <WorkbenchShell
        onBack={() => undefined}
        product={getProductDefinition("liuyao")}
      />,
    );

    expect(screen.getByRole("heading", { name: "六爻工作台" })).toBeVisible();
    expect(screen.getByText("待接入 ·", { exact: false })).toBeVisible();
    expect(screen.getByRole("button", { name: /返回确认/ })).toBeEnabled();
    expect(screen.getByRole("link", { name: "查看术数总览" })).toHaveAttribute("href", "/arts");
    expect(screen.getByRole("button", { name: "导出待接入" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /时间层待接入/ })).toBeDisabled();
  });

  it("reaches honest clickable workbench states from the production surfaceState", () => {
    const product = getProductDefinition("liuyao");
    const { rerender } = render(
      <WorkbenchShell onBack={() => undefined} product={product} surfaceState="loading" />,
    );
    expect(screen.getByRole("status", { name: "正在载入工作台" })).toHaveAttribute(
      "data-state",
      "loading",
    );

    rerender(<WorkbenchShell onBack={() => undefined} product={product} surfaceState="empty" />);
    expect(screen.getByRole("status", { name: "还没有可展示的盘面" })).toHaveAttribute(
      "data-state",
      "empty",
    );
    expect(screen.getByRole("button", { name: "返回录入" })).toBeEnabled();

    rerender(<WorkbenchShell onBack={() => undefined} product={product} surfaceState="error" />);
    expect(screen.getByRole("alert", { name: "读取失败，请重试" })).toHaveAttribute(
      "data-state",
      "error",
    );
    expect(screen.getByRole("button", { name: "返回录入" })).toBeEnabled();

    rerender(<WorkbenchShell onBack={() => undefined} product={product} surfaceState="processing" />);
    expect(screen.getByRole("status", { name: "盘面处理中" })).toHaveAttribute(
      "data-state",
      "processing",
    );

    rerender(<WorkbenchShell onBack={() => undefined} product={product} surfaceState="unavailable" />);
    expect(
      screen.getByRole("status", { name: "结果服务暂时不可用，不会展示未确认内容" }),
    ).toHaveAttribute("data-state", "unavailable");
    expect(screen.getByRole("link", { name: "查看术数总览" })).toHaveAttribute("href", "/arts");

    rerender(<WorkbenchShell onBack={() => undefined} product={product} surfaceState="unauthorized" />);
    expect(screen.getByRole("status", { name: "需要登录才能看这份结果" })).toHaveAttribute(
      "data-state",
      "unauthorized",
    );
    expect(screen.getByRole("link", { name: "登录后继续" })).toHaveAttribute("href", "/auth/login");
  });
});

describe("liuyao result six states", () => {

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
      return jsonResponse(readingSummary("liuyao", "liuyao"));
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
        return jsonResponse(emptyResult("liuyao", "六爻"));
      }
      return jsonResponse(readingSummary("liuyao", "liuyao"));
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
        return jsonResponse(emptyResult("liuyao", "六爻", "unavailable"));
      }
      return jsonResponse(readingSummary("liuyao", "liuyao"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const panel = await screen.findByRole("status", {
      name: "结果服务暂时不可用，不会展示未确认内容",
    });
    expect(panel).toHaveAttribute("data-state", "unavailable");
  });

  it("does not treat accepted copy as a Liuyao plate without a typed ViewModel", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) {
        return jsonResponse(acceptedResult("liuyao", "六爻"));
      }
      return jsonResponse(readingSummary("liuyao", "liuyao"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("status", { name: "还没有可展示的盘面" })).toBeVisible();
    expect(screen.queryByRole("region", { name: "判断" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("status", { name: "结果服务暂时不可用，不会展示未确认内容" }),
    ).not.toBeInTheDocument();
  });

});
