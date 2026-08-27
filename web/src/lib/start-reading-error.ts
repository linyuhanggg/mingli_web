import { ApiError } from "@/lib/api";

export const START_READING_UNAVAILABLE = "服务暂时不可用，请稍后重试。";
export const PAID_READING_REQUIRES_ACCOUNT = "这项解读需要登录后付费使用。";
export const RATE_LIMIT_EXCEEDED = "提交过于频繁，请稍后再试。";
export const GUEST_DAILY_READING_LIMIT = "今日游客排盘次数已用完，请明日再试或登录后继续。";
export const GUEST_DAILY_PAID_READING_LIMIT = "今日游客付费排盘次数已用完，请明日再试或登录后继续。";
export const USER_DAILY_READING_LIMIT = "今日排盘次数已用完，请明日再试。";
export const USER_DAILY_PAID_READING_LIMIT = "今日付费排盘次数已用完，请明日再试。";
export const CHART_RUNTIME_FAULT = "排盘引擎暂时无法完成这次计算，请稍后重试。";

const DAILY_LIMIT_COPY: Record<string, string> = {
  guest_daily_reading_limit: GUEST_DAILY_READING_LIMIT,
  guest_daily_paid_reading_limit: GUEST_DAILY_PAID_READING_LIMIT,
  user_daily_reading_limit: USER_DAILY_READING_LIMIT,
  user_daily_paid_reading_limit: USER_DAILY_PAID_READING_LIMIT,
};

const LOGIN_FAILURE_CODES = new Set([
  "paid_reading_requires_account",
  "guest_daily_reading_limit",
  "guest_daily_paid_reading_limit",
]);

const CONSTRUCTION = /Runtime|Provider|适配器|development_code|release unavailable/i;
const RUNTIME_CODES = new Set([
  "chart_runtime_error",
  "chart_runtime_timeout",
  "chart_runtime_transport",
  "chart_view_model_projection_failed",
  "chart_runtime_protocol_error",
  "chart_runtime_not_configured",
]);

function looksLikeConstruction(text: string | undefined) {
  if (!text) return false;
  if (CONSTRUCTION.test(text)) return true;
  return /[A-Za-z]/.test(text) && !/[一-鿿]/.test(text);
}

function chineseOr(fallback: string, ...candidates: Array<string | undefined>): string {
  for (const candidate of candidates) {
    if (candidate && /[一-鿿]/.test(candidate) && !looksLikeConstruction(candidate)) {
      return candidate.endsWith("。") ? candidate : `${candidate}。`;
    }
  }
  return fallback;
}

export function startReadingFailureAction(reason: unknown): "login" | "retry" | null {
  if (!(reason instanceof ApiError) || !reason.code) return null;
  if (LOGIN_FAILURE_CODES.has(reason.code)) {
    return "login";
  }
  if (reason.code === "rate_limit_exceeded" || reason.code.startsWith("chart_runtime_")) {
    return "retry";
  }
  return null;
}

export function mapStartReadingFailure(reason: unknown): {
  state: "unavailable" | "error" | "unauthorized";
  title: string;
} {
  if (reason instanceof ApiError) {
    if (reason.code === "paid_reading_requires_account") {
      return {
        state: "unauthorized",
        title: chineseOr(PAID_READING_REQUIRES_ACCOUNT, reason.detail, reason.message),
      };
    }
    if (reason.code === "rate_limit_exceeded") {
      return {
        state: "error",
        title: chineseOr(RATE_LIMIT_EXCEEDED, reason.detail, reason.message),
      };
    }
    if (reason.code && DAILY_LIMIT_COPY[reason.code]) {
      return {
        state: "error",
        title: chineseOr(DAILY_LIMIT_COPY[reason.code], reason.detail, reason.message),
      };
    }
    if (reason.code && (RUNTIME_CODES.has(reason.code) || reason.code.startsWith("chart_runtime_"))) {
      return {
        state: "unavailable",
        title: chineseOr(CHART_RUNTIME_FAULT, reason.detail, reason.message),
      };
    }
    if (reason.status === 503 || reason.status >= 500) {
      return { state: "unavailable", title: START_READING_UNAVAILABLE };
    }
    if (looksLikeConstruction(reason.message) || looksLikeConstruction(reason.detail)) {
      return { state: "unavailable", title: START_READING_UNAVAILABLE };
    }
    return { state: "error", title: reason.message };
  }
  if (reason instanceof Error && reason.message && !looksLikeConstruction(reason.message)) {
    return { state: "error", title: reason.message };
  }
  return { state: "unavailable", title: START_READING_UNAVAILABLE };
}
