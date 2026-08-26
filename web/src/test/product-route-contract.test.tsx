import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentType } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BaziPage from "@/app/bazi/page";
import DaliurenPage from "@/app/daliuren/page";
import HecanPage from "@/app/hecan/page";
import JianxiangPage from "@/app/jianxiang/page";
import LiuyaoPage from "@/app/liuyao/page";
import QimenPage from "@/app/qimen/page";
import QizhengPage from "@/app/qizheng/page";
import WenshiPage from "@/app/wenshi/page";
import ZiweiPage from "@/app/ziwei/page";
import { formatProfileOption } from "@/lib/api";

const mockRouterPush = vi.hoisted(() => vi.fn());
const mockCreateProfileDraft = vi.hoisted(() => vi.fn());
const mockConfirmProfileDraft = vi.hoisted(() => vi.fn());
const mockStartPreviewReading = vi.hoisted(() => vi.fn());
const mockPollReading = vi.hoisted(() => vi.fn());
const mockGetCapabilityProjection = vi.hoisted(() => vi.fn());
const mockListProfiles = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: mockRouterPush }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  createProfileDraft: mockCreateProfileDraft,
  confirmProfileDraft: mockConfirmProfileDraft,
  startPreviewReading: mockStartPreviewReading,
  pollReading: mockPollReading,
  getCapabilityProjection: mockGetCapabilityProjection,
  listProfiles: mockListProfiles,
}));

type RouteExpectation = {
  Page: ComponentType;
  name: string;
  input: RegExp;
};

const routes: RouteExpectation[] = [
  { Page: BaziPage, name: "八字", input: /出生日期/ },
  { Page: ZiweiPage, name: "紫微", input: /出生资料/ },
  { Page: QizhengPage, name: "七政", input: /出生地点/ },
  { Page: LiuyaoPage, name: "六爻", input: /起卦方式/ },
  { Page: QimenPage, name: "奇门", input: /场景侧重/ },
  { Page: DaliurenPage, name: "大六壬", input: /判断侧重/ },
  { Page: JianxiangPage, name: "见相", input: /独立同意/ },
  { Page: HecanPage, name: "命盘合参", input: /至少选择两术/ },
  { Page: WenshiPage, name: "问事合参", input: /同一问题与时空/ },
];

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

mockGetCapabilityProjection.mockResolvedValue({
  runtime_release_profile: "v53-time-check",
  source_status: "available",
  capabilities: [
    { capability_id: "bazi", label: "八字", tier: "A", source_system: "bazi", runtime_active_rule_count: 24, judgment_rule_count: 19, source_status: "available" },
    { capability_id: "ziwei", label: "紫微", tier: "B", source_system: "ziwei", runtime_active_rule_count: 2, judgment_rule_count: 0, source_status: "available" },
    { capability_id: "qizheng", label: "七政四余", tier: "B", source_system: "xingming", runtime_active_rule_count: 3, judgment_rule_count: 0, source_status: "available" },
  ],
});
beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  mockPollReading.mockReset().mockResolvedValue({ status: "input_ready" });
  mockListProfiles.mockReset().mockResolvedValue({ profiles: [] });
  vi.stubGlobal("fetch", vi.fn<typeof fetch>(async (url) => {
    const readingId = String(url).split("/").at(-1) ?? "";
    const summary = await mockPollReading(readingId) as Record<string, unknown>;
    return new Response(
      JSON.stringify({ reading_version_id: readingId, ...summary }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  }));
});

