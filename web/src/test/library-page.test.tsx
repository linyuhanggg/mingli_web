import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

const published = {
  content_key: "library.intro",
  locale: "zh-CN",
  revision: 3,
  title: "公开文章标题",
  summary: "公开文章摘要",
  topic: "术数基础",
  source_title: "CMS",
  source_url: "https://example.com/source",
  body: "公开文章正文",
  created_at: "2026-08-14T03:00:00Z",
};

describe("/library product pages", () => {
  it("uses a 30px 知识内容 title and hides CMS construction fields", async () => {
    api.requestJson.mockResolvedValue({ items: [published] });
    render(<LibraryPage />);

    expect(screen.getByRole("heading", { level: 1, name: "知识内容" })).toBeVisible();
    expect(screen.getByText("只展示已发布的文章。")).toBeVisible();
    expect(await screen.findByRole("link", { name: "公开文章标题" })).toHaveAttribute(
      "href",
      "/library/intro",
    );
    expect(screen.getByText("公开文章摘要")).toBeVisible();
    expect(screen.queryByText("library.intro")).not.toBeInTheDocument();
    expect(screen.queryByText("CMS")).not.toBeInTheDocument();
    expect(screen.queryByText(/content_key|CMS 投影|projection/)).not.toBeInTheDocument();
  });

  it("does not submit filters when nothing is published", async () => {
    api.requestJson.mockResolvedValue({ items: [] });
    render(<LibraryPage />);

    expect(await screen.findByText("还没有可展示的内容")).toBeVisible();
    expect(screen.queryByRole("search")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "筛选" })).not.toBeInTheDocument();
    expect(api.requestJson).toHaveBeenCalledTimes(1);
    expect(api.requestJson).toHaveBeenCalledWith(
      "/api/v1/content?prefix=library&locale=zh-CN&limit=100",
    );
  });

  it("lets a published index submit filters", async () => {
    api.requestJson
      .mockResolvedValueOnce({ items: [published] })
      .mockResolvedValue({
        items: [{ ...published, content_key: "library.filtered", title: "筛选后的文章" }],
      });
    const user = userEvent.setup();
    render(<LibraryPage />);

    await screen.findByRole("link", { name: "公开文章标题" });
    await user.type(screen.getByLabelText("搜索内容"), "方法");
    await user.selectOptions(screen.getByLabelText("按主题筛选"), "方法与边界");
    await user.click(screen.getByRole("button", { name: "筛选" }));

    expect(await screen.findByRole("link", { name: "筛选后的文章" })).toBeVisible();
    expect(api.requestJson).toHaveBeenLastCalledWith(
      "/api/v1/content?prefix=library&locale=zh-CN&limit=100&q=%E6%96%B9%E6%B3%95&topic=%E6%96%B9%E6%B3%95%E4%B8%8E%E8%BE%B9%E7%95%8C",
    );
  });

  it("does not guess an unpublished article from the slug", async () => {
    api.requestJson.mockRejectedValue(new ApiError("Not found", 404));
    render(await LibraryArticlePage({ params: Promise.resolve({ slug: "missing" }) }));

    expect(screen.getByRole("heading", { level: 1, name: "知识内容" })).toBeVisible();
    expect(await screen.findByText("没有可展示的文章")).toBeVisible();
    expect(screen.queryByText("missing")).not.toBeInTheDocument();
    expect(screen.queryByText("library.missing")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "返回知识内容" })).toBeVisible();
  });

  it("renders only title, summary, and body on a published article", async () => {
    api.requestJson.mockResolvedValue(published);
    render(await LibraryArticlePage({ params: Promise.resolve({ slug: "intro" }) }));

    expect(await screen.findByRole("heading", { level: 2, name: "公开文章标题" })).toBeVisible();
    expect(screen.getByText("公开文章摘要")).toBeVisible();
    expect(screen.getByText("公开文章正文")).toBeVisible();
    expect(screen.queryByText("library.intro")).not.toBeInTheDocument();
    expect(screen.queryByText("术数基础")).not.toBeInTheDocument();
  });

  it("does not put a construction Status shell on the production library files", () => {
    for (const file of [
      "src/app/library/page.tsx",
      "src/app/library/[slug]/page.tsx",
      "src/components/library-page.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/development_code|调试码/);
      expect(source).not.toMatch(/SecondaryStatus|StatusPanel|authGrid|SecondarySurfaceFrame|PublicContentSurface|AuthShell/);
      expect(source).not.toMatch(/CMS 投影|projectionTitle|projectionIntro/);
    }
  });
});
