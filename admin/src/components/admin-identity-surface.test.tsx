import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminIdentitySurface } from "@/components/admin-identity-surface";

describe("AdminIdentitySurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("renders user identity counts from the real admin response", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        users: [
          {
            id: "user-1",
            status: "active",
            created_at: "2026-08-14T01:00:00Z",
            identity_count: 1,
            consent_count: 2,
            subject_count: 1,
            active_session_count: 1,
          },
        ],
      },
    });

    render(<AdminIdentitySurface kind="users" role="support" />);

    expect(await screen.findByText("user-1")).toBeVisible();
    expect(screen.getByText("1 个身份 · 2 条同意 · 1 个 Subject")).toBeVisible();
    expect(screen.getByText("1 个活跃会话")).toBeVisible();
    expect(adminFetchMock).toHaveBeenCalledWith("/api/v1/admin/users");
  });

  it("shows an available full identity destination on user detail", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        id: "user-1",
        status: "active",
        created_at: "2026-08-14T01:00:00Z",
        identities: [
          {
            id: "identity-1",
            provider: "email",
            masked_destination: "u***@example.com",
            destination: "user@example.com",
            status: "active",
            verified_at: "2026-08-14T01:00:00Z",
            created_at: "2026-08-14T01:00:00Z",
          },
        ],
        consents: [],
        sessions: [],
        subjects: [],
      },
    });

    render(<AdminIdentitySurface kind="user-detail" id="user-1" role="support" />);

    expect(await screen.findByText("user@example.com")).toBeVisible();
    expect(screen.queryByText("u***@example.com")).not.toBeInTheDocument();
  });

  it("renders subject version authorization without encrypted payload material", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        id: "subject-1",
        owner_user_id: "user-1",
        label: "本人",
        status: "active",
        created_at: "2026-08-14T01:00:00Z",
        versions: [
          {
            id: "version-1",
            version: 1,
            created_at: "2026-08-14T01:01:00Z",
            authorization: {
              subject_type: "self",
              is_minor: false,
              authorization_confirmed: false,
              photo_authorization_confirmed: true,
              minor_guardian_confirmed: false,
              difference_acknowledged: true,
            },
            profile: {
              birth_datetime: "1994-04-30T05:55:00+08:00",
              timezone: "Asia/Shanghai",
              location: "北京市朝阳区",
              gender: "female",
              time_basis_policy: "civil",
              zi_hour_policy: "midnight",
              longitude: 116.4074,
              latitude: 39.9042,
              coordinate_source: "user_confirmed",
            },
          },
        ],
      },
    });

    render(<AdminIdentitySurface kind="subject-detail" id="subject-1" role="support" />);

    expect(await screen.findByText("版本 v1")).toBeVisible();
    expect(screen.getByText("本人授权")).toBeVisible();
    expect(screen.getByText("照片授权已确认")).toBeVisible();
    expect(screen.getByText("北京市朝阳区")).toBeVisible();
    expect(screen.getByText("Asia/Shanghai")).toBeVisible();
    expect(screen.queryByText("payload_ciphertext")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith("/api/v1/admin/subjects/subject-1");
  });

  it("keeps the identity surface honest and structurally available when the API is unavailable", async () => {
    adminFetchMock.mockResolvedValue({
      ok: false,
      status: 503,
      title: "身份平台暂不可用",
    });

    const { unmount } = render(
      <AdminIdentitySurface kind="user-detail" id="user-1" role="support" />,
    );
    expect(await screen.findByRole("heading", { name: "用户详情字段" })).toBeVisible();
    expect(screen.getByRole("status", { name: "身份平台暂不可用" })).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    unmount();

    render(<AdminIdentitySurface kind="users" role="support" />);
    expect(await screen.findByRole("status", { name: "身份平台暂不可用" })).toBeVisible();
    expect(screen.queryByRole("table", { name: "用户与身份" })).not.toBeInTheDocument();
  });
});
