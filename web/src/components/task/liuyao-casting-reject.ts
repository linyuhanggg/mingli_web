import { ApiError } from "@/lib/api";

import { LIUYAO_LINE_OPTIONS, liuyaoS6IncompleteMessage } from "./liuyao-entry-copy";

const VALID_LINE = new Set(LIUYAO_LINE_OPTIONS.map((option) => option.value));

export function mapLiuyaoCastingRejection(
  reason: unknown,
  lines: readonly string[],
): { index: number; message: string } | null {
  if (!(reason instanceof ApiError)) return null;
  if (reason.status !== 400 && reason.status !== 422) return null;

  const loc = inspectCastLoc(reason);
  const text = rejectionText(reason);
  const missing = firstMissingLineIndex(lines);
  const incomplete = looksLikeIncompleteCast(text, loc.hit);
  if (!incomplete && !(missing !== null && /invalid request/i.test(text))) return null;

  const index = loc.index ?? missing ?? 0;
  return { index, message: liuyaoS6IncompleteMessage(index) };
}

function firstMissingLineIndex(lines: readonly string[]): number | null {
  for (let index = 0; index < 6; index += 1) {
    if (!VALID_LINE.has(lines[index] as (typeof LIUYAO_LINE_OPTIONS)[number]["value"])) {
      return index;
    }
  }
  return null;
}

function looksLikeIncompleteCast(text: string, hasCastLoc: boolean): boolean {
  if (hasCastLoc) return true;
  const haystack = text.toLowerCase();
  if (/question_class/.test(haystack)) return false;
  return /liuyao cast|toss values|bottom-up tosses|integers in 6\.\.9/.test(haystack);
}

function inspectCastLoc(reason: ApiError): { hit: boolean; index: number | null } {
  const parsed = parseDetail(reason.detail);
  const items = Array.isArray(parsed) ? parsed : parsed ? [parsed] : [];
  for (const item of items) {
    if (!item || typeof item !== "object") continue;
    const loc = (item as { loc?: unknown }).loc;
    if (!Array.isArray(loc)) continue;
    const castAt = loc.findIndex((part) => part === "cast" || part === "lines");
    if (castAt < 0) continue;
    const next = loc[castAt + 1];
    if (typeof next === "number" && next >= 0 && next <= 5) {
      return { hit: true, index: next };
    }
    return { hit: true, index: null };
  }
  return { hit: false, index: null };
}

function rejectionText(reason: ApiError): string {
  const chunks: string[] = [reason.message];
  const detail: unknown = reason.detail;
  if (typeof detail === "string") chunks.push(detail);
  else if (detail) chunks.push(JSON.stringify(detail));
  return chunks.join(" ");
}

function parseDetail(detail: string | undefined): unknown {
  if (!detail) return undefined;
  try {
    return JSON.parse(detail) as unknown;
  } catch {
    return undefined;
  }
}
