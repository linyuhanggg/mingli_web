import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import DailyPage, { metadata } from "@/app/daily/page";

const api = vi.hoisted(() => ({
  requestJson: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/daily",
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));

vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  requestJson: api.requestJson,
}));

describe("/daily retired surface", () => {
  it("keeps the old deep link understandable without requesting daily content", () => {
    render(<DailyPage />);

    const main = screen.getByRole("main");
    expect(within(main).getByRole("heading", { level: 1, name: "每日已下线" })).toBeVisible();
    expect(within(main).getByText("公开入口已改为人生 K 线。")).toBeVisible();
    expect(within(main).getByRole("link", { name: "前往人生 K 线" })).toHaveAttribute(
      "href",
      "/life-kline",
    );
    expect(within(main).getByRole("link", { name: "返回首页" })).toHaveAttribute("href", "/");
    expect(main.querySelector('[data-status="retired"]')).not.toBeNull();
    expect(api.requestJson).not.toHaveBeenCalled();
  });

  it("marks the retired route noindex while allowing crawlers to follow the replacement", () => {
    expect(metadata.title).toBe("每日已下线");
    expect(metadata.robots).toEqual({ index: false, follow: true });
  });
});
