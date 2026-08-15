import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccountProfilesPage from "@/app/account/profiles/page";
import AccountProfileDetailPage from "@/app/account/profiles/[profileId]/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  getCsrfToken: vi.fn(),
  listProfiles: vi.fn(),
  listProfileVersions: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
  getCsrfToken: api.getCsrfToken,
  listProfiles: api.listProfiles,
  listProfileVersions: api.listProfileVersions,
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
          created_at: "2026-08-10T01:00:00Z",
        },
      ],
    });

    render(<AccountProfilesPage />);

    expect(await screen.findByRole("heading", { name: "已保存的档案版本" })).toBeVisible();
    expect(screen.getByText(/档案 3/)).toBeVisible();
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
});
