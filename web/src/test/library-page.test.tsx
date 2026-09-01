import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import LibraryArticlePage, { metadata as articleMetadata } from "@/app/library/[slug]/page";
import LibraryPage, { metadata as indexMetadata } from "@/app/library/page";

const api = vi.hoisted(() => ({
  requestJson: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/library",
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));

vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  requestJson: api.requestJson,
}));

function expectRetiredLibrarySurface() {
  const main = screen.getByRole("main");
  expect(within(main).getByRole("heading", { level: 1, name: "知识内容已下线" })).toBeVisible();
  expect(within(main).getByText("公开入口已改为人生 K 线。")).toBeVisible();
  expect(within(main).getByRole("link", { name: "前往人生 K 线" })).toHaveAttribute(
    "href",
    "/life-kline",
  );
  expect(within(main).getByRole("link", { name: "返回首页" })).toHaveAttribute("href", "/");
  expect(main.querySelector('[data-status="retired"]')).not.toBeNull();
}

describe("/library retired surfaces", () => {
  it("retires the index without requesting CMS content", () => {
    render(<LibraryPage />);

    expectRetiredLibrarySurface();
    expect(screen.queryByRole("search", { name: "知识内容筛选" })).not.toBeInTheDocument();
    expect(api.requestJson).not.toHaveBeenCalled();
  });

  it("retires an arbitrary slug without echoing or requesting it", async () => {
    render(await LibraryArticlePage({ params: Promise.resolve({ slug: "private-looking-slug" }) }));

    expectRetiredLibrarySurface();
    expect(screen.queryByText("private-looking-slug")).not.toBeInTheDocument();
    expect(api.requestJson).not.toHaveBeenCalled();
  });

  it("marks the index and slug routes noindex", () => {
    expect(indexMetadata.title).toBe("知识内容已下线");
    expect(articleMetadata.title).toBe("知识内容已下线");
    expect(indexMetadata.robots).toEqual({ index: false, follow: true });
    expect(articleMetadata.robots).toEqual({ index: false, follow: true });
  });
});
