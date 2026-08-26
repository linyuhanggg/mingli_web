import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProfileForm } from "@/components/profile-form";
import { IANA_TIME_ZONES } from "@/lib/iana-timezones";


const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: routerPush,
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

const api = vi.hoisted(() => ({
  appendProfileVersion: vi.fn(),
  createProfileDraft: vi.fn(),
  confirmProfileDraft: vi.fn(),
  listProfiles: vi.fn(),
}));

vi.mock("@/lib/api", () => api);


beforeEach(() => {
  routerPush.mockReset();
  api.appendProfileVersion.mockReset();
  api.createProfileDraft.mockReset();
  api.confirmProfileDraft.mockReset();
  api.listProfiles.mockReset();
  api.listProfiles.mockResolvedValue({ profiles: [] });
  api.createProfileDraft.mockResolvedValue({
    draft_id: "55555555-5555-4555-8555-555555555555",
    status: "draft",
  });
  api.confirmProfileDraft.mockResolvedValue({
    profile_id: "11111111-1111-4111-8111-111111111111",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
    version: 1,
    created_at: "2026-08-09T12:00:00Z",
  });
  api.appendProfileVersion.mockResolvedValue({
    profile_id: "11111111-1111-4111-8111-111111111111",
    profile_version_id: "33333333-3333-4333-8333-333333333333",
    subject_ref: "profile-version:33333333-3333-4333-8333-333333333333",
    version: 2,
    created_at: "2026-08-10T12:00:00Z",
  });
});

