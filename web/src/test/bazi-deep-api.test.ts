import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  bindReadingFulfillment,
  createBaziDeepCheckout,
  getBaziDeepCheckout,
  resetApiCache,
  startBaziDeepReading,
} from "@/lib/api";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const summary = {
  reading_version_id: "deep-1",
  reading_root_id: "root-1",
  profile_version_id: "profile-1",
  capability_id: "bazi",
  product_id: "bazi-deep",
  runtime_capability_ids: ["bazi"],
  version: 1,
  status: "input_ready",
  object_id: "natal",
  dimension_ids: ["career"],
  horizon: { kind_id: "life", start: null, end: null },
  prior_answer: null,
  input_request: null,
  created_at: "2026-08-18T00:00:00Z",
};

beforeEach(() => {
  resetApiCache();
  document.cookie = "mingli_csrf=bazi-deep-csrf; path=/";
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "mingli_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
});

it("starts the real Bazi deep endpoint with an idempotency key", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(jsonResponse(summary, 201));
  vi.stubGlobal("fetch", fetchMock);

  await startBaziDeepReading(
    { profile_version_id: "profile-1", query: "事业主线" },
    "bazi-deep-start-1",
  );

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/readings/bazi-deep",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ profile_version_id: "profile-1", query: "事业主线" }),
    }),
  );
  const [, init] = fetchMock.mock.calls[0]!;
  const headers = new Headers(init?.headers);
  expect(headers.get("Idempotency-Key")).toBe("bazi-deep-start-1");
  expect(headers.get("X-CSRF-Token")).toBe("bazi-deep-csrf");
});

it("binds only the opaque payment id through the fulfillment seam", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(
    jsonResponse({
      fulfillment_id: "fulfillment-1",
      reading_version_id: "deep-1",
      reading_job_id: "job-1",
      status: "running",
      created: true,
    }, 201),
  );
  vi.stubGlobal("fetch", fetchMock);

  await bindReadingFulfillment(
    "deep-1",
    { payment_id: "opaque-payment-from-server" },
    "bazi-deep-bind-1",
  );

  const [url, init] = fetchMock.mock.calls[0]!;
  expect(url).toBe("/api/v1/readings/deep-1/fulfillment");
  expect(init?.method).toBe("POST");
  expect(init?.body).toBe(JSON.stringify({ payment_id: "opaque-payment-from-server" }));
  expect(init?.body).not.toContain("state_token");
  expect(init?.body).not.toContain("channel_transaction_id");
  expect(new Headers(init?.headers).get("Idempotency-Key")).toBe("bazi-deep-bind-1");
});

it("creates and polls an owner-scoped checkout without browser-selected payment data", async () => {
  const checkout = {
    order: {
      order_id: "order-1",
      reading_version_id: "deep-1",
      product_id: "bazi-deep",
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
    gateway_status: "pending",
    redirect_url: "https://pay.example.invalid/checkout/order-1",
    created: true,
  };
  const confirmed = { ...checkout, gateway_status: "succeeded", payment_id: "confirmed-payment-1" };
  const fetchMock = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(jsonResponse(checkout, 201))
    .mockResolvedValueOnce(jsonResponse(confirmed, 200));
  vi.stubGlobal("fetch", fetchMock);

  await createBaziDeepCheckout({ reading_version_id: "deep-1" }, "checkout-start-1");
  await getBaziDeepCheckout("order-1");

  const [createUrl, createInit] = fetchMock.mock.calls[0]!;
  expect(createUrl).toBe("/api/v1/commerce/checkout");
  expect(createInit?.method).toBe("POST");
  expect(createInit?.body).toBe(JSON.stringify({ reading_version_id: "deep-1" }));
  expect(createInit?.body).not.toContain("offer_id");
  expect(createInit?.body).not.toContain("payment_id");
  expect(new Headers(createInit?.headers).get("Idempotency-Key")).toBe("checkout-start-1");

  const [statusUrl, statusInit] = fetchMock.mock.calls[1]!;
  expect(statusUrl).toBe("/api/v1/commerce/checkout/order-1");
  expect(statusInit?.method).toBeUndefined();
  expect(statusInit?.body).toBeUndefined();
  expect(JSON.stringify(confirmed)).not.toContain("purchase_target_ref");
  expect(JSON.stringify(confirmed)).not.toContain("idempotency_key_hash");
});
