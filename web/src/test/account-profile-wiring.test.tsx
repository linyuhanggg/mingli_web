import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccountProfilesPage from "@/app/account/profiles/page";
import AccountProfileDetailPage from "@/app/account/profiles/[profileId]/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  getCsrfToken: vi.fn(),
  listProfiles: vi.fn(),
  listProfileVersions: vi.fn(),
  updateProfileDisplayName: vi.fn(),
}));

const navigationState = vi.hoisted(() => ({ search: "" }));

function memoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, String(value)),
  };
}

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(navigationState.search),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
  getCsrfToken: api.getCsrfToken,
  listProfiles: api.listProfiles,
  listProfileVersions: api.listProfileVersions,
  updateProfileDisplayName: api.updateProfileDisplayName,
}));

const account = {
  user_id: "4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41",
  identities: [
    {
      id: "8d2f1a4b-6c3e-4d9f-8a5b-2e7c4f1d9a3b",
      provider: "email" as const,
      masked_destination: "q***@example.com",
      verified_at: "2026-08-01T00:00:00Z",
    },
  ],
};

beforeEach(() => {
  navigationState.search = "";
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: memoryStorage(),
  });
  Object.defineProperty(window, "sessionStorage", {
    configurable: true,
    value: memoryStorage(),
  });
  window.localStorage.clear();
  window.sessionStorage.clear();
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.getCsrfToken.mockReset();
  api.getCsrfToken.mockResolvedValue(
    "csrf-token-with-at-least-thirty-two-characters",
  );
  api.listProfiles.mockReset();
  api.listProfiles.mockResolvedValue({ profiles: [] });
  api.listProfileVersions.mockReset();
  api.listProfileVersions.mockResolvedValue({ versions: [] });
  api.updateProfileDisplayName.mockReset();
});

