import { readFileSync } from "node:fs";
import { join } from "node:path";

import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockPollReading = vi.hoisted(() => vi.fn());
const mockStartBaziDeepReading = vi.hoisted(() => vi.fn());
const mockCreateBaziDeepCheckout = vi.hoisted(() => vi.fn());
const mockGetBaziDeepCheckout = vi.hoisted(() => vi.fn());
const mockBindReadingFulfillment = vi.hoisted(() => vi.fn());
const mockRecordConsent = vi.hoisted(() => vi.fn());
const mockReplace = vi.hoisted(() => vi.fn());
const mockStartPreviewReading = vi.hoisted(() => vi.fn());
const mockCreateProfileDraft = vi.hoisted(() => vi.fn());
const mockConfirmProfileDraft = vi.hoisted(() => vi.fn());
const mockListProfiles = vi.hoisted(() => vi.fn());
const mockSearch = vi.hoisted(() => ({ value: new URLSearchParams() }));
const mockSessionStatus = vi.hoisted(() => ({ value: "signedOut" as "checking" | "signedOut" | "signedIn" }));
const readingSummaryCallbacks = vi.hoisted(() => new Map<string, (summary: unknown) => void>());

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  pollReading: mockPollReading,
  startBaziDeepReading: mockStartBaziDeepReading,
  createBaziDeepCheckout: mockCreateBaziDeepCheckout,
  getBaziDeepCheckout: mockGetBaziDeepCheckout,
  bindReadingFulfillment: mockBindReadingFulfillment,
  recordConsent: mockRecordConsent,
  startPreviewReading: mockStartPreviewReading,
  createProfileDraft: mockCreateProfileDraft,
  confirmProfileDraft: mockConfirmProfileDraft,
  listProfiles: mockListProfiles,
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn(), prefetch: vi.fn(), refresh: vi.fn(), back: vi.fn(), forward: vi.fn() }),
  usePathname: () => "/bazi",
  useSearchParams: () => mockSearch.value,
}));

vi.mock("@/components/account-session-context", () => ({
  useOptionalAccountSession: () => ({ state: { status: mockSessionStatus.value } }),
}));

vi.mock("@/components/readings/reading-result", () => ({
  ReadingResult: ({
    readingId,
    baziDeepFulfilled = false,
    density = "default",
    onPollError,
    onSummary,
  }: {
    readingId: string;
    baziDeepFulfilled?: boolean;
    density?: "default" | "chart-first";
    onPollError?: (error: unknown) => void;
    onSummary?: (summary: typeof previewSummary) => void;
  }) => {
    useEffect(() => {
      if (onSummary) readingSummaryCallbacks.set(readingId, onSummary as (summary: unknown) => void);
      return () => {
        readingSummaryCallbacks.delete(readingId);
      };
    }, [onSummary, readingId]);

    useEffect(() => {
      let active = true;
      let timer: ReturnType<typeof setTimeout> | null = null;

      async function run() {
        try {
          const summary = await mockPollReading(readingId);
          if (!active) return;
          onSummary?.(summary);
          const record = summary as Record<string, unknown>;
          const terminal = ["accepted", "runtime_unknown", "terminal_stopped"]
            .includes(String(record.status));
          if (!terminal && record.poll_required !== false) {
            timer = setTimeout(run, 2000);
          }
        } catch (error) {
          if (active) onPollError?.(error);
        }
      }

      void run();
      return () => {
        active = false;
        if (timer) clearTimeout(timer);
      };
    }, [onPollError, onSummary, readingId]);

    return (
      <div
        data-bazi-deep-fulfilled={String(baziDeepFulfilled)}
        data-density={density}
        data-testid={`reading-result-${readingId}`}
      >
        服务端结果 renderer
        {density === "chart-first" ? <button type="button">盘面操作</button> : null}
      </div>
    );
  },
}));

import {
  ProductTaskExperience,
  persistBaziPreviewRecoveryState,
  readBaziPreviewRecoveryState,
} from "@/components/task/product-task-experience";
import {
  BaziDeepTaskFlow,
  baziPreviewRestoreHref,
  isPreviewChartReady,
  readBaziPreviewReadingId,
  stateForDeliveryState,
  stateForReadingStatus,
} from "@/components/task/bazi-deep-task-flow";
import { PRODUCT_CATALOG } from "@/products/catalog";

