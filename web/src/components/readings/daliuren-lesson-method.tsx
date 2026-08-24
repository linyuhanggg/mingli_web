"use client";

import type { DaliurenChartViewModel } from "@/view-models/registry";

import styles from "./daliuren-lesson-method.module.css";

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;

export type DaliurenLessonMethodProps = {
  lessonMethod?: CoreFacts["lesson_method"];
  transmissionMethod?: CoreFacts["transmission_method"];
  structuralPatterns?: CoreFacts["structural_patterns"];
};

const TEXT_KEYS = ["display_text", "fact_text", "text", "label", "name", "note"] as const;

function firstAllowedText(value: unknown): string | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  for (const key of TEXT_KEYS) {
    const field = record[key];
    if (typeof field === "string" && field.trim()) return field.trim();
  }
  return null;
}

function patternChips(value: CoreFacts["structural_patterns"]): readonly string[] {
  if (!value?.length) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0).map((item) => item.trim());
}

export function DaliurenLessonMethod({
  lessonMethod = null,
  transmissionMethod = null,
  structuralPatterns = null,
}: DaliurenLessonMethodProps) {
  const lesson = firstAllowedText(lessonMethod);
  const transmission = firstAllowedText(transmissionMethod);
  const patterns = patternChips(structuralPatterns);
  if (!lesson && !transmission && !patterns.length) return null;

  return (
    <section className={styles.panel} aria-label="课式与传法" data-slot="lesson-method">
      {lesson ? (
        <p className={styles.row}>
          <span className={styles.label}>课式</span>
          <span className={styles.value}>{lesson}</span>
        </p>
      ) : null}
      {transmission ? (
        <p className={styles.row}>
          <span className={styles.label}>传法</span>
          <span className={styles.value}>{transmission}</span>
        </p>
      ) : null}
      {patterns.length ? (
        <ul className={styles.chips}>
          {patterns.map((item) => (
            <li className={styles.chip} data-chip="pattern" key={item}>
              {item}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
