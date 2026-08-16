import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  confirmProfileDraft: vi.fn(),
  createProfileDraft: vi.fn(),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  push: vi.fn(),
  startBaziRelationshipReading: vi.fn(),
  startQizhengRelationshipReading: vi.fn(),
  startZiweiRelationshipReading: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  ...mocks,
}));

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: mocks.push }),
  useSearchParams: () => new URLSearchParams(),
}));

import { RelationshipTaskPage } from "@/components/relationship/relationship-task-page";

afterEach(() => {
  vi.clearAllMocks();
});

function fillPerson(
  user: ReturnType<typeof userEvent.setup>,
  side: "甲方" | "乙方",
  values: { name: string; date: string; time: string; location: string; gender: "male" | "female" },
) {
  return (async () => {
    await user.type(screen.getByLabelText(`${side}受测对象`), values.name);
    await user.selectOptions(screen.getByLabelText(`${side}性别`), values.gender);
    fireEvent.change(screen.getByLabelText(`${side}出生日期`), { target: { value: values.date } });
    fireEvent.change(screen.getByLabelText(`${side}出生时间`), { target: { value: values.time } });
    await user.type(screen.getByLabelText(`${side}出生地点`), values.location);
    await user.selectOptions(screen.getByLabelText(`${side}时间口径`), "civil");
  })();
}

describe("relationship task wiring", () => {
  it("creates two profiles, starts the selected relationship product, and navigates to the result", async () => {
    const user = userEvent.setup();
    mocks.createProfileDraft
      .mockResolvedValueOnce({ draft_id: "draft-a", status: "draft" })
      .mockResolvedValueOnce({ draft_id: "draft-b", status: "draft" });
    mocks.confirmProfileDraft
      .mockResolvedValueOnce({ profile_id: "profile-a", profile_version_id: "version-a", subject_ref: "profile-version:version-a", version: 1, created_at: "2026-08-15T00:00:00Z" })
      .mockResolvedValueOnce({ profile_id: "profile-b", profile_version_id: "version-b", subject_ref: "profile-version:version-b", version: 1, created_at: "2026-08-15T00:00:00Z" });
    mocks.startBaziRelationshipReading.mockResolvedValue({ reading_version_id: "reading-version-1" });

    render(<RelationshipTaskPage productId="bazi" />);
    await fillPerson(user, "甲方", {
      name: "甲",
      date: "1990-10-18",
      time: "05:10",
      location: "福建省福州市",
      gender: "male",
    });
    await fillPerson(user, "乙方", {
      name: "乙",
      date: "1999-02-03",
      time: "09:20",
      location: "上海市",
      gender: "female",
    });

    await user.click(screen.getByRole("button", { name: "检查双方资料" }));
    await user.click(screen.getByRole("button", { name: "创建档案并生成合盘" }));

    await waitFor(() => expect(mocks.startBaziRelationshipReading).toHaveBeenCalledTimes(1));
    expect(mocks.createProfileDraft).toHaveBeenNthCalledWith(1, "甲");
    expect(mocks.createProfileDraft).toHaveBeenNthCalledWith(2, "乙");
    expect(mocks.confirmProfileDraft).toHaveBeenNthCalledWith(
      1,
      "draft-a",
      expect.objectContaining({
        birth_datetime: "1990-10-18T05:10:00+08:00",
        gender: "male",
        location: "福建省福州市",
        time_basis_policy: "civil",
      }),
    );
    expect(mocks.startBaziRelationshipReading).toHaveBeenCalledWith(
      {
        profile_version_ids: ["version-a", "version-b"],
        relationship_type: "romantic",
        dimension_ids: ["relationship"],
      },
      expect.any(String),
    );
    expect(mocks.push).toHaveBeenCalledWith("/bazi/hepan?reading=reading-version-1");
  });
});
