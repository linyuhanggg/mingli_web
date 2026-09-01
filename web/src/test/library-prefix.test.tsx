import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import LibraryArticlePage from "@/app/library/[slug]/page";
import LibraryPage from "@/app/library/page";

const api = vi.hoisted(() => ({ requestJson: vi.fn() }));

vi.mock("next/navigation", () => ({ usePathname: () => "/library" }));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));

vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  requestJson: api.requestJson,
}));

describe("retired library prefix", () => {
  it("does not reopen the retired CMS index or article prefix", async () => {
    const index = render(<LibraryPage />);
    expect(screen.getByRole("heading", { name: "知识内容已下线" })).toBeVisible();
    index.unmount();

    render(await LibraryArticlePage({ params: Promise.resolve({ slug: "intro" }) }));
    expect(screen.getByRole("heading", { name: "知识内容已下线" })).toBeVisible();
    expect(api.requestJson).not.toHaveBeenCalled();
  });
});
