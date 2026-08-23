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

const LONG_QUESTION = 24;

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

function noblePersonLine(value: CoreFacts["noble_person"]): string | null {
  return value?.branch ? `贵人：${value.branch}` : null;
}

function xunkongLine(value: CoreFacts["xunkong"]): string | null {
  const branches = (value as { branches?: unknown } | null)?.branches;
  if (!Array.isArray(branches) || branches.length === 0) return null;
  const texts = branches.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
  return texts.length ? `旬空：${texts.join("")}` : null;
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
