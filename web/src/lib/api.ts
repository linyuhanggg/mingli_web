"use client";

export type Gender = "male" | "female" | "other";
export type TimeBasisPolicy = "civil" | "solar" | "lunar";
export type ZiHourPolicy = "midnight" | "substitute" | "solar";

export type ProfileSummary = {
  profile_id: string;
  profile_version_id: string;
  subject_ref: string;
  version: number;
  created_at: string;
};

export type ProfileDraftResponse = {
  draft_id: string;
  status: "draft";
};

export type ProfileConfirmRequest = {
  birth_datetime: string;
  timezone: string;
  location: string;
  gender: Gender;
  time_basis_policy: TimeBasisPolicy;
  zi_hour_policy: ZiHourPolicy;
  longitude?: number | null;
  latitude?: number | null;
  coordinate_source?: string | null;
};

export type ReadingStatus =
  | "input_ready"
  | "waiting_input"
  | "prepared"
  | "completing"
  | "accepted"
  | "delayed"
  | "runtime_unknown"
  | "terminal_stopped";

export type ReadingHorizon = {
  kind_id: string;
  start: string | null;
  end: string | null;
};

export type PublicTerm = {
  id: string;
  label: string;
  description: string | null;
};

export type NeedInputField = {
  id: string;
  label: string;
  type_id: string;
  description: string | null;
  choices: PublicTerm[];
};

export type NeedInputRequirement = {
  any_of: NeedInputField[];
};

export type NeedInputRequest = {
  requirements: NeedInputRequirement[];
};

export type ReadingVersionSummary = {
  reading_version_id: string;
  reading_root_id: string;
  profile_version_id: string | null;
  capability_id: string;
  version: number;
  status: ReadingStatus;
  object_id: string;
  dimension_ids: string[];
  horizon: ReadingHorizon;
  prior_answer: string | null;
  input_request: NeedInputRequest | null;
  created_at: string;
};

export type PreviewStartRequest = {
  profile_version_id: string;
  query?: string;
  dimension_ids?: ("overview" | "career")[];
};

export type FortuneStartRequest = {
  profile_version_id: string;
  query?: string;
};

export type LiuyaoStartRequest = {
  cast: "digital_coin" | [number, number, number, number, number, number];
  event_datetime: string;
  timezone: string;
  location: string;
  subject_ref?: string;
  query?: string;
  dimension_ids?: ("career" | "outcome" | "timing")[];
};

export type ReadingFact = {
  ref: string;
  subject_ref: string;
  kind_id: string;
  value: unknown;
  display_text: string;
};

export type ReadingEvidence = {
  ref: string;
  source_title: string;
  locator: string | null;
  excerpt: string | null;
  supports_fact_refs: string[];
};

export type ReadingLimit = {
  kind_id: string;
  public_text: string;
  scope_refs: string[];
  detail_ids: string[];
};

export type ReadingRequestView = {
  subject_refs: string[];
  capability_ids: string[];
  object_id: string;
  dimension_ids: string[];
  horizon: ReadingHorizon;
};

export type ReadingFactPanel = {
  question: string;
  vocabulary: PublicTerm[];
  facts: ReadingFact[];
  evidence: ReadingEvidence[];
  findings: unknown[];
  claim_scopes: unknown[];
  limits: ReadingLimit[];
  prior_answer: string | null;
  request_view: ReadingRequestView | null;
};

export type VerificationOutcome =
  | "accepted"
  | "partial"
  | "disagreed"
  | "unknown";

export type ReadingVerificationSummary = {
  verification_id: string;
  reading_version_id: string;
  outcome: VerificationOutcome;
  note: string | null;
  created_at: string;
};

export type ReadingResultResponse = {
  reading_version_id: string;
  status: ReadingStatus;
  accepted_copy: string | null;
  fact_panel: ReadingFactPanel | null;
  verification: ReadingVerificationSummary | null;
  input_request: NeedInputRequest | null;
};

export type ReadingListResponse = {
  readings: ReadingVersionSummary[];
};

const RAW_INPUT_FACT_REF = /\/input\/[^/]+$/;

function removePrivateFactRefs(items: unknown[], removedRefs: Set<string>): unknown[] {
  return items.map((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return item;
    const record = item as Record<string, unknown>;
    if (!Array.isArray(record.fact_refs)) return item;
    return {
      ...record,
      fact_refs: record.fact_refs.filter(
        (ref): ref is string => typeof ref === "string" && !removedRefs.has(ref),
      ),
    };
  });
}

