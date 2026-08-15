import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppPageHeader } from "@/components/app-page-header";
import { FortuneFlow } from "@/components/fortune-flow";
import { LiuyaoForm } from "@/components/liuyao-form";
import { ProfileForm } from "@/components/profile-form";

vi.mock("next/navigation", () => ({
  usePathname: () => "/app",
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

const api = vi.hoisted(() => ({
  getCsrfToken: vi.fn(),
  listProfiles: vi.fn(),
  createProfileDraft: vi.fn(),
  confirmProfileDraft: vi.fn(),
  startTodayReading: vi.fn(),
  startWeekReading: vi.fn(),
  startLiuyaoReading: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  ...api,
}));

const CSRF = "csrf-token-with-at-least-thirty-two-characters";

const PROFILE = {
  profile_id: "11111111-1111-4111-8111-111111111111",
  profile_version_id: "22222222-2222-4222-8222-222222222222",
  subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
  version: 1,
  created_at: "2026-08-09T12:00:00Z",
};

beforeEach(() => {
  api.getCsrfToken.mockReset();
  api.listProfiles.mockReset();
  api.createProfileDraft.mockReset();
  api.confirmProfileDraft.mockReset();
  api.startTodayReading.mockReset();
  api.startWeekReading.mockReset();
  api.startLiuyaoReading.mockReset();

  api.getCsrfToken.mockResolvedValue(CSRF);
  api.listProfiles.mockResolvedValue({ profiles: [] });
  api.createProfileDraft.mockResolvedValue({
    draft_id: "55555555-5555-4555-8555-555555555555",
    status: "draft",
  });
  api.confirmProfileDraft.mockResolvedValue({
    profile_id: PROFILE.profile_id,
    profile_version_id: PROFILE.profile_version_id,
    subject_ref: PROFILE.subject_ref,
    version: 1,
    created_at: "2026-08-09T12:00:00Z",
  });
});

describe("AppPageHeader", () => {
  it("renders a single h1 with description and meta, with no eyebrow above the heading", () => {
    const { container } = render(
      <AppPageHeader
        title="今日解读"
        description="描述正文"
        meta={<span>私人页面 · no-store</span>}
      />,
    );

    const header = container.querySelector("header");
    expect(header).not.toBeNull();
    const heading = screen.getByRole("heading", { level: 1, name: "今日解读" });
    expect(header?.firstElementChild).toBe(heading);
    expect(screen.getByText("描述正文")).toBeVisible();
    expect(screen.getByText("私人页面 · no-store")).toBeVisible();
    expect(screen.getAllByRole("heading")).toHaveLength(1);
  });
});

describe("disabled controls must explain why", () => {
  it("explains the lock while a profile is saving", async () => {
    const user = userEvent.setup();
    api.createProfileDraft.mockReturnValue(new Promise(() => {}));
    render(<ProfileForm />);

    await user.type(screen.getByLabelText("出生时间"), "1994-04-30T05:55");
    await user.type(screen.getByLabelText("出生地点"), "北京市朝阳区");
    await user.selectOptions(screen.getByLabelText("性别"), "female");
    await user.selectOptions(screen.getByLabelText("时间口径"), "civil");
    await user.selectOptions(screen.getByLabelText("子时口径"), "midnight");
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    expect(await screen.findByText(/已暂时锁定/)).toBeVisible();
    expect(screen.getByLabelText("出生时间")).toBeDisabled();
    expect(screen.getByLabelText("出生地点")).toBeDisabled();
    expect(screen.getByRole("button", { name: /保存档案/ })).toBeDisabled();
  });

  it("explains the lock while a liuyao reading is being submitted", async () => {
    const user = userEvent.setup();
    api.startLiuyaoReading.mockReturnValue(new Promise(() => {}));
    render(<LiuyaoForm />);

    await screen.findByLabelText("起卦时刻");
    await user.type(
      screen.getByLabelText("想清楚问什么"),
      "我是否应该在三个月内接受已经拿到的工作邀请？",
    );
    fireEvent.change(screen.getByLabelText("起卦时刻"), {
      target: { value: "2026-08-09T09:30" },
    });
    await user.type(screen.getByLabelText("起卦地点"), "上海市");
    const labels = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"];
    const castValues = ["6", "7", "8", "9", "6", "9"];
    for (let index = 0; index < labels.length; index += 1) {
      await user.selectOptions(screen.getByLabelText(labels[index]), castValues[index]);
    }
    await user.click(screen.getByRole("button", { name: /开始解读/ }));

    expect(await screen.findByText(/已暂时锁定/)).toBeVisible();
    expect(screen.getByLabelText("想清楚问什么")).toBeDisabled();
    expect(screen.getByRole("button", { name: /开始解读/ })).toBeDisabled();
  });

  it("explains the lock while a fortune reading is starting", async () => {
    const user = userEvent.setup();
    api.listProfiles.mockResolvedValue({ profiles: [PROFILE] });
    api.startTodayReading.mockReturnValue(new Promise(() => {}));
    render(<FortuneFlow mode="today" />);

    const select = await screen.findByLabelText("档案版本");
    await user.selectOptions(select, PROFILE.profile_version_id);
    await user.click(screen.getByRole("button", { name: /开始今日解读/ }));

    await waitFor(() =>
      expect(screen.getByText(/已暂时锁定/)).toBeVisible(),
    );
    expect(select).toBeDisabled();
    expect(screen.getByRole("button", { name: /开始今日解读/ })).toBeDisabled();
  });
});
