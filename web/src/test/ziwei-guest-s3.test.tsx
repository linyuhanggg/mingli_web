import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductTaskPage } from "@/components/task/product-task-page";
import { ApiError } from "@/lib/api";

const {
  mockConfirmProfileDraft,
  mockCreateProfileDraft,
  mockListProfiles,
  mockPush,
  mockStartZiweiReading,
} = vi.hoisted(() => ({
  mockConfirmProfileDraft: vi.fn(),
  mockCreateProfileDraft: vi.fn(),
  mockListProfiles: vi.fn(),
  mockPush: vi.fn(),
  mockStartZiweiReading: vi.fn(),
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
  listProfiles: mockListProfiles,
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
  mockConfirmProfileDraft.mockReset();
  mockCreateProfileDraft.mockReset();
  mockListProfiles.mockReset();
  mockPush.mockReset();
  mockStartZiweiReading.mockReset();
});

async function fillNatal(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("受测对象"), "访客测试");
  await user.selectOptions(screen.getByLabelText("出生年份"), "1990");
  await user.selectOptions(screen.getByLabelText("出生月份"), "05");
  await user.selectOptions(screen.getByLabelText("出生日期"), "06");
  await user.selectOptions(screen.getByLabelText("出生小时"), "08");
  await user.selectOptions(screen.getByLabelText("出生分钟"), "30");
  await user.selectOptions(screen.getByLabelText("出生省份"), "江苏省");
  await user.selectOptions(screen.getByLabelText("出生城市"), "常州市");
  await user.selectOptions(screen.getByLabelText("出生区县"), "金坛区");
  await user.click(screen.getByRole("radio", { name: "男" }));
}

describe("/ziwei guest result routing", () => {
  it("keeps a successful guest cast on /ziwei and mounts the result contract", async () => {
    mockListProfiles.mockRejectedValue(new ApiError("需要登录", 401));
    mockCreateProfileDraft.mockResolvedValue({ draft_id: "draft-zw", status: "draft" });
    mockConfirmProfileDraft.mockResolvedValue({
      profile_version_id: "profile-zw-1",
      profile_id: "profile-zw",
      subject_ref: "访客测试",
      version: 1,
      created_at: "2026-08-26T00:00:00Z",
    });
    mockStartZiweiReading.mockResolvedValue({
      reading_version_id: "zw-guest-1",
    });

    const user = userEvent.setup();
    render(<ProductTaskPage productId="ziwei" />);
    await screen.findByRole("button", { name: /立即排盘/ });
    await fillNatal(user);
    await user.click(screen.getByRole("button", { name: /立即排盘/ }));

    expect(await screen.findByTestId("ziwei-inline-result")).toHaveTextContent(
      "zw-guest-1",
    );
    expect(screen.getByRole("status", { name: "紫微盘面" })).toBeVisible();
    expect(
      screen.getByText("盘面留在本页。登录只用于保存、历史和深读。"),
    ).toBeVisible();
    expect(mockStartZiweiReading).toHaveBeenCalledTimes(1);
    expect(mockPush).not.toHaveBeenCalled();
    expect(screen.queryByRole("heading", { name: "紫微工作台" })).not.toBeInTheDocument();
    expect(screen.queryByRole("form", { name: /紫微/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/登录后才能查看历史/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "返回录入" }));
    expect(screen.getByRole("form", { name: /紫微/ })).toBeVisible();
    expect(screen.queryByTestId("ziwei-inline-result")).not.toBeInTheDocument();
    expect(screen.getByLabelText("出生省份")).toHaveValue("江苏省");
    expect(screen.getByLabelText("出生城市")).toHaveValue("常州市");
    expect(screen.getByLabelText("出生区县")).toHaveValue("金坛区");
    expect(screen.getByRole("region", { name: "提交前摘要" })).toHaveTextContent(
      "江苏省 / 常州市 / 金坛区",
    );

    await user.click(screen.getByRole("button", { name: /立即排盘/ }));

    expect(await screen.findByTestId("ziwei-inline-result")).toHaveTextContent(
      "zw-guest-1",
    );
    expect(mockConfirmProfileDraft).toHaveBeenNthCalledWith(
      2,
      "draft-zw",
      expect.objectContaining({ location: "江苏省 / 常州市 / 金坛区" }),
    );
  });
});
