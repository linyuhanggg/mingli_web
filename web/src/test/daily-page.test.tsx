import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DailyPage from "@/app/daily/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  requestJson: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/daily",
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
  content_key: "daily",
  locale: "zh-CN",
  revision: 2,
  title: "今日宜忌摘要",
  summary: "只谈已发布的当日说明。",
  topic: "cms-topic",
  source_title: "CMS",
  source_url: "/app/fortune/today",
  body: "正文只保留可展示段落。",
  created_at: "2026-08-14T03:00:00Z",
};

describe("/daily product page", () => {
  it("uses a 30px 每日 title and the frozen intro", async () => {
    api.requestJson.mockResolvedValue(published);
    render(<DailyPage />);

    expect(screen.getByRole("heading", { level: 1, name: "每日" })).toBeVisible();
    expect(screen.getByText("只展示当天已发布的内容")).toBeVisible();
    expect(await screen.findByRole("heading", { level: 2, name: "今日宜忌摘要" })).toBeVisible();
    expect(screen.getByText("只谈已发布的当日说明。")).toBeVisible();
    expect(screen.getByText("正文只保留可展示段落。")).toBeVisible();
    expect(screen.queryByText("daily")).not.toBeInTheDocument();
    expect(screen.queryByText("cms-topic")).not.toBeInTheDocument();
    expect(screen.queryByText("CMS")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /fortune/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/content_key|CMS 投影|\/app\/fortune/)).not.toBeInTheDocument();
  });

  it("shows the frozen empty copy when nothing published", async () => {
    api.requestJson.mockResolvedValue({ items: [] });
    render(<DailyPage />);

    expect(await screen.findByText("今日还没有可展示的内容")).toBeVisible();
    expect(screen.queryByText(/每日能力暂不可用|每日信息只展示当天真实可用/)).not.toBeInTheDocument();
  });

  it("shows a retry failure, not the empty copy, when the content service fails", async () => {
    api.requestJson.mockRejectedValue(new Error("CMS exploded"));
    render(<DailyPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("读取失败，请重试");
    expect(screen.queryByText("今日还没有可展示的内容")).not.toBeInTheDocument();
    expect(screen.queryByText("CMS exploded")).not.toBeInTheDocument();
  });

  it("locks the daily h1 to --font-size-page and keeps the page off PublicContentSurface", () => {
    const css = readFileSync(resolve(process.cwd(), "src/components/daily-page.module.css"), "utf8");
    const page = readFileSync(resolve(process.cwd(), "src/app/daily/page.tsx"), "utf8");
    const view = readFileSync(resolve(process.cwd(), "src/components/daily-page.tsx"), "utf8");

    expect(css).toMatch(/\.header h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
    expect(page).toContain("DailyPageView");
    expect(page).not.toContain("PublicContentSurface");
    expect(view).not.toMatch(/content_key|\/app\/fortune|CMS/);
  });
});
