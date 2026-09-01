import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProfileArchive as ProfilesPage } from "@/components/profile-archive";
import { ReadingHistory as ReadingsPage } from "@/components/reading-history";
import { ApiError } from "@/lib/api";


const api = vi.hoisted(() => ({
  listProfiles: vi.fn(),
  listReadings: vi.fn(),
  startPreviewReading: vi.fn(),
  updateProfileDisplayName: vi.fn(),
}));

const navigation = vi.hoisted(() => ({
  routerPush: vi.fn(),
  searchParams: new URLSearchParams(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: navigation.routerPush,
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => navigation.searchParams,
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listProfiles: api.listProfiles,
    listReadings: api.listReadings,
    startPreviewReading: api.startPreviewReading,
    updateProfileDisplayName: api.updateProfileDisplayName,
  };
});


const profileVersionId = "22222222-2222-4222-8222-222222222222";
const readingVersionId = "33333333-3333-4333-8333-333333333333";

function profile(overrides: Record<string, unknown> = {}) {
  return {
    profile_id: "11111111-1111-4111-8111-111111111111",
    profile_version_id: profileVersionId,
    subject_ref: `profile-version:${profileVersionId}`,
    version: 1,
    created_at: "2026-08-09T12:00:00Z",
    ...overrides,
  };
}

function reading(overrides: Record<string, unknown> = {}) {
  return {
    reading_version_id: readingVersionId,
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: profileVersionId,
    capability_id: "fortune",
    version: 1,
    status: "accepted",
    object_id: "near_time_personal",
    dimension_ids: ["overview"],
    horizon: { kind_id: "day", start: "2026-08-10", end: "2026-08-10" },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-10T01:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  api.listProfiles.mockReset();
  api.listReadings.mockReset();
  api.startPreviewReading.mockReset();
  api.updateProfileDisplayName.mockReset();
  navigation.routerPush.mockReset();
  navigation.searchParams = new URLSearchParams();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ProfileArchive", () => {
  it("shows the loading state, then the saved profile versions", async () => {
    api.listProfiles.mockResolvedValue({
      profiles: [
        profile(),
        profile({
          profile_version_id: "66666666-6666-4666-8666-666666666666",
          version: 2,
        }),
      ],
    });

    render(<ProfilesPage />);

    const loader = screen.getByRole("status", { name: "正在读取档案…" });
    expect(loader).toBeInTheDocument();
    expect(loader).toHaveAttribute("data-loader-variant", "dots");
    expect(loader.closest('[aria-busy="true"]')).not.toBeNull();

    await waitFor(() =>
      expect(screen.getAllByText(/档案 1/).length).toBeGreaterThan(0),
    );
    expect(screen.getAllByText(/档案 1/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/档案 2/).length).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("button", { name: "查看事业主题概览" }).length,
    ).toBe(2);
    expect(
      screen.getByRole("link", { name: "选择档案并查看事业主题" }),
    ).toHaveAttribute(
      "href",
      "/app/bazi",
    );
    expect(api.listProfiles).toHaveBeenCalledTimes(1);
    expect(screen.getAllByRole("button", { name: "重命名" }).length).toBe(2);
  });

  it("lets a guest rename a saved profile", async () => {
    api.listProfiles.mockResolvedValue({
      profiles: [profile({ display_name: "档案 · 1992-07-08" })],
    });
    let resolveRename!: (next: ReturnType<typeof profile>) => void;
    const renameRequest = new Promise<ReturnType<typeof profile>>((resolve) => {
      resolveRename = resolve;
    });
    api.updateProfileDisplayName.mockReturnValue(renameRequest);

    render(<ProfilesPage />);
    fireEvent.click(await screen.findByRole("button", { name: "重命名" }));
    fireEvent.change(screen.getByLabelText("档案名称"), {
      target: { value: "游客重命名档案" },
    });
    const saveButton = screen.getByRole("button", { name: "保存名称" });
    fireEvent.click(saveButton);

    await waitFor(() =>
      expect(api.updateProfileDisplayName).toHaveBeenCalledWith(
        "11111111-1111-4111-8111-111111111111",
        "游客重命名档案",
      ),
    );
    const savingButton = screen.getByRole("button", { name: "正在保存名称…" });
    expect(savingButton).toBeVisible();
    expect(savingButton).toHaveAttribute("aria-busy", "true");
    expect(savingButton.closest('form[aria-busy="true"]')).not.toBeNull();
    expect(screen.getByLabelText("档案名称")).toBeDisabled();
    expect(savingButton).toBeDisabled();
    expect(screen.getByRole("button", { name: "取消" })).toBeDisabled();

    fireEvent.click(savingButton);
    expect(api.updateProfileDisplayName).toHaveBeenCalledTimes(1);

    resolveRename(profile({ display_name: "游客重命名档案" }));

    expect(await screen.findByRole("button", { name: "名称已保存" })).toBeVisible();
    await waitFor(() => {
      expect(screen.getByText("游客重命名档案")).toBeVisible();
      expect(screen.getByRole("button", { name: "重命名" })).toHaveFocus();
    });
  });

  it("links rename failures to the input and returns the stateful button to idle", async () => {
    api.listProfiles.mockResolvedValue({
      profiles: [profile({ display_name: "旧名称" })],
    });
    api.updateProfileDisplayName.mockRejectedValue(new Error("名称暂时无法保存"));

    render(<ProfilesPage />);
    fireEvent.click(await screen.findByRole("button", { name: "重命名" }));
    const input = screen.getByLabelText("档案名称");
    fireEvent.change(input, { target: { value: "新名称" } });
    fireEvent.click(screen.getByRole("button", { name: "保存名称" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("名称暂时无法保存");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input.getAttribute("aria-describedby")).toBeTruthy();
    expect(input).toHaveFocus();
    expect(screen.getByRole("button", { name: "保存失败" })).toBeEnabled();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "保存名称" })).toBeEnabled(),
    );
  });

  it("uses a width-stable stateful button before opening the supported archive preview", async () => {
    api.listProfiles.mockResolvedValue({ profiles: [profile()] });
    let resolveStart!: (next: { reading_version_id: string }) => void;
    api.startPreviewReading.mockReturnValue(new Promise((resolve) => {
      resolveStart = resolve;
    }));

    render(<ProfilesPage />);
    const startButton = await screen.findByRole("button", {
      name: "查看事业主题概览",
    });
    fireEvent.click(startButton);

    const loadingButton = await screen.findByRole("button", {
      name: "正在启动事业主题…",
    });
    expect(loadingButton).toBeDisabled();
    expect(loadingButton).toHaveAttribute("aria-busy", "true");
    fireEvent.click(loadingButton);
    expect(api.startPreviewReading).toHaveBeenCalledTimes(1);
    expect(api.startPreviewReading).toHaveBeenCalledWith(
      expect.objectContaining({
        profile_version_id: profileVersionId,
        query: "查看这个档案的事业与工作主题",
        dimension_ids: ["career"],
      }),
      expect.any(String),
    );

    resolveStart({ reading_version_id: readingVersionId });
    expect(
      await screen.findByRole("button", { name: "事业主题已启动" }),
    ).toBeDisabled();
    await waitFor(() =>
      expect(navigation.routerPush).toHaveBeenCalledWith(
        `/app/readings/${readingVersionId}`,
      ),
    );
  });

  it("shows a one-shot button error while preserving the retryable Status message", async () => {
    api.listProfiles.mockResolvedValue({ profiles: [profile()] });
    api.startPreviewReading.mockRejectedValue(new Error("事业主题暂时不可用"));

    render(<ProfilesPage />);
    fireEvent.click(
      await screen.findByRole("button", { name: "查看事业主题概览" }),
    );

    expect(
      await screen.findByRole("alert", { name: "无法启动事业主题概览" }),
    ).toHaveTextContent("事业主题暂时不可用");
    expect(screen.getByRole("button", { name: "启动失败" })).toBeEnabled();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "查看事业主题概览" }),
      ).toBeEnabled(),
    );
  });

  it("keeps profile-dependent flows out of the empty archive state", async () => {
    api.listProfiles.mockResolvedValue({ profiles: [] });

    render(<ProfilesPage />);

    await waitFor(() =>
      expect(
        screen.getByRole("status", { name: "还没有已保存的档案" }),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("link", { name: "开始建立档案" }),
    ).toHaveAttribute("href", "/account/profiles/new");
    expect(screen.queryByRole("link", { name: "发起今日解读" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "发起近七日解读" })).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "直接一事一问 · 六爻" }),
    ).toHaveAttribute("href", "/app/ask/liuyao");
  });

  it("surfaces load failures and recovers after retry", async () => {
    api.listProfiles
      .mockRejectedValueOnce(new Error("服务暂时不可用，请稍后重试"))
      .mockResolvedValueOnce({ profiles: [profile()] });

    render(<ProfilesPage />);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("无法读取档案")).toBeInTheDocument();
    expect(
      within(alert).getByText("服务暂时不可用，请稍后重试"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重试" }));

    await waitFor(() =>
      expect(screen.getAllByText(/档案 1/).length).toBeGreaterThan(0),
    );
    expect(api.listProfiles).toHaveBeenCalledTimes(2);
  });

  it("treats a 401 as an expired session with a re-login link instead of only retry", async () => {
    api.listProfiles.mockRejectedValue(
      new ApiError("Authentication required", 401),
    );

    render(<ProfilesPage />);

    expect(await screen.findByText("登录已过期")).toBeVisible();
    expect(screen.getByRole("link", { name: "重新登录" })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    expect(screen.queryByRole("button", { name: "重试" })).not.toBeInTheDocument();
  });
});

