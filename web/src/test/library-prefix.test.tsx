import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LibraryPage from "@/app/library/page";
import LibraryArticlePage from "@/app/library/[slug]/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  requestJson: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/library",
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
}));

vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  requestJson: api.requestJson,
}));

beforeEach(() => {
  api.getAccount.mockReset();
  api.requestJson.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("library list prefix", () => {
  it("requests prefix=library without a trailing dot", async () => {
    api.requestJson.mockResolvedValue({ items: [] });
    render(<LibraryPage />);

    expect(await screen.findByText("还没有可展示的内容")).toBeVisible();
    expect(api.requestJson).toHaveBeenCalledWith(
      "/api/v1/content?prefix=library&locale=zh-CN&limit=100",
    );
    expect(api.requestJson.mock.calls[0]?.[0]).not.toContain("prefix=library.");
  });

  it("still loads an article by library.<slug> and strips the key to /library/intro", async () => {
    api.requestJson.mockResolvedValue({
      items: [
        {
          content_key: "library.intro",
          locale: "zh-CN",
          revision: 1,
          title: "公开文章标题",
          summary: "摘要",
          body: "正文",
          created_at: "2026-08-19T00:00:00Z",
        },
      ],
    });
    render(<LibraryPage />);

    expect(await screen.findByRole("link", { name: "公开文章标题" })).toHaveAttribute(
      "href",
      "/library/intro",
    );

    api.requestJson.mockResolvedValue({
      content_key: "library.intro",
      locale: "zh-CN",
      revision: 1,
      title: "公开文章标题",
      summary: "摘要",
      body: "正文",
      created_at: "2026-08-19T00:00:00Z",
    });
    render(await LibraryArticlePage({ params: Promise.resolve({ slug: "intro" }) }));
    expect(api.requestJson).toHaveBeenCalledWith("/api/v1/content/library.intro");
  });
});