describe("ProfileForm", () => {
  it("does not silently choose values that change the algorithm", () => {
    render(<ProfileForm />);

    expect(screen.getByRole("heading", { name: "1. 出生事实" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "2. 计算口径" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "3. 提交前核对" })).toBeVisible();
    expect(screen.getByLabelText("性别")).toHaveValue("");
    expect(screen.getByLabelText("时间口径")).toHaveValue("");
    expect(screen.getByLabelText("子时口径")).toHaveValue("");
  });

  it("reveals coordinate calibration only for true solar time", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    expect(screen.queryByLabelText("经度（可选）")).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("时间口径"), "solar");
    expect(screen.getByLabelText("经度（可选）")).toBeVisible();
    expect(screen.getByLabelText("纬度（可选）")).toBeVisible();

    await user.selectOptions(screen.getByLabelText("时间口径"), "civil");
    expect(screen.queryByLabelText("经度（可选）")).not.toBeInTheDocument();
  });

  it("uses modern canonical IANA names instead of deprecated aliases", () => {
    for (const canonical of [
      "Asia/Kolkata",
      "Asia/Yangon",
      "Asia/Ho_Chi_Minh",
      "Europe/Kyiv",
    ]) {
      expect(IANA_TIME_ZONES).toContain(canonical);
    }
    for (const deprecated of [
      "Asia/Calcutta",
      "Asia/Rangoon",
      "Asia/Saigon",
      "Europe/Kiev",
    ]) {
      expect(IANA_TIME_ZONES).not.toContain(deprecated);
    }
  });

  it("offers the complete searchable IANA list and rejects values outside it", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    const timezone = screen.getByLabelText("出生时区");
    expect(timezone).toHaveAttribute("list", "profile-timezone-options");
    expect(timezone).toHaveAttribute(
      "placeholder",
      "例如 Asia/Shanghai，请从列表选择",
    );
    expect(
      screen.getByText("请输入并从列表选择出生城市对应的 IANA 时区；界面不会读取设备时区。"),
    ).toBeVisible();
    expect(
      document.querySelectorAll("#profile-timezone-options option").length,
    ).toBeGreaterThan(300);
    expect(
      document.querySelector(
        '#profile-timezone-options option[value="America/New_York"]',
      ),
    ).not.toBeNull();

    await user.clear(timezone);
    await user.type(timezone, "Foo/Bar");
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    expect(await screen.findByText("请选择列表中的有效 IANA 时区")).toBeVisible();
    expect(api.createProfileDraft).not.toHaveBeenCalled();
    expect(api.confirmProfileDraft).not.toHaveBeenCalled();
  });

  it("validates required and malformed birth datetime with accessible errors and focus", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    const birthInput = screen.getByLabelText("出生时间");
    await waitFor(() => expect(birthInput).toHaveFocus());
    expect(birthInput).toHaveAttribute("aria-required", "true");
    expect(birthInput).toHaveAttribute("aria-invalid", "true");
    expect(await screen.findByText("请填写出生时间")).toBeVisible();
    expect(screen.getByText("请填写出生地点")).toBeVisible();

    fireEvent.change(birthInput, { target: { value: "not-a-date" } });
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    expect(await screen.findByText("请填写出生时间")).toBeVisible();
    expect(api.createProfileDraft).not.toHaveBeenCalled();
  });

  it("enforces the stricter location length cap before any API call", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    fireEvent.change(screen.getByLabelText("出生地点"), {
      target: { value: "长".repeat(81) },
    });
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    expect(await screen.findByText("地点最多 80 个字")).toBeVisible();
    expect(api.createProfileDraft).not.toHaveBeenCalled();
  });

  it("submits the confirmed profile through the real draft and confirm API", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    await user.type(screen.getByLabelText("出生时间"), "1994-04-30T05:55");
    await user.type(screen.getByLabelText("出生地点"), "北京市朝阳区");
    await user.selectOptions(screen.getByLabelText("性别"), "female");
    await user.selectOptions(screen.getByLabelText("时间口径"), "civil");
    await user.selectOptions(screen.getByLabelText("子时口径"), "midnight");
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    await waitFor(() =>
      expect(routerPush).toHaveBeenCalledWith("/app/profiles?created=1"),
    );
    expect(api.createProfileDraft).toHaveBeenCalledWith("本人");
    expect(api.confirmProfileDraft).toHaveBeenCalledWith(
      "55555555-5555-4555-8555-555555555555",
      expect.objectContaining({
        timezone: "Asia/Shanghai",
        location: "北京市朝阳区",
        gender: "female",
        time_basis_policy: "civil",
        zi_hour_policy: "midnight",
      }),
    );
  });

  it("presents name conflicts as primary update, grouped save-as, and ghost cancel", async () => {
    api.listProfiles.mockResolvedValue({
      profiles: [
        {
          profile_id: "11111111-1111-4111-8111-111111111111",
          profile_version_id: "22222222-2222-4222-8222-222222222222",
          subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
          version: 1,
          display_name: "同名档案",
          birth_date: "1994-04-30",
          created_at: "2026-08-09T12:00:00Z",
        },
      ],
    });
    const user = userEvent.setup();
    render(<ProfileForm />);

    await user.clear(screen.getByLabelText("档案名称"));
    await user.type(screen.getByLabelText("档案名称"), "同名档案");
    await user.type(screen.getByLabelText("出生时间"), "1994-04-30T05:55");
    await user.type(screen.getByLabelText("出生地点"), "北京市朝阳区");
    await user.selectOptions(screen.getByLabelText("性别"), "female");
    await user.selectOptions(screen.getByLabelText("时间口径"), "civil");
    await user.selectOptions(screen.getByLabelText("子时口径"), "midnight");
    const submit = screen.getByRole("button", { name: "保存档案" });
    await user.click(submit);

    const dialog = await screen.findByRole("dialog", { name: "已有同名档案“同名档案”" });
    const update = screen.getByRole("button", { name: "更新“同名档案”" });
    const saveAsGroup = screen.getByRole("group", { name: "另存为新档案" });
    const saveAs = screen.getByRole("button", { name: "另存为新档案" });
    const cancel = screen.getByRole("button", { name: "取消" });

    expect(dialog).toBeVisible();
    await waitFor(() => expect(update).toHaveFocus());
    expect(update).toHaveAttribute("data-variant", "primary");
    expect(saveAsGroup).toHaveAttribute("data-variant", "secondary-card");
    expect(screen.getByLabelText("新档案名称")).toHaveValue("同名档案 2");
    expect(saveAs).toHaveAttribute("data-variant", "secondary");
    expect(cancel).toHaveAttribute("data-variant", "ghost");
    expect(cancel.getAttribute("style")).toContain("min-height: 2.75rem");

    await user.click(cancel);
    await waitFor(() => expect(dialog).not.toBeInTheDocument());
    expect(submit).toHaveFocus();
    expect(api.appendProfileVersion).not.toHaveBeenCalled();
    expect(api.createProfileDraft).not.toHaveBeenCalled();
  });

  it("restates birth basis choices live before submit", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    const summary = screen.getByRole("region", {
      name: "提交前确认出生口径",
    });
    expect(summary).toHaveTextContent("最终以服务端口径为准");
    expect(summary).toHaveTextContent("未填写出生时间");
    expect(summary).toHaveTextContent("时辰无法确认");

    await user.type(screen.getByLabelText("出生时间"), "1994-04-30T05:55");
    await user.type(screen.getByLabelText("出生地点"), "北京市朝阳区");
    await user.selectOptions(screen.getByLabelText("时间口径"), "solar");

    expect(summary).toHaveTextContent("1994-04-30T05:55");
    expect(summary).toHaveTextContent("Asia/Shanghai");
    expect(summary).toHaveTextContent("真太阳时");
    expect(summary).toHaveTextContent("前端只预览这一选择");
    expect(summary).toHaveTextContent("尚未填写经度");
    expect(summary).not.toHaveTextContent(/已填写经度/);

    await user.type(screen.getByLabelText("经度（可选）"), "120.1");
    expect(summary).toHaveTextContent(/已填写经度 120\.1°/);
  });
});
