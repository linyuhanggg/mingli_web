import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BaziPage from "@/app/bazi/page";
import { ApiError } from "@/lib/api";
import {
  CHART_RUNTIME_FAULT,
  GUEST_DAILY_READING_LIMIT,
  PAID_READING_REQUIRES_ACCOUNT,
  RATE_LIMIT_EXCEEDED,
  START_READING_UNAVAILABLE,
  mapStartReadingFailure,
} from "@/lib/start-reading-error";

const mockStartPreviewReading = vi.hoisted(() => vi.fn());
const mockCreateProfileDraft = vi.hoisted(() => vi.fn());
const mockConfirmProfileDraft = vi.hoisted(() => vi.fn());
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
  mockCreateProfileDraft.mockReset().mockResolvedValue({ draft_id: "draft-1", status: "draft" });
  mockConfirmProfileDraft.mockReset().mockResolvedValue({
    profile_version_id: "profile-version-1",
    profile_id: "profile-1",
    subject_ref: "林宇航",
    version: 1,
    created_at: "2026-08-19T00:00:00Z",
  });
  mockStartPreviewReading.mockReset().mockRejectedValue(
    new ApiError("Runtime release unavailable", 503),
  );
});

describe("bazi start unavailable copy", () => {
  it("maps Runtime release 503 to the frozen Chinese unavailable title", () => {
    expect(mapStartReadingFailure(new ApiError("Runtime release unavailable", 503))).toEqual({
      state: "unavailable",
      title: START_READING_UNAVAILABLE,
    });
    expect(mapStartReadingFailure(new ApiError("Authentication required", 401))).toEqual({
      state: "unavailable",
      title: START_READING_UNAVAILABLE,
    });
    expect(mapStartReadingFailure(new Error("请重新选择见相照片后再提交。"))).toEqual({
      state: "error",
      title: "请重新选择见相照片后再提交。",
    });
    expect(
      mapStartReadingFailure(new ApiError("Payment required", 403, undefined, "paid_reading_requires_account")),
    ).toEqual({ state: "unauthorized", title: PAID_READING_REQUIRES_ACCOUNT });
    expect(
      mapStartReadingFailure(new ApiError("Too many requests", 429, undefined, "rate_limit_exceeded")),
    ).toEqual({ state: "error", title: RATE_LIMIT_EXCEEDED });
    expect(
      mapStartReadingFailure(new ApiError("Daily cap", 429, undefined, "guest_daily_reading_limit")),
    ).toEqual({ state: "error", title: GUEST_DAILY_READING_LIMIT });
    expect(
      mapStartReadingFailure(new ApiError("Stopped", 503, undefined, "chart_runtime_error")),
    ).toEqual({ state: "unavailable", title: CHART_RUNTIME_FAULT });
  });

  it("stays on the bazi input page and hides Runtime when preview returns 503", async () => {
    const user = userEvent.setup();
    render(<BaziPage />);

    const submit = await screen.findByRole("button", { name: /^立即排盘（免费）/ });
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
    await user.click(submit);

    await waitFor(() => expect(mockStartPreviewReading).toHaveBeenCalled());
    expect(
      await screen.findByRole("status", { name: "服务暂时不可用，请稍后重试。" }),
    ).toHaveAttribute("data-state", "unavailable");
    expect(screen.queryByText(/Runtime/)).not.toBeInTheDocument();
    expect(screen.queryByText("Runtime release unavailable")).not.toBeInTheDocument();
    expect(screen.getByRole("form", { name: "八字任务输入" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "八字工作台" })).not.toBeInTheDocument();
  });

  it("does not put Runtime on the production start path", () => {
    for (const file of [
      "src/lib/start-reading-error.ts",
      "src/components/task/product-task-experience.tsx",
      "src/components/task/product-input-form.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/§10|§6\.2/);
    }
    const mapper = readFileSync(resolve(process.cwd(), "src/lib/start-reading-error.ts"), "utf8");
    expect(mapper).toContain("服务暂时不可用，请稍后重试。");
  });
});