const previewSummary = {
  reading_version_id: "preview-1",
  reading_root_id: "root-1",
  profile_version_id: "profile-1",
  capability_id: "bazi",
  product_id: "bazi",
  runtime_capability_ids: ["bazi"],
  version: 1,
  status: "accepted" as const,
  object_id: "natal",
  dimension_ids: ["career"],
  horizon: { kind_id: "life", start: null, end: null },
  prior_answer: null,
  input_request: null,
  created_at: "2026-08-18T00:00:00Z",
};

const deepSummary = {
  ...previewSummary,
  reading_version_id: "deep-1",
  product_id: "bazi-deep",
  status: "accepted" as const,
  delivery_state: "delivered" as const,
};

const checkoutPending = {
  order: {
    order_id: "order-1",
    reading_version_id: "deep-1",
    product_id: "bazi-deep" as const,
    product_version: "bazi-deep-v1",
    amount_minor: 1990,
    currency: "CNY",
    status: "payment_pending",
    created_at: "2026-08-18T00:00:00Z",
    paid_at: null,
  },
  attempt: {
    attempt_id: "attempt-1",
    channel: "fake",
    status: "pending",
    created_at: "2026-08-18T00:00:00Z",
  },
  gateway_status: "pending" as const,
  redirect_url: "https://pay.example.invalid/checkout/order-1",
  created: true,
};

const checkoutConfirmed = {
  ...checkoutPending,
  gateway_status: "succeeded" as const,
  payment_id: "confirmed-payment-from-server",
};

