import type { ProfileSummary } from "@/lib/api/contracts";
import { formatProfileOption } from "@/lib/api/account";

const FLASH_KEY = "mingli.profile-saved-flash.v2";
const LEGACY_FLASH_KEY = "mingli.profile-saved-flash.v1";

export type ProfileSavedFlash = {
  readonly name: string;
  readonly profileId: string;
};

type ProfileDisplayFields = {
  readonly display_name?: string | null;
  readonly birth_date?: string | null;
};

function displayFields(profile: ProfileSummary): ProfileDisplayFields {
  return profile as ProfileSummary & ProfileDisplayFields;
}

function normalizedName(value: string): string {
  return value.trim().replace(/\s+/g, " ").slice(0, 80);
}

export function defaultProfileName(subject: string, birthDate: string): string {
  const subjectName = normalizedName(subject) || "我自己";
  const year = /^\d{4}/.exec(birthDate)?.[0];
  return year ? `${subjectName} · ${year}` : subjectName;
}

export function profileDisplayName(profile: ProfileSummary): string {
  return normalizedName(displayFields(profile).display_name ?? "") || "未命名档案";
}

export function profileBirthDate(profile: ProfileSummary): string {
  const birthDate = displayFields(profile).birth_date;
  return birthDate && /^\d{4}-\d{2}-\d{2}$/.test(birthDate)
    ? birthDate
    : "生日未记录";
}

export function formatProfileDisplayOption(profile: ProfileSummary): string {
  const fields = displayFields(profile);
  const name = normalizedName(fields.display_name ?? "");
  const birthDate = fields.birth_date;
  if (!name || !birthDate || !/^\d{4}-\d{2}-\d{2}$/.test(birthDate)) {
    return formatProfileOption(profile);
  }
  return `${name} · ${birthDate}`;
}

export function findProfileWithDisplayName(
  profiles: readonly ProfileSummary[],
  name: string,
): ProfileSummary | null {
  const expected = normalizedName(name);
  if (!expected) return null;
  return (
    profiles.find(
      (profile) => normalizedName(displayFields(profile).display_name ?? "") === expected,
    ) ?? null
  );
}

export function suggestUniqueProfileName(
  profiles: readonly ProfileSummary[],
  name: string,
): string {
  const base = normalizedName(name) || "新档案";
  const names = new Set(
    profiles
      .map((profile) => normalizedName(displayFields(profile).display_name ?? ""))
      .filter((value): value is string => Boolean(value)),
  );
  if (!names.has(base)) return base;
  let suffix = 2;
  while (true) {
    const suffixText = ` ${suffix}`;
    const candidate = `${base.slice(0, 80 - suffixText.length)}${suffixText}`;
    if (!names.has(candidate)) return candidate;
    suffix += 1;
  }
}

export function setProfileSavedFlash(name: string, profileId: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(
      FLASH_KEY,
      JSON.stringify({ name: normalizedName(name), profile_id: profileId }),
    );
  } catch {
    // A generic success message still renders when session storage is blocked.
  }
}

export function consumeProfileSavedFlash(): ProfileSavedFlash | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(FLASH_KEY);
    window.sessionStorage.removeItem(FLASH_KEY);
    window.sessionStorage.removeItem(LEGACY_FLASH_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { name?: unknown; profile_id?: unknown };
    const name = typeof parsed.name === "string" ? normalizedName(parsed.name) : "";
    return name && typeof parsed.profile_id === "string" && parsed.profile_id
      ? { name, profileId: parsed.profile_id }
      : null;
  } catch {
    return null;
  }
}