describe("ReadingHistory", () => {
  it("shows the loading state, then lists kind, status and time per reading", async () => {
    api.listReadings.mockResolvedValue({
      readings: [
        reading(),
        reading({
          reading_version_id: "55555555-5555-4555-8555-555555555555",
          capability_id: "liuyao",
          version: 2,
          status: "waiting_input",
        }),
      ],
    });

    render(<ReadingsPage />);

    expect(screen.getByRole("status", { name: "正在读取历史…" })).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "最近解读版本" })).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("link", { name: /日运与周运/ }),
    ).toHaveAttribute(
      "href",
      `/account/history/${readingVersionId}`,
    );
    expect(
      screen.getByRole("link", { name: /六爻/ }),
    ).toHaveAttribute(
      "href",
      "/account/history/55555555-5555-4555-8555-555555555555",
    );
    expect(screen.getByText("已交付")).toBeInTheDocument();
    expect(screen.getByText("等待输入")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /2026/ })).toHaveLength(2);
    expect(api.listReadings).toHaveBeenCalledTimes(1);
  });

  it("offers the empty state with a single start action", async () => {
    api.listReadings.mockResolvedValue({ readings: [] });

    render(<ReadingsPage />);

    await waitFor(() =>
      expect(
        screen.getByRole("status", { name: "还没有可显示的解读" }),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("link", { name: "去排盘" }),
    ).toHaveAttribute("href", "/bazi");
  });

  it("surfaces load failures and recovers after retry", async () => {
    api.listReadings
      .mockRejectedValueOnce(new Error("服务暂时不可用，请稍后重试"))
      .mockResolvedValueOnce({ readings: [reading()] });

    render(<ReadingsPage />);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("无法读取历史")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重试" }));

    await waitFor(() =>
      expect(screen.getByRole("link", { name: /日运与周运/ })).toBeInTheDocument(),
    );
    expect(api.listReadings).toHaveBeenCalledTimes(2);
  });

  it("treats a 401 as an expired session with a re-login link instead of only retry", async () => {
    api.listReadings.mockRejectedValue(
      new ApiError("Authentication required", 401),
    );

    render(<ReadingsPage />);

    expect(await screen.findByText("登录已过期")).toBeVisible();
    expect(screen.getByRole("link", { name: "重新登录" })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    expect(screen.queryByRole("button", { name: "重试" })).not.toBeInTheDocument();
  });

  it("lists only public fields and never leaks prior_answer, input_request or tokens", async () => {
    api.listReadings.mockResolvedValue({
      readings: [
        reading({
          prior_answer: "不应出现在历史列表的追问上下文",
          input_request: {
            requirements: [
              {
                any_of: [
                  {
                    id: "state-token",
                    label: "内部状态令牌",
                    type_id: "text",
                    description: "密文",
                    choices: [],
                  },
                ],
              },
            ],
          },
        }),
      ],
    });

    render(<ReadingsPage />);

    await waitFor(() =>
      expect(screen.getByRole("link", { name: /日运与周运/ })).toBeInTheDocument(),
    );
    expect(screen.queryByText(/不应出现在历史列表/)).not.toBeInTheDocument();
    expect(screen.queryByText("内部状态令牌")).not.toBeInTheDocument();
    expect(screen.queryByText("密文")).not.toBeInTheDocument();
  });

  it("renders up to the server cap of fifty readings without trimming", async () => {
    const readings = Array.from({ length: 50 }, (_, index) =>
      reading({
        reading_version_id: `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`,
      }),
    );
    api.listReadings.mockResolvedValue({ readings });

    render(<ReadingsPage />);

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "最近解读版本" })).toBeInTheDocument(),
    );
    expect(screen.getAllByRole("link")).toHaveLength(50);
  });
});
