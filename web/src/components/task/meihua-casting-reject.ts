import { ApiError } from "@/lib/api";

import {
  MEIHUA_S6_COUNT,
  MEIHUA_S6_HEXAGRAM_SOURCE,
  MEIHUA_S6_LOWER,
  MEIHUA_S6_METHOD,
  MEIHUA_S6_MOVING,
  MEIHUA_S6_NUMBER,
  MEIHUA_S6_NUMBER_SOURCE,
  MEIHUA_S6_OBSERVATION_SOURCE,
  MEIHUA_S6_SOUND_SOURCE,
  MEIHUA_S6_UPPER,
} from "./meihua-entry-copy";

export type MeihuaCastingField =
  | "meihuaCastingMethod"
  | "meihuaNumber"
  | "meihuaCount"
  | "meihuaUpperTrigram"
  | "meihuaLowerTrigram"
  | "meihuaMovingLine"
  | "meihuaSource";

export function mapMeihuaCastingRejection(
  reason: unknown,
  values: { meihuaCastingMethod: string },
): { field: MeihuaCastingField; message: string } | null {
  if (!(reason instanceof ApiError)) return null;
  if (reason.status !== 400 && reason.status !== 422) return null;

  const field = detectField(rejectionText(reason)) ?? fallbackField(values.meihuaCastingMethod);
  return { field, message: messageFor(field, values.meihuaCastingMethod) };
}

function rejectionText(reason: ApiError): string {
  const chunks: string[] = [reason.message];
  const detail: unknown = reason.detail;
  if (typeof detail === "string") chunks.push(detail);
  else if (detail) chunks.push(JSON.stringify(detail));
  return chunks.join(" ");
}

function detectField(text: string): MeihuaCastingField | null {
  const haystack = text.toLowerCase();
  if (/moving_line|within 1\.\.6/.test(haystack)) return "meihuaMovingLine";
  if (/upper_trigram/.test(haystack)) return "meihuaUpperTrigram";
  if (/lower_trigram/.test(haystack)) return "meihuaLowerTrigram";
  if (/provenance|observation_source/.test(haystack)) return "meihuaSource";
  if (/casting_method|casting method/.test(haystack)) return "meihuaCastingMethod";
  if (/\bcount\b/.test(haystack)) return "meihuaCount";
  if (/\bnumber\b/.test(haystack)) return "meihuaNumber";
  return null;
}

function fallbackField(method: string): MeihuaCastingField {
  if (method === "supplied_number") return "meihuaNumber";
  if (method === "sound_count") return "meihuaCount";
  if (method === "observation") return "meihuaUpperTrigram";
  if (method === "supplied_hexagram") return "meihuaMovingLine";
  return "meihuaCastingMethod";
}

function messageFor(field: MeihuaCastingField, method: string): string {
  if (field === "meihuaNumber") return MEIHUA_S6_NUMBER;
  if (field === "meihuaCount") return MEIHUA_S6_COUNT;
  if (field === "meihuaUpperTrigram") return MEIHUA_S6_UPPER;
  if (field === "meihuaLowerTrigram") return MEIHUA_S6_LOWER;
  if (field === "meihuaMovingLine") return MEIHUA_S6_MOVING;
  if (field === "meihuaCastingMethod") return MEIHUA_S6_METHOD;
  if (method === "supplied_number") return MEIHUA_S6_NUMBER_SOURCE;
  if (method === "sound_count") return MEIHUA_S6_SOUND_SOURCE;
  if (method === "observation") return MEIHUA_S6_OBSERVATION_SOURCE;
  return MEIHUA_S6_HEXAGRAM_SOURCE;
}
