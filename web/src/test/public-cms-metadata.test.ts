import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getPublicCmsMetadata } from "@/lib/public-cms-metadata";

const fallback = {
  title: "静态标题",
  description: "静态描述",
};

describe("public CMS SEO metadata", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses the title and summary from the published SEO projection", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          content_key: "seo.about",
          title: "动态页面标题",
          summary: "动态页面描述",
          body: "不应进入 metadata",
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    await expect(getPublicCmsMetadata("seo.about", fallback)).resolves.toEqual({
      title: "动态页面标题",
      description: "动态页面描述",
    });
    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/content/seo.about",
      expect.objectContaining({ next: { revalidate: 60 } }),
    );
  });

  it("keeps static metadata when the SEO projection is unavailable or incomplete", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response("", { status: 404 }));

    await expect(getPublicCmsMetadata("seo.about", fallback)).resolves.toEqual(fallback);

    vi.mocked(fetch).mockRejectedValue(new Error("backend unavailable"));
    await expect(getPublicCmsMetadata("seo.about", fallback)).resolves.toEqual(fallback);
  });
});