describe("primary product route contract", () => {
  it.each(routes)("$name renders a real task surface instead of a placeholder", async ({ Page, name, input }) => {
    render(<Page />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("form", { name: `${name}任务输入` })).toBeVisible();
    expect((await screen.findAllByText(input)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/提交后会发生什么/).length).toBeGreaterThan(0);
    expect(screen.queryByRole("navigation", { name: `${name}任务进度` })).not.toBeInTheDocument();
    expect(screen.queryByText("标「待接入」的现在不会出现")).not.toBeInTheDocument();
    expect(screen.queryByText("UI 演示数据")).not.toBeInTheDocument();
    expect(screen.queryByText("页面已预制")).not.toBeInTheDocument();
  });

  it("keeps local input confirmation in the product route and stops honestly at unavailable compute", async () => {
    const user = userEvent.setup();
    mockCreateProfileDraft.mockResolvedValue({ draft_id: "draft-1", status: "draft" });
    mockConfirmProfileDraft.mockResolvedValue({
      profile_version_id: "profile-version-1",
      profile_id: "profile-1",
      subject_ref: "本人",
      version: 1,
      created_at: "2026-08-14T00:00:00Z",
    });
    mockStartPreviewReading.mockResolvedValue({ reading_version_id: "reading-1" });
    mockPollReading.mockResolvedValue({ status: "accepted" });
    render(<BaziPage />);

    const submit = await screen.findByRole("button", { name: /^免费排盘/ });

    await user.click(submit);
    expect(await screen.findByText("请填写受测对象")).toBeVisible();

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
    expect(screen.getByLabelText("出生省份")).toHaveValue("江苏省");
    expect(screen.getByLabelText("出生城市")).toHaveValue("常州市");
    expect(screen.getByLabelText("出生区县")).toHaveValue("金坛区");
    await user.click(submit);

    await waitFor(() => expect(mockStartPreviewReading).toHaveBeenCalled());

    expect(mockStartPreviewReading).toHaveBeenCalledWith(
      expect.objectContaining({ profile_version_id: "profile-version-1" }),
      expect.any(String),
    );
    expect(await screen.findByRole("heading", { name: "八字工作台" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "免费盘面" })).toBeVisible();
    expect(mockRouterPush).not.toHaveBeenCalled();
  });

  it("reuses the newest saved profile on bazi without asking for birth data again", async () => {
    const savedProfileVersionId = "22222222-2222-4222-8222-222222222222";
    mockCreateProfileDraft.mockClear();
    mockConfirmProfileDraft.mockClear();
    mockStartPreviewReading.mockReset().mockResolvedValue({
      reading_version_id: "reading-from-saved-profile",
    });
    mockListProfiles.mockReset().mockResolvedValue({
      profiles: [
        {
          profile_id: "11111111-1111-4111-8111-111111111111",
          profile_version_id: savedProfileVersionId,
          subject_ref: `profile-version:${savedProfileVersionId}`,
          version: 3,
          display_name: "母亲",
          birth_date: "1965-02-03",
          created_at: "2026-08-19T01:30:00Z",
        },
      ],
    });
    const user = userEvent.setup();

    render(<BaziPage />);

    const profileSelect = await screen.findByRole("combobox", { name: "排盘资料" });
    expect(profileSelect).toHaveValue(savedProfileVersionId);
    expect(profileSelect).toHaveDisplayValue("母亲 · 1965-02-03");
    expect(screen.queryByLabelText("出生年份")).not.toBeInTheDocument();
    expect(profileSelect.closest("fieldset")).toHaveTextContent(
      "将直接使用这份已保存资料；如出生信息有变化，选重新录入。",
    );
    expect(document.body).not.toHaveTextContent(
      /verified_exact|ViewModel|不可变|落库|接纳|句柄|payment_id/,
    );

    await user.click(screen.getByRole("button", { name: /^免费排盘/ }));

    await waitFor(() => expect(mockStartPreviewReading).toHaveBeenCalledTimes(1));
    expect(mockStartPreviewReading).toHaveBeenCalledWith(
      expect.objectContaining({ profile_version_id: savedProfileVersionId }),
      expect.any(String),
    );
    expect(mockCreateProfileDraft).not.toHaveBeenCalled();
    expect(mockConfirmProfileDraft).not.toHaveBeenCalled();
  });

  it("falls back to the existing server profile label when a friendly field is missing", async () => {
    const legacyProfile = {
      profile_id: "44444444-4444-4444-8444-444444444444",
      profile_version_id: "55555555-5555-4555-8555-555555555555",
      subject_ref: "profile-version:55555555-5555-4555-8555-555555555555",
      version: 2,
      display_name: "缺少生日的档案",
      birth_date: null,
      created_at: "2026-08-19T01:30:00Z",
    };
    mockListProfiles.mockResolvedValue({ profiles: [legacyProfile] });

    render(<BaziPage />);

    const profileSelect = await screen.findByRole("combobox", { name: "排盘资料" });
    expect(profileSelect).toHaveDisplayValue(formatProfileOption(legacyProfile));
    expect(profileSelect).not.toHaveDisplayValue("缺少生日的档案 · 生日未记录");
  });
});