/**
 * Defense in depth for the result UI: raw caller inputs are never retained in
 * React state. The browser only keeps derived, publicly presentable facts.
 */
function projectClientSafeFactPanel(panel: ReadingFactPanel): ReadingFactPanel {
  const removedRefs = new Set(
    panel.facts
      .filter((fact) => RAW_INPUT_FACT_REF.test(fact.ref))
      .map((fact) => fact.ref),
  );
  if (removedRefs.size === 0) return panel;

  return {
    ...panel,
    facts: panel.facts.filter((fact) => !removedRefs.has(fact.ref)),
    evidence: panel.evidence.map((item) => ({
      ...item,
      supports_fact_refs: item.supports_fact_refs.filter(
        (ref) => !removedRefs.has(ref),
      ),
    })),
    findings: removePrivateFactRefs(panel.findings, removedRefs),
    claim_scopes: removePrivateFactRefs(panel.claim_scopes, removedRefs),
  };
}

export type LoginIdentitySummary = {
  id: string;
  provider: "phone" | "email";
  masked_destination: string;
  verified_at: string;
};

export type AccountResponse = {
  user_id: string;
  identities: LoginIdentitySummary[];
};

type ProblemBody = {
  title?: string;
  detail?: string;
};

type PostOptions = {
  idempotencyKey?: string;
};

let csrfToken = "";
let csrfPromise: Promise<string> | null = null;
type AccountSessionInvalidationListener = () => void | Promise<void>;
const accountSessionInvalidationListeners = new Set<AccountSessionInvalidationListener>();
/**
 * Single-flight for private API 401 storms: concurrent/back-to-back notifies
 * share one listener flush that stays open until every listener settles.
 */
let accountSessionInvalidationFlush: Promise<void> | null = null;

const CSRF_COOKIE = "mingli_csrf";

export function subscribeAccountSessionInvalidation(
  listener: AccountSessionInvalidationListener,
): () => void {
  accountSessionInvalidationListeners.add(listener);
  return () => accountSessionInvalidationListeners.delete(listener);
}

function notifyAccountSessionInvalidated(): void {
  if (accountSessionInvalidationListeners.size === 0) {
    return;
  }
  if (accountSessionInvalidationFlush) {
    return;
  }
  const listeners = [...accountSessionInvalidationListeners];
  accountSessionInvalidationFlush = (async () => {
    await Promise.all(
      listeners.map(async (listener) => {
        await listener();
      }),
    );
  })().finally(() => {
    accountSessionInvalidationFlush = null;
  });
}

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status = 0, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function requestJson<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, { ...options, credentials: "include" });
  let body: (T & ProblemBody) | null = null;

  if (response.headers.get("content-type")?.includes("json")) {
    try {
      body = (await response.json()) as T & ProblemBody;
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearCsrfCache();
      if (url !== "/api/v1/account") {
        notifyAccountSessionInvalidated();
      }
    }
    throw new ApiError(
      body?.title ?? "服务暂时不可用，请稍后重试",
      response.status,
      body?.detail,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!body) {
    throw new ApiError("服务器响应异常，请稍后重试", response.status);
  }
  return body as T;
}

function validateIdempotencyKey(key: string): void {
  if (key.length < 8 || key.length > 128) {
    throw new ApiError("请求标识无效，请重新发起", 400);
  }
}

