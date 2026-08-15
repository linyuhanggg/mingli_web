import { describe, expect, it, vi } from "vitest";

import { adminFetch } from "@/lib/api";

describe("admin API error boundaries", () => {
  it("does not expose upstream error titles to operators", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ title: "database password=should-not-render" }),
          { status: 500, headers: { "content-type": "application/json" } },
        ),
      ),
    );

    const result = await adminFetch("/api/v1/admin/me");

    expect(result).toEqual({
      ok: false,
      status: 500,
      title: "运营平台暂时不可用；当前页面保留只读结构。",
    });
  });

  it("turns an unavailable admin service into a readable state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));

    const result = await adminFetch("/api/v1/admin/me");

    expect(result).toEqual({
      ok: false,
      status: 0,
      title: "运营平台暂时不可用；当前页面保留只读结构。",
    });
  });
});
