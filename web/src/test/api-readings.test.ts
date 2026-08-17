import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  ApiError,
  createReadingRecast,
  listReadings,
  resetApiCache,
  startBaziRelationshipReading,
  startCanwenReading,
  startChartSimilarityReading,
  startDaliurenReading,
  startHecanReading,
  startQimenReading,
  startQizhengReading,
  startQizhengRelationshipReading,
  startWenshiReading,
  startZiweiReading,
  startZiweiRelationshipReading,
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

it("submits an explicit Recast request with a stable idempotency key", async () => {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "mingli_csrf=recast-csrf-token; path=/";
  fetchMock.mockResolvedValueOnce(jsonResponse(readingSummary({ capability_id: "liuyao", profile_version_id: null }), 201));

  const result = await createReadingRecast(
    "11111111-1111-4111-8111-111111111111",
    {
      action: "liuyao_one_question",
      cast: [6, 7, 8, 9, 6, 7],
      event_datetime: "2026-08-14T10:00:00+08:00",
      timezone: "Asia/Shanghai",
      location: "上海市",
      dimension_ids: ["outcome"],
    },
    "recast-web-v1",
  );

  expect(result.capability_id).toBe("liuyao");
  const [url, init] = fetchMock.mock.calls[0]!;
  expect(url).toBe("/api/v1/readings/11111111-1111-4111-8111-111111111111/recast");
  expect(init?.method).toBe("POST");
  expect(new Headers(init?.headers).get("Idempotency-Key")).toBe("recast-web-v1");
  expect(JSON.parse(String(init?.body))).toMatchObject({
    action: "liuyao_one_question",
    dimension_ids: ["outcome"],
  });
});

it("routes each newly connected core art through its explicit reading endpoint", async () => {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "mingli_csrf=core-art-csrf-token; path=/";
  fetchMock.mockImplementation(async () =>
    jsonResponse(readingSummary({ capability_id: "ziwei" }), 201),
  );

  await startZiweiReading(
    { profile_version_id: "22222222-2222-4222-8222-222222222222", dimension_ids: ["career"] },
    "ziwei-key-1",
  );
  await startQizhengReading(
    { profile_version_id: "22222222-2222-4222-8222-222222222222", dimension_ids: ["career"] },
    "qizheng-key-1",
  );
  await startQimenReading(
    {
      event_datetime: "2026-08-14T10:00:00+08:00",
      timezone: "Asia/Shanghai",
      location: "上海市",
      query: "这件事如何推进？",
      dimension_ids: ["outcome"],
    },
    "qimen-key-1",
  );
  await startDaliurenReading(
    {
      event_datetime: "2026-08-14T10:00:00+08:00",
      timezone: "Asia/Shanghai",
      location: "上海市",
      query: "这件事如何推进？",
      dimension_ids: ["timing"],
      timing_start: "2026-08-15",
      timing_end: "2026-09-14",
    },
    "liuren-key-1",
  );
  await startWenshiReading(
    {
      cast: [6, 7, 8, 9, 6, 7],
      event_datetime: "2026-08-14T10:00:00+08:00",
      timezone: "Asia/Shanghai",
      location: "上海市",
      query: "这件事如何推进？",
      dimension_ids: ["outcome", "timing"],
    },
    "wenshi-key-1",
  );
  await startCanwenReading(
    {
      profile_version_id: "22222222-2222-4222-8222-222222222222",
      selected_art_ids: ["bazi", "ziwei"],
      query: "比较共同事实范围",
      dimension_ids: ["career"],
    },
    "canwen-key-1",
  );
  await startHecanReading(
    {
      profile_version_id: "22222222-2222-4222-8222-222222222222",
      selected_art_ids: ["bazi", "ziwei"],
      dimension_ids: ["career"],
    },
    "hecan-key-1",
  );
  const relationshipBody = {
    profile_version_ids: [
      "22222222-2222-4222-8222-222222222222",
      "55555555-5555-4555-8555-555555555555",
    ] as [string, string],
    relationship_type: "romantic" as const,
    dimension_ids: ["relationship"] as ["relationship"],
  };
  await startBaziRelationshipReading(relationshipBody, "bazi-relation-key-1");
  await startZiweiRelationshipReading(relationshipBody, "ziwei-relation-key-1");
  await startQizhengRelationshipReading(relationshipBody, "qizheng-relation-key-1");
  await startChartSimilarityReading(
    {
      profile_version_ids: [
        "22222222-2222-4222-8222-222222222222",
        "55555555-5555-4555-8555-555555555555",
      ],
      query: "比较两份已确认命盘的八字四柱事实。",
      dimension_ids: ["state"],
    },
    "chart-similarity-key-1",
  );

  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
    "/api/v1/readings/ziwei",
    "/api/v1/readings/qizheng",
    "/api/v1/readings/qimen",
    "/api/v1/readings/daliuren",
    "/api/v1/readings/wenshi",
    "/api/v1/readings/canwen",
    "/api/v1/readings/hecan",
    "/api/v1/readings/bazi-relationship",
    "/api/v1/readings/ziwei-relationship",
    "/api/v1/readings/qizheng-relationship",
    "/api/v1/readings/chart-similarity",
  ]);
  expect(fetchMock.mock.calls.map(([, init]) => new Headers(init?.headers).get("Idempotency-Key"))).toEqual([
    "ziwei-key-1",
    "qizheng-key-1",
    "qimen-key-1",
    "liuren-key-1",
    "wenshi-key-1",
    "canwen-key-1",
    "hecan-key-1",
    "bazi-relation-key-1",
    "ziwei-relation-key-1",
    "qizheng-relation-key-1",
    "chart-similarity-key-1",
  ]);
});
