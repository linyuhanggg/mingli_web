import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductTaskPage } from "@/components/task/product-task-page";

const { mockStartZiweiReading, mockCreateProfileDraft, mockConfirmProfileDraft, mockPush } = vi.hoisted(() => ({
  mockStartZiweiReading: vi.fn(),
  mockCreateProfileDraft: vi.fn(),
  mockConfirmProfileDraft: vi.fn(),
  mockPush: vi.fn(),
}));

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
  usePathname: () => "/ziwei",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  getCapabilityProjection: vi.fn().mockResolvedValue({
    runtime_release_profile: "v53-time-check",
    source_status: "available",
    capabilities: [],
  }),
  listProfiles: vi.fn().mockResolvedValue({ profiles: [] }),
  createProfileDraft: mockCreateProfileDraft,
  confirmProfileDraft: mockConfirmProfileDraft,
  startZiweiReading: mockStartZiweiReading,
}));

vi.mock("@/components/readings/reading-result", () => ({
  ReadingResult: ({ readingId }: { readingId: string }) => (
    <div data-testid="ziwei-inline-result">本页紫微盘面 {readingId}</div>
  ),
}));

afterEach(() => {
  cleanup();
  mockStartZiweiReading.mockReset();
  mockCreateProfileDraft.mockReset();
  mockConfirmProfileDraft.mockReset();
  mockPush.mockReset();
});

async function fillNatal(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("受测对象"), "林宇航");
  await user.selectOptions(screen.getByLabelText("出生年份"), "2000");
  await user.selectOptions(screen.getByLabelText("出生月份"), "10");
  await user.selectOptions(screen.getByLabelText("出生日期"), "18");
  await user.selectOptions(screen.getByLabelText("出生小时"), "05");
  await user.selectOptions(screen.getByLabelText("出生分钟"), "10");
  await user.selectOptions(screen.getByLabelText("出生省份"), "福建省");
  await user.selectOptions(screen.getByLabelText("出生城市"), "莆田市");
  await user.selectOptions(screen.getByLabelText("出生区县"), "涵江区");
  await user.click(screen.getByRole("radio", { name: "男" }));
}

describe("/ziwei guest stays on S3", () => {
  it("keeps bazi inline preview routing without router.push on natal success", () => {
    const experience = readFileSync(
      resolve(process.cwd(), "src/components/task/product-task-experience.tsx"),
      "utf8",
    );
    const baziBranch = experience.match(
      /if \(product\.id === "bazi"\) \{[\s\S]*?setStage\("workbench"\);/,
    )?.[0];
    expect(baziBranch).toBeTruthy();
    expect(baziBranch).toContain("setBaziPreviewReadingId");
    expect(baziBranch).not.toContain("router.push");
  });

  it("keeps a successful guest cast on /ziwei and does not push history", async () => {
    mockCreateProfileDraft.mockResolvedValue({ draft_id: "draft-zw", status: "draft" });
    mockConfirmProfileDraft.mockResolvedValue({
      profile_version_id: "profile-zw-1",
      profile_id: "profile-zw",
      subject_ref: "林宇航",
      version: 1,
      created_at: "2026-08-22T00:00:00Z",
    });
    mockStartZiweiReading.mockResolvedValue({
      reading_version_id: "zw-guest-1",
    });
    const user = userEvent.setup();
    render(<ProductTaskPage productId="ziwei" />);
    await screen.findByRole("button", { name: /立即排盘/ });
    await fillNatal(user);
    await user.click(screen.getByRole("button", { name: /立即排盘/ }));

    const board = await screen.findByTestId("ziwei-inline-result");
    expect(board).toHaveTextContent("zw-guest-1");
    expect(screen.getByRole("status", { name: "紫微盘面" })).toBeVisible();
    expect(screen.getByText("盘面留在本页。登录只用于保存、历史和深读。")).toBeVisible();
    expect(mockStartZiweiReading).toHaveBeenCalledTimes(1);
    expect(mockPush).not.toHaveBeenCalled();
    expect(screen.queryByRole("heading", { name: "紫微工作台" })).not.toBeInTheDocument();
    expect(screen.queryByRole("form", { name: /紫微/ })).not.toBeInTheDocument();
    expect(screen.queryByText("登录后才能查看历史")).not.toBeInTheDocument();
    expect(screen.queryByText("需要登录才能查看历史")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "返回录入" }));
    expect(screen.getByRole("form", { name: /紫微/ })).toBeVisible();
    expect(screen.queryByTestId("ziwei-inline-result")).not.toBeInTheDocument();
  });
});
