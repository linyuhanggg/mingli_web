import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminModelProfilesSurface } from "@/components/admin-model-profiles-surface";

describe("AdminModelProfilesSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows model receipt metadata without fingerprints or token usage", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        profiles: [
          {
            generation_attempt_id: "attempt-1",
            reading_version_id: "reading-version-1",
            attempt_number: 1,
            model_profile_id: "fake-model-p0-v1",
            provider: "fake",
            provider_model_version: "fake-model-v1",
            outcome: "succeeded",
            error_code: null,
            narrative_policy_version: "policy-v1",
            output_contract_id: "reading-document-v1",
            latency_ms: 42,
            usage_known: true,
            cost_known: true,
            guard_error_count: 2,
            created_at: "2026-08-14T01:00:00Z",
          },
        ],
      },
    });

    render(<AdminModelProfilesSurface role="ops" />);

    expect(await screen.findByText("fake-model-p0-v1")).toBeVisible();
    expect(screen.getByText("fake-model-v1")).toBeVisible();
    expect(screen.getByText("成功")).toBeVisible();
    expect(screen.getByText("2")).toBeVisible();
    expect(screen.queryByText("request-fingerprint")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/model-profiles?limit=100",
    );
  });

  it("keeps model receipt metadata away from finance staff", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "Model profile read permission required",
    });

    render(<AdminModelProfilesSurface role="finance" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.queryByText("fake-model-p0-v1")).not.toBeInTheDocument();
  });
});
