import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccountHistoryPage from "@/app/account/history/page";
import AccountHistoryDetailPage from "@/app/account/history/[rootId]/page";
import { AccountSessionProvider } from "@/components/account-session-context";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  getCsrfToken: vi.fn(),
  listAccountHistory: vi.fn(),
  listReadings: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
  getCsrfToken: api.getCsrfToken,
  listAccountHistory: api.listAccountHistory,
  listReadings: api.listReadings,
}));

vi.mock("@/components/readings/reading-result", () => ({
  ReadingResult: ({ readingId }: { readingId: string }) => (
    <div role="region" aria-label="真实历史详情">
      ReadingResult:{readingId}
    </div>
  ),
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

const reading = {
  reading_version_id: "33333333-3333-4333-8333-333333333333",
  reading_root_id: "44444444-4444-4444-8444-444444444444",
  profile_version_id: "22222222-2222-4222-8222-222222222222",
  capability_id: "fortune",
  version: 2,
  status: "accepted" as const,
  object_id: "near_time_personal",
  dimension_ids: ["overview"],
  horizon: { kind_id: "day" as const, start: "2026-08-10", end: "2026-08-10" },
  prior_answer: null,
  input_request: null,
  created_at: "2026-08-10T01:00:00Z",
};

beforeEach(() => {
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.getCsrfToken.mockReset();
  api.getCsrfToken.mockResolvedValue(
    "csrf-token-with-at-least-thirty-two-characters",
  );
  api.listAccountHistory.mockReset();
  api.listAccountHistory.mockResolvedValue({ roots: [] });
  api.listReadings.mockReset();
  api.listReadings.mockResolvedValue({ readings: [] });
});

describe("account history route wiring", () => {
  it("keeps the list private for signed-out users and offers login", async () => {
    render(<AccountHistoryPage />);

    expect(await screen.findByRole("status", { name: "需要登录" })).toBeVisible();
    expect(screen.getByRole("link", { name: "前往登录" })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    expect(api.listReadings).not.toHaveBeenCalled();
  });

  it("connects the signed-in list to the server ReadingRoot/version projection", async () => {
    api.getAccount.mockResolvedValue(account);
    api.listAccountHistory.mockResolvedValue({
      roots: [
        {
          reading_root_id: reading.reading_root_id,
          profile_version_id: reading.profile_version_id,
          capability_id: reading.capability_id,
          created_at: reading.created_at,
          versions: [
            {
              reading_version_id: reading.reading_version_id,
              reading_root_id: reading.reading_root_id,
              capability_id: reading.capability_id,
              version: reading.version,
              status: reading.status,
              object_id: reading.object_id,
              dimension_ids: reading.dimension_ids,
              horizon: reading.horizon,
              created_at: reading.created_at,
            },
            {
              reading_version_id: "66666666-6666-4666-8666-666666666666",
              reading_root_id: reading.reading_root_id,
              capability_id: reading.capability_id,
              version: 1,
              status: "accepted",
              object_id: reading.object_id,
              dimension_ids: reading.dimension_ids,
              horizon: reading.horizon,
              created_at: "2026-08-09T01:00:00Z",
            },
          ],
        },
      ],
    });

    render(<AccountHistoryPage />);

    expect(await screen.findByRole("heading", { name: "最近解读版本" })).toBeVisible();
    expect(screen.getByRole("link", { name: /日运与周运.*版本 v2/ })).toHaveAttribute(
      "href",
      `/account/history/${reading.reading_version_id}`,
    );
    expect(screen.getByText("2 个版本")).toBeVisible();
    expect(api.listAccountHistory).toHaveBeenCalledTimes(1);
    expect(api.listReadings).not.toHaveBeenCalled();
  });

  it("passes the opaque version id to the real detail reader after login", async () => {
    api.getAccount.mockResolvedValue(account);

    const page = await AccountHistoryDetailPage({
      params: Promise.resolve({ rootId: reading.reading_version_id }),
    });
    render(<AccountSessionProvider>{page}</AccountSessionProvider>);

    expect(await screen.findByRole("region", { name: "真实历史详情" })).toHaveTextContent(
      reading.reading_version_id,
    );
  });
});
