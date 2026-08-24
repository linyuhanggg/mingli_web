"use client";

import type { DaliurenChartViewModel } from "@/view-models/registry";

import styles from "./daliuren-caliber-bar.module.css";

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;

export type DaliurenCaliberBarProps = {
  question?: string | null;
  dayHour?: CoreFacts["day_hour"];
  monthGeneral?: CoreFacts["month_general"];
  noblePerson?: CoreFacts["noble_person"];
  xunkong?: CoreFacts["xunkong"];
};

const TEXT_KEYS = ["display_text", "fact_text", "text", "label", "name", "note"] as const;
const MONTH_TEXT_KEYS = ["display_text", "fact_text", "text", "label", "note"] as const;
const LONG_QUESTION = 24;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function readString(value: unknown, key: string): string | null {
  if (!isRecord(value)) return null;
  const field = value[key];
  return typeof field === "string" && field.trim() ? field.trim() : null;
}

function firstAllowedText(value: unknown, keys: readonly string[] = TEXT_KEYS): string | null {
  if (!isRecord(value)) return null;
  for (const key of keys) {
    const text = readString(value, key);
    if (text) return text;
  }
  return null;
}

function readQuestion(value: string | null | undefined): string | null {
  const text = value?.trim();
  return text ? text : null;
}

function dayHourLine(value: unknown): string | null {
  const sentence = firstAllowedText(value);
  if (sentence) return sentence;
  const day = readString(value, "day");
  const hour = readString(value, "hour");
  if (day && hour) return `${day}日 ${hour}时`;
  return day ?? hour;
}

function monthGeneralLine(value: unknown): string | null {
  const sentence = firstAllowedText(value, MONTH_TEXT_KEYS);
  if (sentence) return sentence;
  const branch = readString(value, "branch");
  const name = readString(value, "name");
  if (branch && name) return `月将：${branch}（${name}）`;
  if (branch) return `月将：${branch}`;
  if (name) return `月将：${name}`;
  return null;
}

function noblePersonLine(value: unknown): string | null {
  const sentence = firstAllowedText(value);
  if (sentence) return sentence;
  const branch = readString(value, "branch") ?? readString(value, "earth_position");
  return branch ? `贵人：${branch}` : null;
}

function xunkongLine(value: unknown): string | null {
  const sentence = firstAllowedText(value);
  if (sentence) return sentence;
  if (isRecord(value) && Array.isArray(value.branches)) {
    const branches = value.branches.filter((item): item is string => typeof item === "string" && Boolean(item.trim()));
    if (branches.length) return `旬空：${branches.map((item) => item.trim()).join("")}`;
  }
  const xun = readString(value, "xun");
  return xun ? `旬空：${xun}` : null;
}

export function DaliurenCaliberBar({
  question = null,
  dayHour = null,
  monthGeneral = null,
  noblePerson = null,
  xunkong = null,
}: DaliurenCaliberBarProps) {
  const asked = readQuestion(question);
  const day = dayHourLine(dayHour);
  const month = monthGeneralLine(monthGeneral);
  const noble = noblePersonLine(noblePerson);
  const voids = xunkongLine(xunkong);
  if (!asked && !day && !month && !noble && !voids) return null;

  const fold = Boolean(asked && asked.length > LONG_QUESTION);

  return (
    <section aria-label="起课口径" className={styles.bar} data-slot="caliber">
      {asked ? (
        fold ? (
          <details className={styles.fold}>
            <summary className={styles.summary}>展开</summary>
            <p className={styles.line}>{asked}</p>
          </details>
        ) : (
          <p className={styles.line}>{asked}</p>
        )
      ) : null}
      {day ? <p className={styles.line}>{day}</p> : null}
      {month ? <p className={styles.line}>{month}</p> : null}
      {noble ? <p className={styles.line}>{noble}</p> : null}
      {voids ? <p className={styles.line}>{voids}</p> : null}
    </section>
  );
}