describe("account profile route wiring", () => {
  it("keeps profiles private for signed-out users", async () => {
    render(<AccountProfilesPage />);

    expect(await screen.findByRole("status", { name: "需要登录" })).toBeVisible();
    expect(screen.getByRole("link", { name: "前往登录" })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    expect(api.listProfiles).not.toHaveBeenCalled();
  });

  it("shows immutable server-returned profile versions after login", async () => {
    api.getAccount.mockResolvedValue(account);
    api.listProfiles.mockResolvedValue({
      profiles: [
        {
          profile_id: "11111111-1111-4111-8111-111111111111",
          profile_version_id: "22222222-2222-4222-8222-222222222222",
          subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
          version: 3,
          display_name: "母亲",
          birth_date: "1965-02-03",
          created_at: "2026-08-10T01:00:00Z",
        },
      ],
    });

    render(<AccountProfilesPage />);

    expect(await screen.findByRole("heading", { name: "已保存的档案" })).toBeVisible();
    expect(screen.getByText("母亲")).toBeVisible();
    expect(screen.getByText(/1965-02-03 · v3 · 更新于/)).toBeVisible();
    expect(screen.getByRole("link", { name: "新建档案版本" })).toHaveAttribute(
      "href",
      "/app/profile/new",
    );
  });

  it("shows only safe version metadata on the owned profile detail route", async () => {
    api.getAccount.mockResolvedValue(account);
    api.listProfileVersions.mockResolvedValue({
      versions: [
        {
          profile_id: "11111111-1111-4111-8111-111111111111",
          profile_version_id: "22222222-2222-4222-8222-222222222222",
          subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
          version: 3,
          display_name: "母亲",
          birth_date: "1965-02-03",
          created_at: "2026-08-10T01:00:00Z",
        },
      ],
    });

    const page = await AccountProfileDetailPage({
      params: Promise.resolve({ profileId: "11111111-1111-4111-8111-111111111111" }),
    });
    render(page);

    expect(await screen.findByRole("heading", { name: "档案版本历史" })).toBeVisible();
    expect(screen.getByText("档案 v3")).toBeVisible();
    expect(screen.queryByText(/出生时间|出生地点|密文|nonce/)).not.toBeInTheDocument();
    expect(api.listProfileVersions).toHaveBeenCalledWith(
      "11111111-1111-4111-8111-111111111111",
    );
  });

  it("uses the server name after fresh storage and persists rename with PATCH", async () => {
    const profile = {
      profile_id: "11111111-1111-4111-8111-111111111111",
      profile_version_id: "22222222-2222-4222-8222-222222222222",
      subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
      version: 3,
      display_name: "母亲",
      birth_date: "1965-02-03",
      created_at: "2026-08-10T01:00:00Z",
    };
    window.localStorage.setItem(
      "mingli.profile-display-metadata.v1",
      JSON.stringify({ [profile.profile_id]: { name: "过期本地名称" } }),
    );
    api.getAccount.mockResolvedValue(account);
    api.listProfiles.mockResolvedValue({ profiles: [profile] });
    api.updateProfileDisplayName.mockResolvedValue({
      ...profile,
      display_name: "妈妈",
    });
    const user = userEvent.setup();

    render(<AccountProfilesPage />);

    expect(await screen.findByText("母亲")).toBeVisible();
    expect(screen.queryByText("过期本地名称")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "重命名" }));
    const input = screen.getByLabelText("档案名称");
    await user.clear(input);
    await user.type(input, "妈妈");
    await user.click(screen.getByRole("button", { name: "保存名称" }));

    await waitFor(() =>
      expect(api.updateProfileDisplayName).toHaveBeenCalledWith(
        profile.profile_id,
        "妈妈",
      ),
    );
    expect(await screen.findByText("妈妈")).toBeVisible();
  });

  it("shows the saved-success banner from session flash on a fresh list", async () => {
    navigationState.search = "created=1";
    window.sessionStorage.setItem(
      "mingli.profile-saved-flash.v2",
      JSON.stringify({
        name: "母亲",
        profile_id: "11111111-1111-4111-8111-111111111111",
      }),
    );
    api.getAccount.mockResolvedValue(account);
    api.listProfiles.mockResolvedValue({
      profiles: [
        {
          profile_id: "11111111-1111-4111-8111-111111111111",
          profile_version_id: "22222222-2222-4222-8222-222222222222",
          subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
          version: 1,
          display_name: "母亲",
          birth_date: "1965-02-03",
          created_at: "2026-08-10T01:00:00Z",
        },
      ],
    });

    render(<AccountProfilesPage />);

    expect(await screen.findByRole("status", { name: "“母亲”已保存" })).toBeVisible();
  });

  it("syncs the one-time saved banner from the server PATCH response", async () => {
    navigationState.search = "created=1";
    const profile = {
      profile_id: "11111111-1111-4111-8111-111111111111",
      profile_version_id: "22222222-2222-4222-8222-222222222222",
      subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
      version: 1,
      display_name: "我自己 · 1990",
      birth_date: "1990-05-06",
      created_at: "2026-08-10T01:00:00Z",
    };
    window.sessionStorage.setItem(
      "mingli.profile-saved-flash.v2",
      JSON.stringify({ name: profile.display_name, profile_id: profile.profile_id }),
    );
    api.getAccount.mockResolvedValue(account);
    api.listProfiles.mockResolvedValue({ profiles: [profile] });
    api.updateProfileDisplayName.mockResolvedValue({
      ...profile,
      display_name: "我的测试档案",
    });
    const user = userEvent.setup();

    render(<AccountProfilesPage />);

    expect(
      await screen.findByRole("status", { name: "“我自己 · 1990”已保存" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "重命名" }));
    const input = screen.getByLabelText("档案名称");
    await user.clear(input);
    await user.type(input, "客户端名称");
    await user.click(screen.getByRole("button", { name: "保存名称" }));

    expect(
      await screen.findByRole("status", { name: "“我的测试档案”已保存" }),
    ).toBeVisible();
    expect(
      screen.queryByRole("status", { name: "“我自己 · 1990”已保存" }),
    ).not.toBeInTheDocument();
  });

  it("clears the one-time saved banner when PATCH returns no usable name", async () => {
    navigationState.search = "created=1";
    const profile = {
      profile_id: "11111111-1111-4111-8111-111111111111",
      profile_version_id: "22222222-2222-4222-8222-222222222222",
      subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
      version: 1,
      display_name: "我自己 · 1990",
      birth_date: "1990-05-06",
      created_at: "2026-08-10T01:00:00Z",
    };
    window.sessionStorage.setItem(
      "mingli.profile-saved-flash.v2",
      JSON.stringify({ name: profile.display_name, profile_id: profile.profile_id }),
    );
    api.getAccount.mockResolvedValue(account);
    api.listProfiles.mockResolvedValue({ profiles: [profile] });
    api.updateProfileDisplayName.mockResolvedValue({
      ...profile,
      display_name: null,
    });
    const user = userEvent.setup();

    render(<AccountProfilesPage />);

    expect(
      await screen.findByRole("status", { name: "“我自己 · 1990”已保存" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "重命名" }));
    const input = screen.getByLabelText("档案名称");
    await user.clear(input);
    await user.type(input, "客户端名称");
    await user.click(screen.getByRole("button", { name: "保存名称" }));

    await waitFor(() =>
      expect(
        screen.queryByRole("status", { name: /已保存/ }),
      ).not.toBeInTheDocument(),
    );
  });
});
