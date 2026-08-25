import { formatProfileOption } from "@/lib/api/account";
import type { ProfileSummary } from "@/lib/api/contracts";
import {
  formatProfileDisplayOption,
  profileBirthDate,
} from "@/lib/profile-display-metadata";

type ProfileWithDisplayMetadata = ProfileSummary & {
  readonly birth_date: string;
  readonly display_name: string;
};

function profileWithBirthDate(birthDate: string): ProfileWithDisplayMetadata {
  return {
    profile_id: "11111111-1111-4111-8111-111111111111",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
    version: 7,
    created_at: "2026-08-25T00:00:00Z",
    display_name: "测试档案",
    birth_date: birthDate,
  };
}

describe("profile display metadata", () => {
  it.each(["1992-06-18", "2024-02-29"])(
    "keeps the friendly label for the valid calendar date %s",
    (birthDate) => {
      const profile = profileWithBirthDate(birthDate);

      expect(profileBirthDate(profile)).toBe(birthDate);
      expect(formatProfileDisplayOption(profile)).toBe(`测试档案 · ${birthDate}`);
    },
  );

  it.each(["2026-99-99", "2026-02-30"])(
    "falls back for the impossible calendar date %s",
    (birthDate) => {
      const profile = profileWithBirthDate(birthDate);

      expect(profileBirthDate(profile)).toBe("生日未记录");
      expect(formatProfileDisplayOption(profile)).toBe(formatProfileOption(profile));
    },
  );
});
