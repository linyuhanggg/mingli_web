import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  ApiError,
  listReadings,
  resetApiCache,
  type ReadingVersionSummary,
} from "@/lib/api";


function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function clearCsrfCookie() {
  document.cookie =
    "mingli_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
}

function readingSummary(
  overrides: Partial<ReadingVersionSummary> = {},
): ReadingVersionSummary {
  return {
    reading_version_id: "33333333-3333-4333-8333-333333333333",
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    capability_id: "fortune",
    version: 1,
    status: "accepted",
    object_id: "near_time_personal",
    dimension_ids: ["overview"],
    horizon: { kind_id: "day", start: "2026-08-10", end: "2026-08-10" },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-10T01:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  clearCsrfCookie();
  resetApiCache();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it("reads the CSRF cookie and then lists readings without a Guest Session or CSRF header", async () => {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "mingli_csrf=history-csrf-cookie-token; path=/";
  fetchMock.mockResolvedValueOnce(
    jsonResponse({ readings: [readingSummary()] }),
  );

  const result = await listReadings();

  expect(result.readings).toHaveLength(1);
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, init] = fetchMock.mock.calls[0]!;
  expect(url).toBe("/api/v1/readings");
  expect(init?.method).toBeUndefined();
  expect(new Headers(init?.headers).has("X-CSRF-Token")).toBe(false);
});

it("creates a Guest Session before listing readings when no cookie exists", async () => {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  fetchMock
    .mockResolvedValueOnce(
      jsonResponse(
        {
          status: "active",
          expires_at: "2026-08-11T00:00:00Z",
          csrf_token: "guest-csrf-for-history-list",
        },
        201,
      ),
    )
    .mockResolvedValueOnce(
      jsonResponse({ readings: [readingSummary()] }),
    );

  await listReadings();

  expect(fetchMock).toHaveBeenNthCalledWith(
    1,
    "/api/v1/guest-sessions",
    expect.objectContaining({ method: "POST", credentials: "include" }),
  );
  expect(fetchMock).toHaveBeenNthCalledWith(
    2,
    "/api/v1/readings",
    expect.objectContaining({ credentials: "include" }),
  );
});

it("throws ApiError with the problem title and detail on server errors", async () => {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "mingli_csrf=history-csrf-cookie-token; path=/";
  fetchMock.mockResolvedValueOnce(
    jsonResponse({ title: "读取失败", detail: "数据库繁忙" }, 500),
  );

  const promise = listReadings();

  await expect(promise).rejects.toMatchObject({
    name: "ApiError",
    status: 500,
    message: "读取失败",
    detail: "数据库繁忙",
  } satisfies Partial<ApiError>);
  await expect(promise).rejects.toBeInstanceOf(ApiError);
});

it("preserves the newest-first order the server returns", async () => {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "mingli_csrf=history-csrf-cookie-token; path=/";
  fetchMock.mockResolvedValueOnce(
    jsonResponse({
      readings: [
        readingSummary({ created_at: "2026-08-10T02:00:00Z" }),
        readingSummary({
          reading_version_id: "55555555-5555-4555-8555-555555555555",
          created_at: "2026-08-09T02:00:00Z",
        }),
      ],
    }),
  );

  const { readings } = await listReadings();

  expect(readings.map((entry) => entry.created_at)).toEqual([
    "2026-08-10T02:00:00Z",
    "2026-08-09T02:00:00Z",
  ]);
});