beforeEach(() => {
  window.sessionStorage.clear();
  readingSummaryCallbacks.clear();
  mockSessionStatus.value = "signedOut";
  mockSearch.value = new URLSearchParams();
  mockPollReading.mockReset();
  mockStartBaziDeepReading.mockReset();
  mockCreateBaziDeepCheckout.mockReset();
  mockGetBaziDeepCheckout.mockReset();
  mockBindReadingFulfillment.mockReset();
  mockRecordConsent.mockReset();
  mockRecordConsent.mockResolvedValue({});
  mockReplace.mockReset();
  mockStartPreviewReading.mockReset();
  mockCreateProfileDraft.mockReset().mockResolvedValue({ draft_id: "draft-1", status: "draft" });
  mockConfirmProfileDraft.mockReset().mockResolvedValue({
    profile_version_id: "profile-version-1",
    profile_id: "profile-1",
    subject_ref: "本人",
    version: 1,
    created_at: "2026-08-14T00:00:00Z",
  });
  mockListProfiles.mockReset().mockResolvedValue({ profiles: [] });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Bazi deep task state contract", () => {
  it("maps only public ReadingVersion statuses and keeps job states explicit", () => {
    expect(stateForReadingStatus("accepted", "preview")).toBe("free");
    expect(stateForReadingStatus("input_ready", "preview")).toBe("preview_loading");
    expect(stateForReadingStatus("prepared", "preview")).toBe("free");
    expect(stateForReadingStatus("prepared", "preview", {
      result_available: true,
      poll_required: false,
    })).toBe("free");
    expect(isPreviewChartReady("prepared", {
      result_available: true,
      poll_required: false,
    })).toBe(true);
    expect(stateForReadingStatus("prepared", "preview", { poll_required: true })).toBe("preview_loading");
    expect(stateForReadingStatus("completing", "preview")).toBe("preview_loading");
    expect(stateForReadingStatus("input_ready", "deep")).toBe("awaiting_fulfillment");
    expect(stateForReadingStatus("prepared", "deep")).toBe("running");
    expect(stateForReadingStatus("completing", "deep")).toBe("running");
    expect(stateForReadingStatus("delayed", "preview")).toBe("preview_loading");
    expect(stateForReadingStatus("accepted", "deep")).toBe("succeeded");
    expect(stateForReadingStatus("delayed", "deep")).toBe("failed");
    expect(stateForReadingStatus("terminal_stopped", "deep")).toBe("failed");
    expect(stateForReadingStatus("runtime_unknown", "deep")).toBe("failed");
    expect(stateForDeliveryState("payment_required", "awaiting_fulfillment")).toBe("awaiting_fulfillment");
    expect(stateForDeliveryState("queued", "awaiting_fulfillment")).toBe("queued");
    expect(stateForDeliveryState("processing", "queued")).toBe("running");
    expect(stateForDeliveryState("delivered", "running")).toBe("succeeded");
    expect(stateForDeliveryState("failed", "running")).toBe("failed");
  });

  it("exits preview loading and mounts ReadingResult for prepared + result_available + poll_required=false", async () => {
    vi.useFakeTimers();
    mockPollReading.mockResolvedValue({
      ...previewSummary,
      status: "prepared",
      result_available: true,
      poll_required: false,
    });

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByTestId("reading-result-preview-1")).toBeVisible();
    expect(screen.queryByText("正在准备免费盘面")).not.toBeInTheDocument();
    expect(mockPollReading).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(mockPollReading).toHaveBeenCalledTimes(1);
  });


  it("F1: prepared + result_available renders free chart without worker-queue copy", async () => {
    mockPollReading.mockResolvedValue({
      ...previewSummary,
      status: "prepared",
      result_available: true,
      poll_required: false,
    });

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    expect(await screen.findByTestId("reading-result-preview-1")).toBeVisible();
    expect(screen.getByText("免费盘面已就绪")).toBeVisible();
    expect(screen.queryByText("正在准备免费盘面")).not.toBeInTheDocument();
    expect(screen.queryByText(/离开页面后任务仍会继续/)).not.toBeInTheDocument();
  });

  it("F2: chart-ready shell leads with chart and compresses task chrome", async () => {
    const user = userEvent.setup();
    mockPollReading.mockResolvedValue({
      ...previewSummary,
      status: "prepared",
      result_available: true,
      poll_required: false,
    });

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    expect(await screen.findByTestId("reading-result-preview-1")).toBeVisible();
    const flow = screen.getByRole("region", { name: "八字工作台" });
    expect(flow).toHaveAttribute("data-chart-first", "true");
    const chartHeading = screen.getByRole("heading", { name: "免费盘面" });
    const toolbarHeading = screen.getByRole("heading", { name: "八字工作台" });
    expect(chartHeading).toBeVisible();
    expect(
      chartHeading.compareDocumentPosition(toolbarHeading)
        & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "任务进度" })).not.toBeInTheDocument();

    await user.tab();
    expect(screen.getByRole("button", { name: "盘面操作" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "返回录入" })).toHaveFocus();

    const css = readFileSync(
      join(process.cwd(), "src/components/task/bazi-deep-task-flow.module.css"),
      "utf8",
    );
    expect(css).not.toMatch(/\.flow\[data-chart-first="true"\]\s*>\s*\.chartLead\s*\{[^}]*order\s*:/s);
    expect(css).toMatch(/\.toolbar\[data-compact="true"\]\s+\.backButton\s*\{[^}]*min-height:\s*var\(--target-min\)/s);
    const mediumChartLayout = css.slice(
      css.indexOf("@media (min-width: 64rem) and (max-width: 79.999rem)"),
      css.indexOf("@media (max-width: 47.999rem)"),
    );
    expect(mediumChartLayout).toMatch(
      /\.flow\[data-chart-first="true"\]\s+\.result\s+:global\(\[data-bazi-chart-host="true"\]\)\s*\{[^}]*margin-inline:\s*0/s,
    );
  });

  it("keeps a ready chart first through fulfillment, checkout, queue, and running states", async () => {
    mockSessionStatus.value = "signedIn";
    mockPollReading
      .mockResolvedValueOnce(previewSummary)
      .mockImplementation(() => new Promise(() => undefined));
    let releaseDeepStart: ((value: unknown) => void) | undefined;
    mockStartBaziDeepReading.mockReturnValue(
      new Promise((resolve) => {
        releaseDeepStart = resolve;
      }),
    );
    mockCreateBaziDeepCheckout.mockResolvedValue(checkoutPending);
    let releaseCheckout: ((value: typeof checkoutConfirmed) => void) | undefined;
    mockGetBaziDeepCheckout.mockReturnValue(
      new Promise((resolve) => {
        releaseCheckout = resolve;
      }),
    );
    let releaseBinding: ((value: { status: string }) => void) | undefined;
    mockBindReadingFulfillment.mockReturnValue(
      new Promise((resolve) => {
        releaseBinding = resolve;
      }),
    );

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    const preview = await screen.findByTestId("reading-result-preview-1");
    const flow = screen.getByRole("region", { name: "八字工作台" });
    const chartHeading = screen.getByRole("heading", { name: "免费盘面" });
    const toolbarHeading = screen.getByRole("heading", { name: "八字工作台" });
    const expectChartFirst = () => {
      expect(flow).toHaveAttribute("data-chart-first", "true");
      expect(screen.getByTestId("reading-result-preview-1")).toBe(preview);
      expect(preview).toHaveAttribute("data-density", "chart-first");
      expect(
        chartHeading.compareDocumentPosition(toolbarHeading)
          & Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy();
      expect(screen.getAllByRole("button")[0]).toHaveAccessibleName("盘面操作");
    };

    expectChartFirst();
    await userEvent.click(screen.getByRole("button", { name: "开始安全结账" }));
    expect(await screen.findByText("正在准备履约")).toBeVisible();
    expectChartFirst();

    releaseDeepStart?.({
      ...deepSummary,
      status: "input_ready",
      delivery_state: "payment_required",
    });
    expect((await screen.findAllByText("等待支付确认")).length).toBeGreaterThan(0);
    expectChartFirst();

    releaseCheckout?.(checkoutConfirmed);
    await waitFor(() => expect(mockBindReadingFulfillment).toHaveBeenCalled());
    expectChartFirst();

    releaseBinding?.({ status: "running" });
    expect(await screen.findByText("已进入深读队列")).toBeVisible();
    expectChartFirst();

    await waitFor(() => expect(readingSummaryCallbacks.has("deep-1")).toBe(true));
    act(() => {
      readingSummaryCallbacks.get("deep-1")?.({
        ...deepSummary,
        status: "prepared",
        delivery_state: "processing",
      });
    });
    expect(await screen.findByText("深读生成中")).toBeVisible();
    expectChartFirst();
    expect(mockPollReading.mock.calls.filter(([readingId]) => readingId === "preview-1"))
      .toHaveLength(1);
  });

  it("keeps preview loading and continues polling while input_ready", async () => {
    vi.useFakeTimers();
    mockPollReading.mockResolvedValue({
      ...previewSummary,
      status: "input_ready",
    });

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText("正在准备免费盘面")).toBeVisible();
    expect(screen.getByTestId("reading-result-preview-1")).toBeVisible();
    expect(mockPollReading).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(mockPollReading).toHaveBeenCalledTimes(2);
  });

  it("keeps a free preview usable for a signed-out visitor and never starts deep reading", async () => {
    mockPollReading.mockResolvedValue(previewSummary);

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    expect(await screen.findByText("深读需要登录")).toBeVisible();
    expect(screen.getByTestId("reading-result-preview-1")).toBeVisible();
    expect(mockStartBaziDeepReading).not.toHaveBeenCalled();
    expect(mockBindReadingFulfillment).not.toHaveBeenCalled();
  });

  it("shows unpaid without starting deep reading or probing checkout", async () => {
    mockSessionStatus.value = "signedIn";
    mockPollReading.mockResolvedValue(previewSummary);

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    expect(await screen.findByText("尚未确认付费")).toBeVisible();
    expect(screen.getByText(/不会创建 mock 订单/)).toBeVisible();
    expect(screen.getByTestId("reading-result-preview-1"))
      .toHaveAttribute("data-bazi-deep-fulfilled", "false");
    expect(mockStartBaziDeepReading).not.toHaveBeenCalled();
    expect(mockBindReadingFulfillment).not.toHaveBeenCalled();
  });

  it("starts checkout, waits for confirmed payment, then reaches queued → succeeded", async () => {
    mockSessionStatus.value = "signedIn";
    mockPollReading
      .mockResolvedValueOnce(previewSummary)
      .mockResolvedValueOnce(deepSummary);
    mockStartBaziDeepReading.mockResolvedValue({
      ...deepSummary,
      status: "input_ready",
      delivery_state: "payment_required",
    });
    mockCreateBaziDeepCheckout.mockResolvedValue(checkoutPending);
    let releaseCheckout: ((value: typeof checkoutConfirmed) => void) | undefined;
    mockGetBaziDeepCheckout.mockReturnValue(
      new Promise((resolve) => {
        releaseCheckout = resolve;
      }),
    );
    let releaseBinding: ((value: { status: string }) => void) | undefined;
    mockBindReadingFulfillment.mockReturnValue(
      new Promise((resolve) => {
        releaseBinding = resolve;
      }),
    );

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    expect(await screen.findByText("尚未确认付费")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "开始安全结账" }));
    await waitFor(() => expect(mockCreateBaziDeepCheckout).toHaveBeenCalledWith(
      { reading_version_id: "deep-1" },
      expect.any(String),
    ));
    expect(mockRecordConsent).toHaveBeenNthCalledWith(1, {
      policy_key: "privacy",
      policy_version: "development-preview-v0.1",
      context: "purchase",
    });
    expect(mockRecordConsent).toHaveBeenNthCalledWith(2, {
      policy_key: "terms",
      policy_version: "development-preview-v0.1",
      context: "purchase",
    });
    expect(JSON.stringify(mockCreateBaziDeepCheckout.mock.calls[0]?.[0])).not.toMatch(/policy/);
    expect((await screen.findAllByText("等待支付确认")).length).toBeGreaterThan(0);
    await waitFor(() => expect(mockGetBaziDeepCheckout).toHaveBeenCalledWith("order-1"));
    releaseCheckout?.(checkoutConfirmed);
    await waitFor(() => expect(mockBindReadingFulfillment).toHaveBeenCalled());
    expect(mockStartBaziDeepReading).toHaveBeenCalledWith(
      { profile_version_id: "profile-1", query: "事业主线" },
      expect.any(String),
    );
    expect(mockBindReadingFulfillment).toHaveBeenCalledWith(
      "deep-1",
      { payment_id: "confirmed-payment-from-server" },
      expect.any(String),
    );
    expect(screen.queryByText("confirmed-payment-from-server")).not.toBeInTheDocument();

    releaseBinding?.({ status: "running" });
    await waitFor(() => expect(screen.getByText("已进入深读队列")).toBeVisible());
    await waitFor(() => expect(screen.getByText("深读已交付")).toBeVisible());
    expect(screen.getByTestId("reading-result-preview-1"))
      .toHaveAttribute("data-bazi-deep-fulfilled", "true");
    expect(screen.getByTestId("reading-result-deep-1")).toBeVisible();
  });

  it("does not let a late preview summary roll checkout progress back to unpaid", async () => {
    mockSessionStatus.value = "signedIn";
    mockPollReading.mockResolvedValue(previewSummary);
    mockStartBaziDeepReading.mockReturnValue(new Promise(() => undefined));

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    expect(await screen.findByText("尚未确认付费")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "开始安全结账" }));
    expect(await screen.findByText("正在准备履约")).toBeVisible();

    act(() => {
      readingSummaryCallbacks.get("preview-1")?.(previewSummary);
    });

    expect(screen.getByText("正在准备履约")).toBeVisible();
    expect(screen.queryByText("尚未确认付费")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "开始安全结账" })).not.toBeInTheDocument();
  });

  it("fails closed when payment or fulfillment is rejected", async () => {
    mockSessionStatus.value = "signedIn";
    mockPollReading.mockResolvedValue(previewSummary);
    mockStartBaziDeepReading.mockResolvedValue({ ...deepSummary, status: "input_ready", delivery_state: "payment_required" });
    mockCreateBaziDeepCheckout.mockResolvedValue(checkoutPending);
    mockGetBaziDeepCheckout.mockResolvedValue(checkoutConfirmed);
    mockBindReadingFulfillment.mockRejectedValue(new Error("confirmed payment is required"));

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    await userEvent.click(await screen.findByRole("button", { name: "开始安全结账" }));
    expect(await screen.findByText("confirmed payment is required")).toBeVisible();
    expect(screen.queryByTestId("reading-result-deep-1")).not.toBeInTheDocument();
  });

  it("recovers a confirmed checkout after fulfillment binding fails", async () => {
    mockSessionStatus.value = "signedIn";
    mockPollReading
      .mockResolvedValueOnce(previewSummary)
      .mockImplementation(() => new Promise(() => undefined));
    mockStartBaziDeepReading.mockResolvedValue({
      ...deepSummary,
      status: "input_ready",
      delivery_state: "payment_required",
    });
    mockCreateBaziDeepCheckout.mockResolvedValue(checkoutPending);
    mockGetBaziDeepCheckout.mockResolvedValue(checkoutConfirmed);
    mockBindReadingFulfillment
      .mockRejectedValueOnce(new Error("fulfillment binding unavailable"))
      .mockResolvedValueOnce({ status: "running" });

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    await userEvent.click(await screen.findByRole("button", { name: "开始安全结账" }));
    expect(await screen.findByText("fulfillment binding unavailable")).toBeVisible();
    expect(mockBindReadingFulfillment).toHaveBeenCalledTimes(1);
    const originalFulfillmentKey = mockBindReadingFulfillment.mock.calls[0]?.[2];

    await userEvent.click(screen.getByRole("button", { name: "重试状态读取" }));

    await waitFor(() => expect(mockGetBaziDeepCheckout).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(mockBindReadingFulfillment).toHaveBeenCalledTimes(2));
    expect(mockBindReadingFulfillment).toHaveBeenNthCalledWith(
      2,
      "deep-1",
      { payment_id: "confirmed-payment-from-server" },
      originalFulfillmentKey,
    );
    expect(await screen.findByText("已进入深读队列")).toBeVisible();
  });

  it("does not treat the fake/unavailable gateway as a successful payment", async () => {
    mockSessionStatus.value = "signedIn";
    mockPollReading.mockResolvedValue(previewSummary);
    mockStartBaziDeepReading.mockResolvedValue({ ...deepSummary, status: "input_ready", delivery_state: "payment_required" });
    mockCreateBaziDeepCheckout.mockResolvedValue({ ...checkoutPending, gateway_status: "unavailable" });

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    await userEvent.click(await screen.findByRole("button", { name: "开始安全结账" }));
    expect((await screen.findAllByText("支付暂时不可用")).length).toBeGreaterThan(0);
    expect(mockBindReadingFulfillment).not.toHaveBeenCalled();
    expect(screen.queryByTestId("reading-result-deep-1")).not.toBeInTheDocument();
  });

  it("reaccepts on stale purchase policy instead of creating checkout", async () => {
    mockSessionStatus.value = "signedIn";
    mockPollReading.mockResolvedValue(previewSummary);
    mockStartBaziDeepReading.mockResolvedValue({ ...deepSummary, status: "input_ready", delivery_state: "payment_required" });
    const { ApiError } = await import("@/lib/api");
    mockRecordConsent.mockRejectedValue(new ApiError("Policy version is not current", 400));

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    await userEvent.click(await screen.findByRole("button", { name: "开始安全结账" }));
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/auth/consent"));
    expect(mockCreateBaziDeepCheckout).not.toHaveBeenCalled();
    expect(screen.queryByText("Policy version is not current")).not.toBeInTheDocument();
  });

  it("writes the reading query while the workbench is mounted and clears it on back", async () => {
    mockPollReading.mockResolvedValue({
      ...previewSummary,
      status: "prepared",
      result_available: true,
      poll_required: false,
    });
    const onBack = vi.fn();

    render(
      <BaziDeepTaskFlow
        onBack={onBack}
        previewReadingId="preview-1"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    expect(await screen.findByTestId("reading-result-preview-1")).toBeVisible();
    expect(mockReplace).toHaveBeenCalledWith("/bazi?reading=preview-1&profile=profile-1");

    await userEvent.click(screen.getByRole("button", { name: "返回录入" }));
    expect(onBack).toHaveBeenCalledTimes(1);
    expect(mockReplace).toHaveBeenCalledWith("/bazi");
  });

  it("fail-closes with a recover entry when the restored preview reading is gone", async () => {
    const { ApiError } = await import("@/lib/api");
    mockPollReading.mockRejectedValue(new ApiError("任务不存在", 404));

    render(
      <BaziDeepTaskFlow
        onBack={vi.fn()}
        previewReadingId="missing-preview"
        profileVersionId="profile-1"
        query="事业主线"
      />,
    );

    expect(await screen.findByText("还没有可展示的盘面")).toBeVisible();
    expect(screen.getByRole("button", { name: "返回修改资料" })).toBeVisible();
    expect(screen.queryByTestId("reading-result-missing-preview")).not.toBeInTheDocument();
  });
});

