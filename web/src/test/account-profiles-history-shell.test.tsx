import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccountProfilesPage from "@/app/account/profiles/page";
import AccountProfileDetailPage from "@/app/account/profiles/[profileId]/page";
import AccountHistoryPage from "@/app/account/history/page";
import AccountHistoryDetailPage from "@/app/account/history/[rootId]/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  getCsrfToken: vi.fn(),
  listProfiles: vi.fn(),
  listProfileVersions: vi.fn(),
  listAccountHistory: vi.fn(),
  listReadings: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
  getCsrfToken: api.getCsrfToken,
  listProfiles: api.listProfiles,
  listProfileVersions: api.listProfileVersions,
  listAccountHistory: api.listAccountHistory,
  listReadings: api.listReadings,
}));

const profileId = "11111111-1111-4111-8111-111111111111";
const rootId = "44444444-4444-4444-8444-444444444444";

beforeEach(() => {
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.getCsrfToken.mockReset();
  api.getCsrfToken.mockResolvedValue("csrf-token-with-at-least-thirty-two-characters");
  api.listProfiles.mockReset();
  api.listProfiles.mockResolvedValue({ profiles: [] });
  api.listProfileVersions.mockReset();
  api.listProfileVersions.mockResolvedValue({ versions: [] });
  api.listAccountHistory.mockReset();
  api.listAccountHistory.mockResolvedValue({ roots: [] });
  api.listReadings.mockReset();
  api.listReadings.mockResolvedValue({ readings: [] });
});

describe("account profiles + history four-page shell", () => {
  it("keeps /account/profiles on a 30px title without construction copy", () => {
    render(<AccountProfilesPage />);

    expect(screen.getByRole("heading", { level: 1, name: "档案" })).toBeVisible();
    expect(screen.getByText("查看已保存的出生档案。")).toBeVisible();
    expect(screen.queryByText(/受测人档案|ProfileVersion|授权边界|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
  });

  it("keeps /account/profiles/[profileId] on a 30px title without construction copy", async () => {
    const page = await AccountProfileDetailPage({
      params: Promise.resolve({ profileId }),
    });
    render(page);

    expect(screen.getByRole("heading", { level: 1, name: "档案" })).toBeVisible();
    expect(screen.getByText("查看这份档案的版本。")).toBeVisible();
    expect(screen.queryByText(/档案版本与授权边界|SubjectProfile|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
  });

  it("keeps /account/history on a 30px title without construction copy", () => {
    render(<AccountHistoryPage />);

    expect(screen.getByRole("heading", { level: 1, name: "历史" })).toBeVisible();
    expect(screen.getByText("查看你的任务和报告。")).toBeVisible();
    expect(screen.queryByText(/任务、版本与报告历史|ReadingRoot|ReadingVersion|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
  });

  it("keeps /account/history/[rootId] on a 30px title without construction copy", async () => {
    const page = await AccountHistoryDetailPage({
      params: Promise.resolve({ rootId }),
    });
    render(page);

    expect(screen.getByRole("heading", { level: 1, name: "历史详情" })).toBeVisible();
    expect(screen.getByText("查看这份任务的版本。")).toBeVisible();
    expect(screen.queryByText(/一份任务的版本与交付记录|ReadingVersion|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
  });

  it("locks the shared header to --font-size-page", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/account-section-shell.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.header h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
  });

  it("does not put construction chrome on the four production files", () => {
    for (const file of [
      "src/app/account/profiles/page.tsx",
      "src/app/account/profiles/[profileId]/page.tsx",
      "src/app/account/history/page.tsx",
      "src/app/account/history/[rootId]/page.tsx",
      "src/components/surfaces/account-profiles-surface.tsx",
      "src/components/surfaces/account-profile-detail-surface.tsx",
      "src/components/surfaces/account-history-surface.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/development_code|调试码/);
      expect(source).not.toMatch(/SecondarySurfaceFrame|authGrid|§10|§6\.2/);
      expect(source).not.toMatch(/AppPageHeader/);
    }
  });
});
