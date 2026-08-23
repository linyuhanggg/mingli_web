"use client";

import type { DaliurenChartViewModel } from "@/view-models/registry";

import styles from "./daliuren-dimension-evidence.module.css";

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;

export type DaliurenDimensionEvidenceProps = {
  dimensionFacts?: CoreFacts["dimension_facts"];
};

const TEXT_KEYS = ["display_text", "fact_text", "text", "label", "name", "note"] as const;

type EvidenceEntry = {
  ruleId: string;
  fact: string;
  pack: string | null;
  anchor: string | null;
};

type EvidenceGroup = {
  dimension: string;
  entries: readonly EvidenceEntry[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function readString(value: unknown, key: string): string | null {
  if (!isRecord(value)) return null;
  const field = value[key];
  return typeof field === "string" && field.trim() ? field.trim() : null;
}

function firstAllowedText(value: unknown): string | null {
  if (!isRecord(value)) return null;
  for (const key of TEXT_KEYS) {
    const text = readString(value, key);
    if (text) return text;
  }
  return null;
}

function parseEntry(value: unknown): EvidenceEntry | null {
  if (!isRecord(value)) return null;
  const ruleId = readString(value, "rule_id");
  const fact = firstAllowedText(value.observation);
  if (!ruleId || !fact) return null;
  const refs = value.source_refs;
  const first = Array.isArray(refs) && refs.length > 0 ? refs[0] : null;
  return {
    ruleId,
    fact,
    pack: readString(first, "pack"),
    anchor: readString(first, "source_anchor"),
  };
}

function parseDimension(value: unknown): EvidenceGroup | null {
  if (!isRecord(value)) return null;
  const dimension = readString(value, "canonical_dimension");
  const requested = readString(value, "requested_dimension");
  const evidence = value.rule_evidence;
  if (!dimension || !requested || !isRecord(evidence)) return null;
  if (!Object.prototype.hasOwnProperty.call(evidence, "hard_verdict") || evidence.hard_verdict !== null) {
    return null;
  }
  if (!Array.isArray(evidence.matched)) return null;
  const entries: EvidenceEntry[] = [];
  for (const item of evidence.matched) {
    const entry = parseEntry(item);
    if (entry) entries.push(entry);
  }
  return entries.length ? { dimension, entries } : null;
}

function parseGroups(value: CoreFacts["dimension_facts"]): readonly EvidenceGroup[] {
  if (!isRecord(value)) return [];
  const grouped = new Map<string, EvidenceEntry[]>();
  for (const block of Object.values(value)) {
    const parsed = parseDimension(block);
    if (!parsed) continue;
    const current = grouped.get(parsed.dimension) ?? [];
    current.push(...parsed.entries);
    grouped.set(parsed.dimension, current);
  }
  return [...grouped.entries()].map(([dimension, entries]) => ({ dimension, entries }));
}

export function DaliurenDimensionEvidence({ dimensionFacts = null }: DaliurenDimensionEvidenceProps) {
  const groups = parseGroups(dimensionFacts);
  if (!groups.length) return null;

  return (
    <section className={styles.panel} aria-label="维度证据" data-slot="dimension-evidence">
      {groups.map((group) => (
        <section className={styles.group} aria-label={group.dimension} key={group.dimension} role="group">
          <h3 className={styles.heading}>{group.dimension}</h3>
          <ul className={styles.list}>
            {group.entries.map((entry) => (
              <li className={styles.item} key={`${group.dimension}-${entry.ruleId}-${entry.fact}`}>
                {entry.anchor ? (
                  <details className={styles.drawer}>
                    <summary className={styles.summary}>
                      <span className={styles.badge} data-badge="evidence">
                        可核验
                      </span>
                      <span className={styles.rule}>{entry.ruleId}</span>
                      <span className={styles.fact}>{entry.fact}</span>
                    </summary>
                    {entry.pack ? <p className={styles.source}>{entry.pack}</p> : null}
                    <p className={styles.source}>{entry.anchor}</p>
                  </details>
                ) : (
                  <div className={styles.plain}>
                    <span className={styles.rule}>{entry.ruleId}</span>
                    <span className={styles.fact}>{entry.fact}</span>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </section>
  );
}
