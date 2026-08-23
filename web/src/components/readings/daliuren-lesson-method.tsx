"use client";

import type { DaliurenChartViewModel } from "@/view-models/registry";

import styles from "./daliuren-lesson-method.module.css";

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;

export type DaliurenLessonMethodProps = {
  lessonMethod?: CoreFacts["lesson_method"];
  structuralPatterns?: CoreFacts["structural_patterns"];
};

type MethodRow = {
  label: string;
  value: string;
};

function readText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function methodRows(value: CoreFacts["lesson_method"]): readonly MethodRow[] {
  if (!value) return [];
  const rows = [
    { label: "课式", value: readText(value.table_label) ?? readText(value.primary) },
    { label: "发用", value: readText(value.use_method) },
    { label: "三传", value: readText(value.calculated_transmissions) ?? readText(value.table_transmissions) },
  ];
  return rows.filter((row): row is MethodRow => Boolean(row.value));
}

function patternChips(value: CoreFacts["structural_patterns"]): readonly string[] {
  if (!value?.length) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0).map((item) => item.trim());
}

export function DaliurenLessonMethod({
  lessonMethod = null,
  structuralPatterns = null,
}: DaliurenLessonMethodProps) {
  const rows = methodRows(lessonMethod);
  const patterns = patternChips(structuralPatterns);
  if (!rows.length && !patterns.length) return null;

  return (
    <section className={styles.panel} aria-label="课式与传法" data-slot="lesson-method">
      {rows.map((row) => (
        <p className={styles.row} key={row.label}>
          <span className={styles.label}>{row.label}</span>
          <span className={styles.value}>{row.value}</span>
        </p>
      ))}
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
