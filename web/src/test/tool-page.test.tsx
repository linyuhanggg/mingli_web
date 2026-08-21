import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ToolsPage from "@/app/tools/page";
import ToolDetailPage from "@/app/tools/[tool]/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  requestJson: vi.fn(),
  listProfiles: vi.fn(),
  createIdempotencyKey: vi.fn(),
  formatProfileOption: vi.fn((profile: { version: number }) => `档案 ${profile.version}`),
  startTimeCheckReading: vi.fn(),
  startChartSimilarityReading: vi.fn(),
  startRhythmReading: vi.fn(),
  startFiveElementsFactsReading: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/tools",
  useSearchParams: () => new URLSearchParams(),
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
  listProfiles: api.listProfiles,
  createIdempotencyKey: api.createIdempotencyKey,
  formatProfileOption: api.formatProfileOption,
  startTimeCheckReading: api.startTimeCheckReading,
  startChartSimilarityReading: api.startChartSimilarityReading,
  startRhythmReading: api.startRhythmReading,
  startFiveElementsFactsReading: api.startFiveElementsFactsReading,
}));

vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  requestJson: api.requestJson,
}));

beforeEach(() => {
  api.getAccount.mockReset();
  api.requestJson.mockReset();
  api.listProfiles.mockReset();
  api.createIdempotencyKey.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.listProfiles.mockResolvedValue({ profiles: [] });
  api.createIdempotencyKey.mockReturnValue("tool-intent-1");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("/tools index", () => {
  it("uses a 30px 工具 title and only links the connected entries", () => {
    render(<ToolsPage />);

    expect(screen.getByRole("heading", { level: 1, name: "工具" })).toBeVisible();
    expect(screen.getByText("只展示已经开放的入口。")).toBeVisible();
    expect(screen.getByRole("link", { name: "寻时定盘" })).toHaveAttribute("href", "/tools/time-check");
    expect(screen.getByRole("link", { name: "同盘匹配" })).toHaveAttribute("href", "/tools/chart-similarity");
    expect(screen.getByRole("link", { name: "本命音律" })).toHaveAttribute("href", "/tools/rhythm");
    expect(screen.getByRole("link", { name: "五行事实与调候" })).toHaveAttribute(
      "href",
      "/tools/five-elements",
    );
    expect(screen.queryByRole("link", { name: "解梦" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "姓名分析" })).not.toBeInTheDocument();
    expect(screen.getByText("解梦")).toBeVisible();
    expect(screen.getAllByText("尚未开放").length).toBeGreaterThan(0);
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText(/content_key|CMS 投影|阅读 tools/)).not.toBeInTheDocument();
  });
});

describe("/tools/[tool] product pages", () => {
  it.each([
    ["dream", "解梦", ["梦境内容", "现实背景"]],
    ["name", "姓名分析", ["姓名", "使用场景"]],
  ] as const)("keeps unconnected %s on a disabled readonly boundary", async (slug, title, fields) => {
    const page = await ToolDetailPage({ params: Promise.resolve({ tool: slug }) });
    render(page);

    expect(screen.getByRole("heading", { level: 1, name: title })).toBeVisible();
    for (const label of fields) {
      const control = screen.getByLabelText(label);
      const fieldLabel = screen.getByText(label, { selector: "label" });
      const hint = document.getElementById(control.getAttribute("aria-describedby") ?? "");

      expect(control).toHaveAttribute("readonly");
      expect(fieldLabel.nextElementSibling).toBe(control);
      expect(control.nextElementSibling).toBe(hint);
    }
    expect(screen.getByRole("button", { name: "提交暂未开放" })).toBeDisabled();
    expect(api.requestJson).not.toHaveBeenCalled();
  });

  it.each([
    ["time-check", "寻时定盘", "围绕未知时辰生成候选事实"],
    ["chart-similarity", "同盘匹配", "比较两份命盘的八字四柱事实"],
    ["rhythm", "本命音律", "查看本命音律事实"],
    ["five-elements", "五行事实与调候", "查看五行事实与调候依据"],
  ] as const)("keeps connected %s on the product shell without a fake result", async (slug, title, flowTitle) => {
    const page = await ToolDetailPage({ params: Promise.resolve({ tool: slug }) });
    render(page);

    expect(screen.getByRole("heading", { level: 1, name: title })).toBeVisible();
    expect(await screen.findByRole("heading", { level: 2, name: flowTitle })).toBeVisible();
    expect(screen.queryByRole("button", { name: "提交暂未开放" })).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
  });

  it("does not guess an unknown tool from the URL", async () => {
    const page = await ToolDetailPage({ params: Promise.resolve({ tool: "private-route-value" }) });
    render(page);

    expect(screen.getByRole("heading", { level: 1, name: "这个工具入口尚未开放。" })).toBeVisible();
    expect(screen.queryByText("private-route-value")).not.toBeInTheDocument();
    expect(api.requestJson).not.toHaveBeenCalled();
  });

  it("does not put a construction Status shell on the production tool files", () => {
    for (const file of [
      "src/app/tools/page.tsx",
      "src/app/tools/[tool]/page.tsx",
      "src/components/tool-page.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/development_code|调试码/);
      expect(source).not.toMatch(/SecondaryStatus|StatusPanel|authGrid|SecondarySurfaceFrame|PublicContentSurface|AuthShell/);
      expect(source).not.toMatch(/待接入/);
      expect(source).not.toMatch(/Provider|adapter|适配器|Runtime/);
    }
  });
});
