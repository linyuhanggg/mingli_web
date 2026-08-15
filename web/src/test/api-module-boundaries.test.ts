import { afterEach, expect, it, vi } from "vitest";

import { ApiError, requestJson } from "@/lib/api/client";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

it("keeps session credentials in the shared API transport layer", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(jsonResponse({ ok: true }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(requestJson<{ ok: boolean }>("/api/v1/transport-test")).resolves
    .toEqual({ ok: true });

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/transport-test",
    expect.objectContaining({ credentials: "include" }),
  );
});

it("keeps structured problem details in the shared API transport layer", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(
      jsonResponse({ title: "读取失败", detail: "数据库繁忙" }, 503),
    );
  vi.stubGlobal("fetch", fetchMock);

  await expect(requestJson("/api/v1/transport-test")).rejects.toMatchObject({
    name: "ApiError",
    status: 503,
    message: "读取失败",
    detail: "数据库繁忙",
  } satisfies Partial<ApiError>);
});
