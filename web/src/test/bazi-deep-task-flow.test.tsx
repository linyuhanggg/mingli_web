import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockPollReading = vi.hoisted(() => vi.fn());
const mockStartBaziDeepReading = vi.hoisted(() => vi.fn());
const mockCreateBaziDeepCheckout = vi.hoisted(() => vi.fn());
const mockGetBaziDeepCheckout = vi.hoisted(() => vi.fn());
const mockBindReadingFulfillment = vi.hoisted(() => vi.fn());
const mockRecordConsent = vi.hoisted(() => vi.fn());
const mockReplace = vi.hoisted(() => vi.fn());
const mockSessionStatus = vi.hoisted(() => ({ value: "signedOut" as "checking" | "signedOut" | "signedIn" }));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  pollReading: mockPollReading,
  startBaziDeepReading: mockStartBaziDeepReading,
  createBaziDeepCheckout: mockCreateBaziDeepCheckout,
  getBaziDeepCheckout: mockGetBaziDeepCheckout,
  bindReadingFulfillment: mockBindReadingFulfillment,
  recordConsent: mockRecordConsent,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn(), prefetch: vi.fn(), refresh: vi.fn(), back: vi.fn(), forward: vi.fn() }),
}));

vi.mock("@/components/account-session-context", () => ({
  useOptionalAccountSession: () => ({ state: { status: mockSessionStatus.value } }),
}));

vi.mock("@/components/readings/reading-result", async () => {
  const { useEffect } = await import("react");
  return {
    ReadingResult: ({
      readingId,
      onPollError,
      onSummary,
    }: {
      readingId: string;
      onPollError?: (error: unknown) => void;
      onSummary?: (summary: typeof previewSummary) => void;
    }) => {
      useEffect(() => {
        let active = true;
        void mockPollReading(readingId).then(
          (summary: typeof previewSummary) => {
            if (active) onSummary?.(summary);
          },
          (error: unknown) => {
            if (active) onPollError?.(error);
          },
        );
        return () => {
          active = false;
        };
      }, [readingId, onPollError, onSummary]);
      return <div data-testid={`reading-result-${readingId}`}>服务端结果 renderer</div>;
    },
  };
});

import {
  BaziDeepTaskFlow,
  stateForDeliveryState,
  stateForReadingStatus,
} from "@/components/task/bazi-deep-task-flow";

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
  mockSessionStatus.value = "signedOut";
  mockPollReading.mockReset();
  mockStartBaziDeepReading.mockReset();
  mockCreateBaziDeepCheckout.mockReset();
  mockGetBaziDeepCheckout.mockReset();
  mockBindReadingFulfillment.mockReset();
  mockRecordConsent.mockReset();
  mockRecordConsent.mockResolvedValue({});
  mockReplace.mockReset();
});

afterEach(cleanup);

describe("Bazi deep task state contract", () => {
  it("maps only public ReadingVersion statuses and keeps job states explicit", () => {
    expect(stateForReadingStatus("accepted", "preview")).toBe("free");
    expect(stateForReadingStatus("input_ready", "preview")).toBe("preview_loading");
    expect(stateForReadingStatus("prepared", "preview")).toBe("preview_loading");
    expect(stateForReadingStatus("input_ready", "deep")).toBe("awaiting_fulfillment");
    expect(stateForReadingStatus("prepared", "deep")).toBe("running");
    expect(stateForReadingStatus("completing", "deep")).toBe("running");
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
    expect(mockPollReading).toHaveBeenCalledTimes(1);
    expect(mockPollReading).toHaveBeenCalledWith("preview-1");
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
    expect(screen.getByText(/只有支付确认后才会开始深读/)).toBeVisible();
    expect(document.body).not.toHaveTextContent(/payment_id|Payment|履约|结账|Fake|mock/);
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
    await userEvent.click(screen.getByRole("button", { name: "前往支付" }));
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
    expect(screen.getByText("请在打开的支付页面完成付款。支付确认后才会开始深读。")).toBeVisible();
    expect(document.body).not.toHaveTextContent(/payment_id|Payment|履约|结账|Fake|mock/);
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
    await waitFor(() => expect(screen.getByText("深读已完成")).toBeVisible());
    expect(screen.getByTestId("reading-result-deep-1")).toBeVisible();
    expect(mockPollReading.mock.calls.map(([readingId]) => readingId)).toEqual([
      "preview-1",
      "deep-1",
    ]);
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

    await userEvent.click(await screen.findByRole("button", { name: "前往支付" }));
    expect(await screen.findByText("confirmed payment is required")).toBeVisible();
    expect(screen.queryByTestId("reading-result-deep-1")).not.toBeInTheDocument();
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

    await userEvent.click(await screen.findByRole("button", { name: "前往支付" }));
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

    await userEvent.click(await screen.findByRole("button", { name: "前往支付" }));
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/auth/consent"));
    expect(mockCreateBaziDeepCheckout).not.toHaveBeenCalled();
    expect(screen.queryByText("Policy version is not current")).not.toBeInTheDocument();
  });
});
