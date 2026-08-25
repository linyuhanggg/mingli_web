"use client";

import type { DaliurenChartViewModel } from "@/view-models/registry";

import styles from "./daliuren-caliber-bar.module.css";

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;
type NoblePerson = NonNullable<CoreFacts["noble_person"]>;

export type DaliurenCaliberBarProps = {
  question?: string | null;
  dayHour?: CoreFacts["day_hour"];
  monthGeneral?: CoreFacts["month_general"];
  noblePerson?: CoreFacts["noble_person"];
  xunkong?: CoreFacts["xunkong"];
};

const LONG_QUESTION = 24;

const NOBLE_PERIOD_LABELS: Readonly<Record<NoblePerson["period"], string>> = {
  day: "昼贵",
  night: "夜贵",
};

const NOBLE_DIRECTION_LABELS: Readonly<Record<NoblePerson["direction"], string>> = {
  forward: "顺布",
  reverse: "逆布",
};

const NOBLE_PROFILE_LABELS: Readonly<Record<string, string>> = {
  "official-corrected": "官修订正",
  "traditional-common": "通行口径",
};

const DAY_NIGHT_PROFILE_LABELS: Readonly<Record<string, string>> = {
  "civil-double-hour": "民用双时辰",
};

type NoblePersonLines = Readonly<{
  calculation: string | null;
  summary: string;
  profile: string | null;
  source: string | null;
}>;

function readQuestion(value: string | null | undefined): string | null {
  const text = value?.trim();
  return text ? text : null;
}

function dayHourLine(value: CoreFacts["day_hour"]): string | null {
  if (!value?.day || !value.hour) return null;
  return `${value.day}日 ${value.hour}时`;
}

function monthGeneralLine(value: CoreFacts["month_general"]): string | null {
  if (!value?.branch || !value.name) return null;
  return `月将：${value.branch}（${value.name}）`;
}

function nonEmptyText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim();
  return text ? text : null;
}

function noblePersonLines(value: CoreFacts["noble_person"]): NoblePersonLines | null {
  if (!value) return null;

  const record = value as Partial<Record<keyof NoblePerson, unknown>>;
  const branch = nonEmptyText(record.branch);
  const earthPosition = nonEmptyText(record.earth_position);
  const period = record.period === "day" || record.period === "night" ? record.period : null;
  const direction = record.direction === "forward" || record.direction === "reverse" ? record.direction : null;
  const profile = nonEmptyText(record.profile);
  const dayNightProfile = nonEmptyText(record.day_night_profile);
  const source = nonEmptyText(record.source);
  const profileLabel = profile ? NOBLE_PROFILE_LABELS[profile] : null;
  const dayNightProfileLabel = dayNightProfile ? DAY_NIGHT_PROFILE_LABELS[dayNightProfile] : null;

  if (!branch) return null;

  if (!earthPosition || !period || !direction || !profileLabel || !dayNightProfileLabel || !source) {
    return {
      calculation: null,
      summary: `贵人：${branch}`,
      profile: null,
      source: null,
    };
  }

  return {
    calculation: `贵人时段：${NOBLE_PERIOD_LABELS[period]} · 天将排布：${NOBLE_DIRECTION_LABELS[direction]}`,
    summary: `贵人：${branch}`,
    profile: `贵人口径：${profileLabel} · 昼夜口径：${dayNightProfileLabel}`,
    source: `贵人取法来源：${source}`,
  };
}

function xunkongLine(value: CoreFacts["xunkong"]): string | null {
  if (!value) return null;

  const record = value as { branches?: unknown; xun?: unknown };
  const xun = nonEmptyText(record.xun);
  if (!xun || xun.length < 2 || !Array.isArray(record.branches) || record.branches.length !== 2) return null;

  const branches = record.branches.map(nonEmptyText);
  if (branches.some((branch) => branch === null)) return null;

  return `旬空：${xun}旬 · ${branches.join("")}`;
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
  const noble = noblePersonLines(noblePerson);
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
      {noble ? (
        <>
          <p className={styles.line}>{noble.summary}</p>
          {noble.calculation ? <p className={styles.line}>{noble.calculation}</p> : null}
          {noble.profile ? <p className={styles.line}>{noble.profile}</p> : null}
          {noble.source ? <p className={styles.line}>{noble.source}</p> : null}
        </>
      ) : null}
      {voids ? <p className={styles.line}>{voids}</p> : null}
    </section>
  );
}
