import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BaziPage from "@/app/bazi/page";
import { ApiError } from "@/lib/api";

const mockStartPreviewReading = vi.hoisted(() => vi.fn());
const mockCreateProfileDraft = vi.hoisted(() => vi.fn());
const mockConfirmProfileDraft = vi.hoisted(() => vi.fn());
const mockDiscardProfileDraft = vi.hoisted(() => vi.fn());
const mockListProfiles = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/bazi",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  createProfileDraft: mockCreateProfileDraft,
  confirmProfileDraft: mockConfirmProfileDraft,
  discardProfileDraft: mockDiscardProfileDraft,
  startPreviewReading: mockStartPreviewReading,
  listProfiles: mockListProfiles,
  getCapabilityProjection: vi.fn().mockResolvedValue({
    runtime_release_profile: "v53-time-check",
    source_status: "available",
    capabilities: [],
  }),
}));

afterEach(cleanup);

beforeEach(() => {
  mockListProfiles.mockReset().mockResolvedValue({ profiles: [] });
  mockCreateProfileDraft.mockReset().mockResolvedValue({ draft_id: "draft-conflict-1", status: "draft" });
  mockDiscardProfileDraft.mockReset().mockResolvedValue(undefined);
  mockStartPreviewReading.mockReset();
  const conflict = new ApiError("Name conflict", 409, undefined, "profile_name_conflict");
  conflict.options = ["overwrite", "save_as", "cancel"];
  conflict.suggestedSaveAsName = "本人 (2)";
  mockConfirmProfileDraft.mockReset().mockRejectedValue(conflict);
});

async function fillNatalAndSubmit(user: ReturnType<typeof userEvent.setup>) {
  const submit = await screen.findByRole("button", { name: /^立即排盘（免费）/ });
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
  await user.click(submit);
}

describe("product task name-conflict cancel", () => {
  it("discards the persisted draft when the user cancels a name conflict", async () => {
    const user = userEvent.setup();
    render(<BaziPage />);
    await fillNatalAndSubmit(user);

    expect(await screen.findByRole("alertdialog", { name: "档案名称已存在" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "取消" }));

    await waitFor(() => {
      expect(mockDiscardProfileDraft).toHaveBeenCalledWith("draft-conflict-1");
    });
    expect(mockStartPreviewReading).not.toHaveBeenCalled();
    expect(screen.queryByRole("alertdialog", { name: "档案名称已存在" })).not.toBeInTheDocument();
  });
});