describe("guest bazi preview restore", () => {
  const preparedPreview = {
    ...previewSummary,
    status: "prepared" as const,
    result_available: true,
    poll_required: false,
  };

  async function fillGuestBaziForm() {
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("受测对象"), "本人");
    await user.selectOptions(screen.getByLabelText("出生年份"), "1990");
    await user.selectOptions(screen.getByLabelText("出生月份"), "05");
    await user.selectOptions(screen.getByLabelText("出生日期"), "06");
    await user.selectOptions(screen.getByLabelText("出生小时"), "08");
    await user.selectOptions(screen.getByLabelText("出生分钟"), "30");
    await user.selectOptions(screen.getByLabelText("出生省份"), "江苏省");
    await user.selectOptions(screen.getByLabelText("出生城市"), "常州市");
    await user.selectOptions(screen.getByLabelText("出生区县"), "金坛区");
    await user.click(screen.getByRole("radio", { name: "男" }));
    return user;
  }

  function persistPreviewRecovery(question = "请预览我的八字命盘。") {
    persistBaziPreviewRecoveryState({
      readingId: "preview-1",
      profileVersionId: "profile-1",
      question,
    });
  }

  it("reads and writes the guest reading query without dropping other params", () => {
    const current = new URLSearchParams("profile=profile-1");
    expect(readBaziPreviewReadingId(current)).toBeNull();
    expect(baziPreviewRestoreHref("/bazi", current, "preview-1", "profile-1")).toBe(
      "/bazi?profile=profile-1&reading=preview-1",
    );
    expect(readBaziPreviewReadingId(new URLSearchParams("reading=preview-1"))).toBe("preview-1");
    expect(baziPreviewRestoreHref("/bazi", new URLSearchParams("reading=preview-1&profile=profile-1"), null)).toBe(
      "/bazi?profile=profile-1",
    );
  });

  it("restores a prepared preview after a /bazi refresh that still carries the reading query", async () => {
    persistPreviewRecovery();
    mockSearch.value = new URLSearchParams("reading=preview-1&profile=profile-1");
    mockPollReading.mockResolvedValue(preparedPreview);

    render(<ProductTaskExperience product={PRODUCT_CATALOG.bazi} />);

    expect(await screen.findByRole("heading", { name: "八字工作台" })).toBeVisible();
    expect(screen.getByTestId("reading-result-preview-1")).toBeVisible();
    expect(screen.queryByRole("form", { name: "八字任务输入" })).not.toBeInTheDocument();
    expect(mockStartPreviewReading).not.toHaveBeenCalled();
    expect(mockPollReading).toHaveBeenCalledTimes(1);
  });

  it("writes the reading query on first chart generation so refresh can recover it", async () => {
    mockStartPreviewReading.mockResolvedValue({ reading_version_id: "preview-new" });
    mockPollReading.mockResolvedValue(preparedPreview);

    render(<ProductTaskExperience product={PRODUCT_CATALOG.bazi} />);

    expect(await screen.findByRole("form", { name: "八字任务输入" })).toBeVisible();
    const user = await fillGuestBaziForm();
    await user.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));

    expect(await screen.findByRole("heading", { name: "八字工作台" })).toBeVisible();
    expect(mockStartPreviewReading).toHaveBeenCalledTimes(1);
    expect(mockReplace).toHaveBeenCalledWith(
      "/bazi?reading=preview-new&profile=profile-version-1",
    );
    expect(readBaziPreviewRecoveryState("preview-new")).toEqual({
      version: 1,
      readingId: "preview-new",
      profileVersionId: "profile-version-1",
      question: "请预览我的八字命盘。",
    });
  });

  it("restores the submitted question for deep reading instead of using a UI fallback", async () => {
    persistPreviewRecovery("问题 A：未来一年应优先调整什么？");
    mockSearch.value = new URLSearchParams("reading=preview-1&profile=profile-1");
    mockSessionStatus.value = "signedIn";
    mockPollReading.mockResolvedValue(preparedPreview);
    mockStartBaziDeepReading.mockResolvedValue({
      ...deepSummary,
      status: "input_ready",
      delivery_state: "payment_required",
    });
    mockCreateBaziDeepCheckout.mockResolvedValue({
      ...checkoutPending,
      gateway_status: "unavailable",
      redirect_url: null,
    });

    render(<ProductTaskExperience product={PRODUCT_CATALOG.bazi} />);

    await userEvent.click(await screen.findByRole("button", { name: "开始安全结账" }));

    await waitFor(() => {
      expect(mockStartBaziDeepReading).toHaveBeenCalledWith(
        {
          profile_version_id: "profile-1",
          query: "问题 A：未来一年应优先调整什么？",
        },
        expect.any(String),
      );
    });
    expect(mockStartBaziDeepReading).not.toHaveBeenCalledWith(
      expect.objectContaining({ query: "请预览我的八字命盘。" }),
      expect.any(String),
    );
  });

  it("fail-closes old restored previews that have no persisted question", async () => {
    window.sessionStorage.setItem(
      "mingli.bazi-preview-recovery:preview-1",
      JSON.stringify({
        version: 1,
        readingId: "preview-1",
        profileVersionId: "profile-1",
      }),
    );
    mockSearch.value = new URLSearchParams("reading=preview-1&profile=profile-1");
    mockSessionStatus.value = "signedIn";
    mockPollReading.mockResolvedValue(preparedPreview);

    render(<ProductTaskExperience product={PRODUCT_CATALOG.bazi} />);

    expect(await screen.findByText("深读需要重新输入原问题")).toBeVisible();
    expect(screen.getByTestId("reading-result-preview-1")).toBeVisible();
    expect(screen.queryByRole("button", { name: "开始安全结账" })).not.toBeInTheDocument();
    expect(mockStartBaziDeepReading).not.toHaveBeenCalled();
  });

  it("returns to the input form and drops the reading query", async () => {
    persistPreviewRecovery();
    mockSearch.value = new URLSearchParams("reading=preview-1");
    mockPollReading.mockResolvedValue(preparedPreview);

    render(<ProductTaskExperience product={PRODUCT_CATALOG.bazi} />);

    expect(await screen.findByRole("heading", { name: "八字工作台" })).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "返回录入" }));

    expect(await screen.findByRole("form", { name: "八字任务输入" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "八字工作台" })).not.toBeInTheDocument();
    expect(mockReplace).toHaveBeenCalledWith("/bazi");
  });

  it("keeps polling a truly pending preview after restore", async () => {
    vi.useFakeTimers();
    persistPreviewRecovery();
    mockSearch.value = new URLSearchParams("reading=preview-1");
    mockPollReading.mockResolvedValue({
      ...preparedPreview,
      status: "input_ready",
      result_available: undefined,
      poll_required: undefined,
    });

    render(<ProductTaskExperience product={PRODUCT_CATALOG.bazi} />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText("正在准备免费盘面")).toBeVisible();
    expect(screen.getByTestId("reading-result-preview-1")).toBeVisible();
    expect(mockPollReading).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(mockPollReading).toHaveBeenCalledTimes(2);
  });
});
