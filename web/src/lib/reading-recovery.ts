import type { TaskFormValues } from "@/components/task/product-input-form";

const STORAGE_PREFIX = "mingli.recoverable-reading.v3";
const LEGACY_STORAGE_PREFIXES = [
  "mingli.recoverable-reading.v1",
  "mingli.recoverable-reading.v2",
] as const;
export const RECOVERY_TTL_MS = 30 * 60 * 1000;
const RECORD_VERSION = 3;
const INLINE_PRODUCT_IDS = new Set(["bazi", "ziwei", "liuyao", "meihua", "daliuren"]);

const STRING_FIELDS: Record<string, readonly (keyof TaskFormValues)[]> = {
  bazi: ["issue", "targetYear", "targetMonth", "targetDate"],
  ziwei: ["issue", "targetYear", "targetMonth"],
  liuyao: ["issue", "focus", "eventTime", "timezone", "location"],
  meihua: [
    "issue",
    "focus",
    "eventTime",
    "timezone",
    "location",
    "timeStandard",
    "meihuaCastingMethod",
    "meihuaNumber",
    "meihuaCount",
    "meihuaUpperTrigram",
    "meihuaLowerTrigram",
    "meihuaMovingLine",
    "meihuaSource",
  ],
  daliuren: [
    "issue",
    "focus",
    "eventTime",
    "timezone",
    "location",
    "timeStandard",
    "timingStart",
    "timingEnd",
  ],
};

export type RecoverableReading = {
  readonly readingVersionId: string;
  readonly startedAt: number;
  readonly submission: {
    readonly profileVersionId?: string;
    readonly values: Partial<TaskFormValues>;
  };
};

type SaveSubmission = {
  readonly profileVersionId?: string;
  readonly startedAt: number;
  readonly values: TaskFormValues;
};

function key(productId: string): string {
  return `${STORAGE_PREFIX}.${productId}`;
}

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function saveRecoverableReading(
  productId: string,
  readingVersionId: string,
  submission: SaveSubmission,
): void {
  if (!INLINE_PRODUCT_IDS.has(productId) || !readingVersionId) return;
  const target = storage();
  if (!target) return;
  const values = sanitizeValues(productId, submission.values);
  const profileVersionId =
    typeof submission.profileVersionId === "string" && submission.profileVersionId
      ? submission.profileVersionId
      : undefined;
  const startedAt =
    Number.isFinite(submission.startedAt) && submission.startedAt > 0
      ? submission.startedAt
      : Date.now();
  try {
    target.setItem(
      key(productId),
      JSON.stringify({
        version: RECORD_VERSION,
        product_id: productId,
        reading_version_id: readingVersionId,
        started_at: startedAt,
        expires_at: Date.now() + RECOVERY_TTL_MS,
        submission: {
          ...(profileVersionId ? { profile_version_id: profileVersionId } : {}),
          values,
        },
      }),
    );
  } catch {
    // Recovery is best-effort when browser storage is unavailable.
  }
}

export function loadRecoverableReading(productId: string): RecoverableReading | null {
  if (!INLINE_PRODUCT_IDS.has(productId)) return null;
  const target = storage();
  if (!target) return null;
  try {
    for (const prefix of LEGACY_STORAGE_PREFIXES) {
      target.removeItem(`${prefix}.${productId}`);
    }
    const raw = target.getItem(key(productId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!isRecord(parsed)) throw new Error("invalid recovery record");
    if (
      parsed.version !== RECORD_VERSION ||
      parsed.product_id !== productId ||
      typeof parsed.reading_version_id !== "string" ||
      !parsed.reading_version_id ||
      typeof parsed.started_at !== "number" ||
      !Number.isFinite(parsed.started_at) ||
      parsed.started_at <= 0 ||
      typeof parsed.expires_at !== "number" ||
      !Number.isFinite(parsed.expires_at) ||
      parsed.started_at > parsed.expires_at ||
      parsed.expires_at <= Date.now() ||
      !isRecord(parsed.submission) ||
      !isRecord(parsed.submission.values)
    ) {
      throw new Error("invalid recovery record");
    }
    const profileVersionId =
      typeof parsed.submission.profile_version_id === "string" &&
      parsed.submission.profile_version_id
        ? parsed.submission.profile_version_id
        : undefined;
    return {
      readingVersionId: parsed.reading_version_id,
      startedAt: parsed.started_at,
      submission: {
        ...(profileVersionId ? { profileVersionId } : {}),
        values: sanitizeValues(productId, parsed.submission.values),
      },
    };
  } catch {
    try {
      target.removeItem(key(productId));
    } catch {
      // Recovery remains optional when session storage is unavailable.
    }
    return null;
  }
}

export function clearRecoverableReading(productId: string): void {
  if (!productId) return;
  const target = storage();
  if (!target) return;
  try {
    target.removeItem(key(productId));
    for (const prefix of LEGACY_STORAGE_PREFIXES) {
      target.removeItem(`${prefix}.${productId}`);
    }
  } catch {
    // Nothing else to clear.
  }
}

export function resolveReadingStartedAt(
  createdAt: string | null | undefined,
  fallbackStartedAt: number,
): number {
  const serverStartedAt = typeof createdAt === "string" ? Date.parse(createdAt) : Number.NaN;
  if (Number.isFinite(serverStartedAt) && serverStartedAt > 0) {
    return serverStartedAt;
  }
  return Number.isFinite(fallbackStartedAt) && fallbackStartedAt > 0
    ? fallbackStartedAt
    : Date.now();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function sanitizeValues(
  productId: string,
  source: Record<string, unknown> | TaskFormValues,
): Partial<TaskFormValues> {
  const values: Partial<TaskFormValues> = {};
  for (const field of STRING_FIELDS[productId] ?? []) {
    const value = source[field];
    if (typeof value === "string") {
      Object.assign(values, { [field]: value });
    }
  }
  if (
    productId === "liuyao" &&
    Array.isArray(source.lines) &&
    source.lines.length === 6 &&
    source.lines.every((line) => typeof line === "string")
  ) {
    values.lines = [...source.lines];
  }
  return values;
}
