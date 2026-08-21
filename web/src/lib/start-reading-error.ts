import { ApiError } from "@/lib/api";

export const START_READING_UNAVAILABLE = "服务暂时不可用，请稍后重试。";

const CONSTRUCTION = /Runtime|Provider|适配器|development_code|release unavailable/i;

function looksLikeConstruction(text: string | undefined) {
  if (!text) return false;
  if (CONSTRUCTION.test(text)) return true;
  return /[A-Za-z]/.test(text) && !/[一-鿿]/.test(text);
}

export function mapStartReadingFailure(reason: unknown): {
  state: "unavailable" | "error";
  title: string;
} {
  if (reason instanceof ApiError) {
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
