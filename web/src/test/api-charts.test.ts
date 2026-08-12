import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  supplyBaziChartInput,
  syncBaziChart,
  resetApiCache,
} from "@/lib/api";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const profileVersionId = "22222222-2222-4222-8222-222222222222";

beforeEach(() => {
  resetApiCache();
  document.cookie = "mingli_csrf=chart-csrf-token; path=/";
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie =
    "mingli_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
});

it("posts a synchronous chart request with its required idempotency key", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(
    jsonResponse({
      profile_version_id: profileVersionId,
      status: "ready",
      chart_handle: null,
      fact_panel: {
        question: "查看这个档案的确定性八字盘。",
        vocabulary: [],
        facts: [
          {
            ref: "fact:profile/calculated/bazi/four_pillars",
            subject_ref: `profile-version:${profileVersionId}`,
            kind_id: "kind.fact",
            value: { year: "甲子", month: "乙丑", day: "丙寅", hour: "丁卯" },
            display_text: "四柱",
          },
          {
            ref: "fact:profile/input/birth_datetime",
            subject_ref: `profile-version:${profileVersionId}`,
            kind_id: "kind.input",
            value: "1990-01-01T00:00:00",
            display_text: "出生时间",
          },
        ],
        evidence: [],
        findings: [],
        claim_scopes: [],
        limits: [],
        prior_answer: null,
        request_view: null,
      },
      input_request: null,
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  const result = await syncBaziChart(
    { profile_version_id: profileVersionId },
    "chart-sync-intent-0001",
  );

  expect(result.status).toBe("ready");
  if (result.status === "ready") {
    expect(result.fact_panel.facts.map((fact) => fact.ref)).toEqual([
      "fact:profile/calculated/bazi/four_pillars",
    ]);
  }
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, init] = fetchMock.mock.calls[0]!;
  expect(url).toBe("/api/v1/charts/bazi/sync");
  expect(init?.method).toBe("POST");
  expect(new Headers(init?.headers).get("Idempotency-Key")).toBe(
    "chart-sync-intent-0001",
  );
  expect(JSON.parse(String(init?.body))).toEqual({
    profile_version_id: profileVersionId,
  });
});

it("submits structured runtime input to the opaque chart handle", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(
    jsonResponse({
      profile_version_id: profileVersionId,
      status: "need_input",
      chart_handle: "chart-handle-0001",
      fact_panel: null,
      input_request: {
        requirements: [
          {
            any_of: [
              {
                id: "zi_policy",
                label: "夜子时口径",
                type_id: "choice",
                description: null,
                choices: [],
              },
            ],
          },
        ],
      },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  const result = await supplyBaziChartInput(
    "chart-handle-0001",
    { zi_policy: "midnight" },
    "chart-input-intent-0001",
  );

  expect(result.status).toBe("need_input");
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/charts/bazi/sync/chart-handle-0001/input",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ values: { zi_policy: "midnight" } }),
    }),
  );
  const headers = new Headers(fetchMock.mock.calls[0]?.[1]?.headers);
  expect(headers.get("Idempotency-Key")).toBe("chart-input-intent-0001");
});
