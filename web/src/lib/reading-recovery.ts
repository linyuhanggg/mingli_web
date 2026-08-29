const STORAGE_PREFIX = "mingli.inline-reading.v1.";
const INLINE_ARTS = new Set(["ziwei", "liuyao"]);
const LIUYAO_LINES = new Set([
  "old-yin",
  "young-yang",
  "young-yin",
  "old-yang",
]);

export type RecoverableArtId = "ziwei" | "liuyao";

export type RecoverableZiweiValues = {
  issue: string;
  targetMonth: string;
  targetYear: string;
};

export type RecoverableLiuyaoValues = {
  eventTime: string;
  focus: string;
  issue: string;
  lines: string[];
  location: string;
  timezone: string;
};

export type RecoverableReading = {
  productId: RecoverableArtId;
  readingVersionId: string;
  startedAt: number;
  submission: {
    profileVersionId?: string;
    values: RecoverableZiweiValues | RecoverableLiuyaoValues;
  };
  version: 1;
};

type SaveInput = {
  profileVersionId?: string;
  startedAt: number;
  values: Record<string, unknown>;
};

type SearchLike = {
  get(name: string): string | null;
  toString(): string;
};

function supportedArt(productId: string): productId is RecoverableArtId {
  return INLINE_ARTS.has(productId);
}

function storageKey(productId: RecoverableArtId): string {
  return `${STORAGE_PREFIX}${productId}`;
}

function cleanString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function cleanLines(value: unknown): string[] | null {
  if (!Array.isArray(value) || value.length !== 6) return null;
  const lines = value.map(cleanString);
  return lines.every((line) => LIUYAO_LINES.has(line)) ? lines : null;
}

function cleanValues(
  productId: RecoverableArtId,
  values: Record<string, unknown>,
): RecoverableZiweiValues | RecoverableLiuyaoValues | null {
  if (productId === "ziwei") {
    return {
      issue: cleanString(values.issue),
      targetMonth: cleanString(values.targetMonth),
      targetYear: cleanString(values.targetYear),
    };
  }
  const lines = cleanLines(values.lines);
  if (!lines) return null;
  return {
    eventTime: cleanString(values.eventTime),
    focus: cleanString(values.focus),
    issue: cleanString(values.issue),
    lines,
    location: cleanString(values.location),
    timezone: cleanString(values.timezone),
  };
}

function normalizeRecovery(value: unknown): RecoverableReading | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const candidate = value as Record<string, unknown>;
  const productId = cleanString(candidate.productId);
  const readingVersionId = cleanString(candidate.readingVersionId);
  const startedAt = candidate.startedAt;
  const submission = candidate.submission;
  if (
    candidate.version !== 1
    || !supportedArt(productId)
    || !readingVersionId
    || typeof startedAt !== "number"
    || !Number.isFinite(startedAt)
    || startedAt <= 0
    || !submission
    || typeof submission !== "object"
    || Array.isArray(submission)
  ) {
    return null;
  }
  const submissionRecord = submission as Record<string, unknown>;
  const rawValues = submissionRecord.values;
  if (!rawValues || typeof rawValues !== "object" || Array.isArray(rawValues)) {
    return null;
  }
  const values = cleanValues(productId, rawValues as Record<string, unknown>);
  if (!values) return null;
  const profileVersionId = cleanString(submissionRecord.profileVersionId);
  return {
    productId,
    readingVersionId,
    startedAt,
    submission: {
      ...(profileVersionId ? { profileVersionId } : {}),
      values,
    },
    version: 1,
  };
}

export function saveRecoverableReading(
  productId: string,
  readingVersionId: string,
  input: SaveInput,
): RecoverableReading | null {
  if (!supportedArt(productId)) return null;
  const recovery = normalizeRecovery({
    productId,
    readingVersionId,
    startedAt: input.startedAt,
    submission: {
      profileVersionId: input.profileVersionId,
      values: input.values,
    },
    version: 1,
  });
  if (!recovery || typeof window === "undefined") return recovery;
  try {
    window.sessionStorage.setItem(storageKey(productId), JSON.stringify(recovery));
  } catch {
    return null;
  }
  return recovery;
}

export function loadRecoverableReading(
  productId: string,
  expectedReadingVersionId?: string | null,
): RecoverableReading | null {
  if (!supportedArt(productId) || typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(storageKey(productId));
    if (!raw) return null;
    const recovery = normalizeRecovery(JSON.parse(raw));
    const expected = expectedReadingVersionId?.trim() ?? "";
    if (
      !recovery
      || recovery.productId !== productId
      || (expected && recovery.readingVersionId !== expected)
    ) {
      return null;
    }
    return recovery;
  } catch {
    return null;
  }
}

export function clearRecoverableReading(productId: string): void {
  if (!supportedArt(productId) || typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(storageKey(productId));
  } catch {
    // Clearing the route still prevents an inaccessible storage value from resuming.
  }
}

export function readInlineReadingId(
  productId: string,
  searchParams: SearchLike,
): string | null {
  if (!supportedArt(productId)) return null;
  const readingId = searchParams.get("reading")?.trim() ?? "";
  return readingId || null;
}

export function inlineReadingRestoreHref(
  pathname: string,
  searchParams: SearchLike,
  readingVersionId: string | null,
): string {
  const next = new URLSearchParams(searchParams.toString());
  const readingId = readingVersionId?.trim() ?? "";
  if (readingId) next.set("reading", readingId);
  else next.delete("reading");
  const query = next.toString();
  return query ? `${pathname}?${query}` : pathname;
}

export function resolveReadingStartedAt(
  createdAt: string | null | undefined,
  fallback = Date.now(),
): number {
  const parsed = typeof createdAt === "string" ? Date.parse(createdAt) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}
