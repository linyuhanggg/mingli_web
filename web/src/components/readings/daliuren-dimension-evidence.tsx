"use client";

import type {
  DaliurenChartViewModel,
  DaliurenDimensionObservationMap,
  DaliurenRelationshipObservation,
  DaliurenTimingObservation,
} from "@/view-models/registry";

import styles from "./daliuren-dimension-evidence.module.css";

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;

export type DaliurenDimensionEvidenceProps = {
  dimensionFacts?: CoreFacts["dimension_facts"];
};

const TEXT_KEYS = ["display_text", "fact_text", "text", "label", "name", "note"] as const;
const RELATION_FACTS: Readonly<Record<DaliurenRelationshipObservation["relation"], string>> = {
  object_overcomes_subject: "客体克主体",
  subject_overcomes_object: "主体克客体",
};
const RELATIVE_SPEED_FACTS: Readonly<
  Record<NonNullable<DaliurenTimingObservation["relative_speed"]>, string>
> = {
  relatively_faster: "较快",
  relatively_slower: "较慢",
};
const RELATIONSHIP_OBSERVATION_KEYS = ["relation"] as const;
const TIMING_OBSERVATION_KEYS = ["candidate_branch", "candidate_date", "relative_speed"] as const;
const CANDIDATE_BRANCH_KEYS = ["anchor_earth_branch", "branch", "source_rule"] as const;
const CANDIDATE_DATE_KEYS = [
  "id",
  "role",
  "anchor_earth_branch",
  "branch",
  "solar_date",
  "day_ganzhi",
  "days_after_cast",
  "source_pack",
  "source_rule",
  "candidate_not_guarantee",
] as const;

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

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => Object.prototype.hasOwnProperty.call(value, key));
}

function hasOwnKey<T extends object>(value: T, key: PropertyKey): key is keyof T {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function firstAllowedText(value: unknown): string | null {
  if (!isRecord(value)) return null;
  for (const key of TEXT_KEYS) {
    const text = readString(value, key);
    if (text) return text;
  }
  return null;
}

function isRelationshipObservation(value: unknown): value is DaliurenRelationshipObservation {
  if (!isRecord(value) || !hasExactKeys(value, RELATIONSHIP_OBSERVATION_KEYS)) return false;
  const relation = readString(value, "relation");
  return Boolean(relation && hasOwnKey(RELATION_FACTS, relation));
}

function isCandidateBranch(value: unknown): value is DaliurenTimingObservation["candidate_branch"] {
  return (
    isRecord(value) &&
    hasExactKeys(value, CANDIDATE_BRANCH_KEYS) &&
    Boolean(readString(value, "anchor_earth_branch")) &&
    Boolean(readString(value, "branch")) &&
    value.source_rule === "LM-R21"
  );
}

function isCandidateDate(value: unknown): value is NonNullable<DaliurenTimingObservation["candidate_date"]> {
  return (
    isRecord(value) &&
    hasExactKeys(value, CANDIDATE_DATE_KEYS) &&
    value.id === "initial_group_upper_candidate" &&
    value.role === "event_response_candidate" &&
    Boolean(readString(value, "anchor_earth_branch")) &&
    Boolean(readString(value, "branch")) &&
    Boolean(readString(value, "solar_date")) &&
    Boolean(readString(value, "day_ganzhi")) &&
    typeof value.days_after_cast === "number" &&
    Number.isInteger(value.days_after_cast) &&
    Boolean(readString(value, "source_pack")) &&
    value.source_rule === "LM-R21" &&
    value.candidate_not_guarantee === true
  );
}

function isTimingObservation(value: unknown): value is DaliurenTimingObservation {
  if (!isRecord(value) || !hasExactKeys(value, TIMING_OBSERVATION_KEYS)) return false;
  const candidateBranch = value.candidate_branch;
  const candidateDate = value.candidate_date;
  const relativeSpeed = value.relative_speed;
  if (!isCandidateBranch(candidateBranch)) return false;
  if (candidateDate !== null && !isCandidateDate(candidateDate)) return false;
  if (
    relativeSpeed !== null &&
    (typeof relativeSpeed !== "string" || !hasOwnKey(RELATIVE_SPEED_FACTS, relativeSpeed))
  ) {
    return false;
  }
  return (
    candidateDate === null ||
    (candidateDate.branch === candidateBranch.branch &&
      candidateDate.anchor_earth_branch === candidateBranch.anchor_earth_branch &&
      candidateDate.source_rule === candidateBranch.source_rule)
  );
}

function relationshipFact(value: unknown): string | null {
  return isRelationshipObservation(value) ? `主客关系：${RELATION_FACTS[value.relation]}` : null;
}

function timingFact(value: unknown): string | null {
  if (!isTimingObservation(value)) return null;
  const facts = [`规则候选支：${value.candidate_branch.branch}`];
  if (value.candidate_date) {
    facts.push(`候选日期：${value.candidate_date.solar_date}（${value.candidate_date.day_ganzhi}日）`);
  }
  if (value.relative_speed) {
    facts.push(`相对节奏：${RELATIVE_SPEED_FACTS[value.relative_speed]}`);
  }
  return facts.join(" · ");
}

const RUNTIME_OBSERVATION_FACTS = Object.freeze({
  relationship: relationshipFact,
  timing: timingFact,
}) satisfies Readonly<{
  [Dimension in keyof DaliurenDimensionObservationMap]: (value: unknown) => string | null;
}>;

function observationFact(dimension: string, value: unknown): string | null {
  if (dimension === "relationship" || dimension === "timing") {
    return RUNTIME_OBSERVATION_FACTS[dimension](value);
  }
  return firstAllowedText(value);
}

function parseEntry(value: unknown, dimension: string): EvidenceEntry | null {
  if (!isRecord(value)) return null;
  const ruleId = readString(value, "rule_id");
  const fact = observationFact(dimension, value.observation);
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
    const entry = parseEntry(item, dimension);
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