async function jsonPost<T>(
  url: string,
  payload: unknown,
  options: PostOptions = {},
): Promise<T> {
  if (options.idempotencyKey) {
    validateIdempotencyKey(options.idempotencyKey);
  }

  const execute = async () => {
    const csrf = await getCsrfToken();
    const headers = new Headers({
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    });
    if (options.idempotencyKey) {
      headers.set("Idempotency-Key", options.idempotencyKey);
    }
    return requestJson<T>(url, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
  };

  try {
    return await execute();
  } catch (error) {
    if (
      !(error instanceof ApiError) ||
      error.status !== 403 ||
      error.message !== "CSRF validation failed"
    ) {
      throw error;
    }
    clearCsrfCache();
    return execute();
  }
}

function readCsrfCookie(): string {
  if (typeof document === "undefined") {
    return "";
  }
  const pair = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${CSRF_COOKIE}=`));
  if (!pair) {
    return "";
  }
  return pair.slice(pair.indexOf("=") + 1);
}

function clearCsrfCache(): void {
  csrfToken = "";
  csrfPromise = null;
}

/** Adopt the device CSRF returned by a successful OTP verification. */
export function adoptCsrfToken(token: string): void {
  if (!token) {
    return;
  }
  csrfToken = token;
  csrfPromise = null;
}

export async function getCsrfToken(): Promise<string> {
  const cookieToken = readCsrfCookie();
  if (cookieToken) {
    csrfToken = cookieToken;
    csrfPromise = null;
    return cookieToken;
  }
  if (csrfToken) {
    return csrfToken;
  }
  if (!csrfPromise) {
    csrfPromise = requestJson<{ csrf_token: string }>("/api/v1/guest-sessions", {
      method: "POST",
    })
      .then((session) => {
        if (!session.csrf_token) {
          throw new ApiError("安全会话响应缺少 CSRF Token", 502);
        }
        csrfToken = session.csrf_token;
        return csrfToken;
      })
      .finally(() => {
        csrfPromise = null;
      });
  }
  return csrfPromise;
}

export function createIdempotencyKey(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `reading-${globalThis.crypto.randomUUID()}`;
  }
  return `reading-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export async function createProfileDraft(
  label = "本人",
): Promise<ProfileDraftResponse> {
  const normalizedLabel = label.trim() || "本人";
  return jsonPost<ProfileDraftResponse>("/api/v1/profiles/drafts", {
    label: normalizedLabel,
  });
}

export async function confirmProfileDraft(
  draftId: string,
  body: ProfileConfirmRequest,
): Promise<ProfileSummary> {
  return jsonPost<ProfileSummary>(
    `/api/v1/profiles/drafts/${encodeURIComponent(draftId)}/confirm`,
    body,
  );
}

export async function listProfiles(): Promise<{ profiles: ProfileSummary[] }> {
  await getCsrfToken();
  return requestJson<{ profiles: ProfileSummary[] }>("/api/v1/profiles");
}

export async function listReadings(): Promise<ReadingListResponse> {
  await getCsrfToken();
  return requestJson<ReadingListResponse>("/api/v1/readings");
}

export async function getAccount(): Promise<AccountResponse> {
  return requestJson<AccountResponse>("/api/v1/account");
}

export async function logoutCurrentDevice(): Promise<void> {
  await jsonPost<void>("/api/v1/auth/logout", {});
  resetApiCache();
}

export async function startPreviewReading(
  body: PreviewStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/preview", body, {
    idempotencyKey,
  });
}

export async function startTodayReading(
  body: FortuneStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/today", body, {
    idempotencyKey,
  });
}

export async function startWeekReading(
  body: FortuneStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/week", body, {
    idempotencyKey,
  });
}

export async function startLiuyaoReading(
  body: LiuyaoStartRequest,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>("/api/v1/readings/liuyao", body, {
    idempotencyKey,
  });
}

export async function pollReading(
  readingVersionId: string,
): Promise<ReadingVersionSummary> {
  return requestJson<ReadingVersionSummary>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}`,
  );
}

export async function getReadingResult(
  readingVersionId: string,
): Promise<ReadingResultResponse> {
  const result = await requestJson<ReadingResultResponse>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}/result`,
  );
  return {
    ...result,
    fact_panel: result.fact_panel
      ? projectClientSafeFactPanel(result.fact_panel)
      : null,
  };
}

export async function submitReadingInput(
  readingVersionId: string,
  values: Record<string, unknown>,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}/input`,
    { values },
  );
}

export async function verifyReading(
  readingVersionId: string,
  outcome: VerificationOutcome,
  note?: string,
): Promise<ReadingVerificationSummary> {
  const payload: { outcome: VerificationOutcome; note?: string } = { outcome };
  if (note?.trim()) {
    payload.note = note.trim();
  }
  return jsonPost<ReadingVerificationSummary>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}/verification`,
    payload,
  );
}

export async function createFollowUp(
  readingVersionId: string,
  query: string,
  idempotencyKey: string,
): Promise<ReadingVersionSummary> {
  return jsonPost<ReadingVersionSummary>(
    `/api/v1/readings/${encodeURIComponent(readingVersionId)}/follow-up`,
    { query },
    { idempotencyKey },
  );
}

export function formatProfileOption(profile: ProfileSummary): string {
  return `档案 ${profile.version} · ${new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(profile.created_at))}`;
}

export function resetApiCache(): void {
  clearCsrfCache();
}
