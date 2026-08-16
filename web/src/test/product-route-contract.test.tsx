import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentType } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import BaziPage from "@/app/bazi/page";
import DaliurenPage from "@/app/daliuren/page";
import HecanPage from "@/app/hecan/page";
import JianxiangPage from "@/app/jianxiang/page";
import LiuyaoPage from "@/app/liuyao/page";
import QimenPage from "@/app/qimen/page";
import QizhengPage from "@/app/qizheng/page";
import WenshiPage from "@/app/wenshi/page";
import ZiweiPage from "@/app/ziwei/page";

const mockRouterPush = vi.hoisted(() => vi.fn());
const mockCreateProfileDraft = vi.hoisted(() => vi.fn());
const mockConfirmProfileDraft = vi.hoisted(() => vi.fn());
const mockStartPreviewReading = vi.hoisted(() => vi.fn());

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
}));

type RouteExpectation = {
  Page: ComponentType;
  name: string;
  input: RegExp;
  module: RegExp;
};

const routes: RouteExpectation[] = [
  { Page: BaziPage, name: "八字", input: /出生日期/, module: /四柱与五行力量/ },
  { Page: ZiweiPage, name: "紫微", input: /出生资料/, module: /十二宫与四化/ },
  { Page: QizhengPage, name: "七政", input: /出生地点/, module: /星盘与十一曜/ },
  { Page: LiuyaoPage, name: "六爻", input: /起卦方式/, module: /六次过程与本卦变卦/ },
  { Page: QimenPage, name: "奇门", input: /场景侧重/, module: /九宫与值符值使/ },
  { Page: DaliurenPage, name: "大六壬", input: /判断侧重/, module: /四课三传/ },
  { Page: JianxiangPage, name: "见相", input: /独立同意/, module: /结构化观察与证据充足度/ },
  { Page: HecanPage, name: "命盘合参", input: /至少选择两术/, module: /互证、分歧与缺失/ },
  { Page: WenshiPage, name: "问事合参", input: /同一问题与时空/, module: /六爻、大六壬与奇门/ },
];

afterEach(cleanup);

describe("primary product route contract", () => {
  it.each(routes)("$name renders a real task surface instead of a placeholder", ({ Page, name, input, module }) => {
    render(<Page />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("form", { name: `${name}任务输入` })).toBeVisible();
    expect(screen.getAllByText(input).length).toBeGreaterThan(0);
    expect(screen.getAllByText(module).length).toBeGreaterThan(0);
    const runtimeConnected = ["八字", "紫微", "七政", "六爻", "奇门", "大六壬", "命盘合参", "问事合参"].includes(name);
    expect(document.querySelector(`[data-state="${runtimeConnected ? "success" : "unavailable"}"]`)).not.toBeNull();
    expect(screen.getAllByText(/输入确认/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/工作台/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/报告与追问/).length).toBeGreaterThan(0);
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
    render(<BaziPage />);

    await user.click(screen.getByRole("button", { name: "检查输入" }));
    expect(await screen.findByText("请填写受测对象")).toBeVisible();

    await user.type(screen.getByLabelText("受测对象"), "本人");
    await user.type(screen.getByLabelText("出生日期"), "1990-05-06");
    await user.type(screen.getByLabelText("出生时间"), "08:30");
    await user.type(screen.getByLabelText("出生地点"), "江苏省常州市金坛区");
    await user.selectOptions(screen.getByLabelText("性别"), "male");
    await user.click(screen.getByRole("button", { name: "检查输入" }));

    expect(await screen.findByRole("heading", { name: "确认八字输入" })).toBeVisible();
    expect(screen.getByText("江苏省常州市金坛区")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "确认并生成盘面" }));

    expect(mockStartPreviewReading).toHaveBeenCalledWith(
      expect.objectContaining({ profile_version_id: "profile-version-1" }),
      expect.any(String),
    );
    expect(mockRouterPush).toHaveBeenCalledWith("/app/readings/reading-1");
  });
});
