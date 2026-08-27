import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProductTaskExperience } from "@/components/task/product-task-experience";
import { baziPreviewHref, readBaziPreviewReadingId } from "@/lib/bazi-preview-restore";
import { getProductDefinition } from "@/products/catalog";

const mockPollReading = vi.hoisted(() => vi.fn());
const mockStartPreviewReading = vi.hoisted(() => vi.fn());
const mockCreateProfileDraft = vi.hoisted(() => vi.fn());
const mockConfirmProfileDraft = vi.hoisted(() => vi.fn());
const mockListProfiles = vi.hoisted(() => vi.fn());
const mockReplace = vi.hoisted(() => vi.fn());
const mockSearch = vi.hoisted(() => ({ value: new URLSearchParams() }));

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({
    replace: mockReplace,
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
  usePathname: () => "/bazi",
  useSearchParams: () => mockSearch.value,
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  pollReading: mockPollReading,
  startPreviewReading: mockStartPreviewReading,
  createProfileDraft: mockCreateProfileDraft,
  confirmProfileDraft: mockConfirmProfileDraft,
  listProfiles: mockListProfiles,
  getCapabilityProjection: vi.fn().mockResolvedValue({
    runtime_release_profile: "v53-time-check",
    source_status: "available",
    capabilities: [],
  }),
}));

vi.mock("@/components/account-session-context", () => ({
  useOptionalAccountSession: () => ({ state: { status: "signedOut" } }),
}));

vi.mock("@/components/readings/reading-result", () => ({
  ReadingResult: ({ readingId }: { readingId: string }) => (
    <div data-testid={`reading-result-${readingId}`}>服务端结果 renderer</div>
  ),
}));

const preparedPreview = {
  reading_version_id: "preview-1",
  reading_root_id: "root-1",
  profile_version_id: "profile-1",
  capability_id: "bazi",
  product_id: "bazi",
  runtime_capability_ids: ["bazi"],
  version: 1,
  status: "prepared" as const,
  result_available: true,
  poll_required: false,
  object_id: "natal",
  dimension_ids: ["career"],
  horizon: { kind_id: "life", start: null, end: null },
  prior_answer: null,
  input_request: null,
  created_at: "2026-08-18T00:00:00Z",
};

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

beforeEach(() => {
  mockSearch.value = new URLSearchParams();
  mockReplace.mockReset();
  mockPollReading.mockReset();
  mockStartPreviewReading.mockReset();
  mockCreateProfileDraft.mockReset().mockResolvedValue({ draft_id: "draft-1", status: "draft" });
  mockConfirmProfileDraft.mockReset().mockResolvedValue({
    profile_version_id: "profile-version-1",
    profile_id: "profile-1",
    subject_ref: "本人",
    version: 1,
    created_at: "2026-08-14T00:00:00Z",
  });
  mockListProfiles.mockReset().mockResolvedValue({ profiles: [] });
});

async function fillGuestBaziForm() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("受测对象"), "本人");
  await user.selectOptions(screen.getByLabelText("出生年份"), "1990");
  await user.selectOptions(screen.getByLabelText("出生月份"), "05");
  await user.selectOptions(screen.getByLabelText("出生日期"), "06");
  await user.selectOptions(screen.getByLabelText("出生小时"), "08");
  await user.selectOptions(screen.getByLabelText("出生分钟"), "30");
  await user.selectOptions(screen.getByLabelText("出生省份"), "江苏省");
  await user.selectOptions(screen.getByLabelText("出生城市"), "常州市");
  await user.selectOptions(screen.getByLabelText("出生区县"), "金坛区");
  await user.click(screen.getByRole("radio", { name: "男" }));
  return user;
}

describe("bazi preview restore helpers", () => {
  it("reads and writes the guest reading query without dropping other params", () => {
    const current = new URLSearchParams("profile=profile-1");
    expect(readBaziPreviewReadingId(current)).toBeNull();
    expect(baziPreviewHref("/bazi", current, "preview-1", "profile-1")).toBe(
      "/bazi?profile=profile-1&reading=preview-1",
    );
    expect(readBaziPreviewReadingId(new URLSearchParams("reading=preview-1"))).toBe("preview-1");
    expect(baziPreviewHref("/bazi", new URLSearchParams("reading=preview-1&profile=profile-1"), null)).toBe(
      "/bazi?profile=profile-1",
    );
  });
});

describe("guest bazi preview restore", () => {
  it("restores a prepared preview after a /bazi refresh that still carries the reading query", async () => {
    mockSearch.value = new URLSearchParams("reading=preview-1&profile=profile-1");
    mockPollReading.mockResolvedValue(preparedPreview);

    render(<ProductTaskExperience product={getProductDefinition("bazi")} />);

    expect(await screen.findByRole("heading", { name: "八字工作台" })).toBeVisible();
    expect(screen.getByTestId("reading-result-preview-1")).toBeVisible();
    expect(screen.queryByRole("form", { name: "八字任务输入" })).not.toBeInTheDocument();
    expect(mockStartPreviewReading).not.toHaveBeenCalled();
    expect(mockPollReading).toHaveBeenCalledTimes(1);
  });

  it("writes the reading query on first chart generation so refresh can recover it", async () => {
    mockStartPreviewReading.mockResolvedValue({ reading_version_id: "preview-new" });
    mockPollReading.mockResolvedValue(preparedPreview);

    render(<ProductTaskExperience product={getProductDefinition("bazi")} />);

    expect(await screen.findByRole("form", { name: "八字任务输入" })).toBeVisible();
    const user = await fillGuestBaziForm();
    await user.click(screen.getByRole("button", { name: /^立即排盘（免费）/ }));

    expect(await screen.findByRole("heading", { name: "八字工作台" })).toBeVisible();
    expect(mockStartPreviewReading).toHaveBeenCalledTimes(1);
    expect(mockReplace).toHaveBeenCalledWith(
      "/bazi?reading=preview-new&profile=profile-version-1",
    );
  });

  it("returns to the input form and drops the reading query", async () => {
    mockSearch.value = new URLSearchParams("reading=preview-1");
    mockPollReading.mockResolvedValue(preparedPreview);

    render(<ProductTaskExperience product={getProductDefinition("bazi")} />);

    expect(await screen.findByRole("heading", { name: "八字工作台" })).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "返回录入" }));

    expect(await screen.findByRole("form", { name: "八字任务输入" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "八字工作台" })).not.toBeInTheDocument();
    expect(mockReplace).toHaveBeenCalledWith("/bazi");
  });

  it("keeps polling a truly pending preview after restore", async () => {
    vi.useFakeTimers();
    mockSearch.value = new URLSearchParams("reading=preview-1");
    mockPollReading.mockResolvedValue({
      ...preparedPreview,
      status: "input_ready",
      result_available: undefined,
      poll_required: undefined,
    });

    render(<ProductTaskExperience product={getProductDefinition("bazi")} />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText("正在准备免费盘面")).toBeVisible();
    expect(screen.queryByTestId("reading-result-preview-1")).not.toBeInTheDocument();
    expect(mockPollReading).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(mockPollReading).toHaveBeenCalledTimes(2);
  });
});
