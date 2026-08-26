"use client";

import type { ZiweiCoreFacts } from "@/view-models/registry";

import styles from "./ziwei-source-pattern-drawer.module.css";

const BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"] as const;

const SOURCE_PACK_LABELS: Readonly<Record<string, string>> = {
  "ziwei/taiwei-fu": "太微赋",
  "ziwei/ziwei-doushu-quanshu": "紫微斗数全书",
  "ziwei/feixing-ziwei-doushu-yuanzhi": "華山陳希夷先生飛星紫微斗數原旨",
};

type PalaceLike = {
  readonly earthly_branch: string;
};

type PatternView = {
  readonly ruleId: string;
  readonly localRuleId: string;
  readonly title: string;
  readonly packLabel: string | null;
  readonly sourceAnchor: string;
  readonly audits: readonly string[];
  readonly branches: readonly string[];
};

export type ZiweiSourcePatternDrawerProps = {
  items: ZiweiCoreFacts["source_conditioned_patterns"] | null | undefined;
  palaces?: readonly PalaceLike[] | null;
  selectedBranch?: string | null;
  onSelectPattern?: (palaceBranch: string) => void;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function textField(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function textList(value: unknown): readonly string[] | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const items: string[] = [];
  for (const item of value) {
    const text = textField(item);
    if (!text) return null;
    items.push(text);
  }
  return items;
}

function normalizeFactPath(path: string): string {
  const raw = path.startsWith("fact:") ? path.slice("fact:".length) : path;
  return raw.startsWith("/") ? raw : `/${raw}`;
}

function branchFromFactPath(path: string, palaces: readonly PalaceLike[]): string | null {
  const segments = normalizeFactPath(path).split("/").filter(Boolean);
  for (const segment of segments) {
    if ((BRANCHES as readonly string[]).includes(segment)) return segment;
  }
  for (let index = 0; index < segments.length - 1; index += 1) {
    if (segments[index] !== "palaces" && segments[index] !== "palace_facts") continue;
    const raw = segments[index + 1] ?? "";
    if (!/^\d+$/.test(raw)) continue;
    const n = Number(raw);
    if (n < 0 || n >= palaces.length) return null;
    const branch = palaces[n]?.earthly_branch;
    return branch && (BRANCHES as readonly string[]).includes(branch) ? branch : null;
  }
  return null;
}

function parsePattern(value: unknown, palaces: readonly PalaceLike[]): PatternView | null {
  if (!isRecord(value)) return null;
  const ruleId = textField(value.rule_id);
  const localRuleId = textField(value.local_rule_id);
  const title = textField(value.title);
  const pack = textField(value.source_pack);
  const sourceAnchor = textField(value.source_anchor);
  const paths = textList(value.fact_paths);
  const audits = textList(value.predicate_audit);
  if (
    !ruleId ||
    !localRuleId ||
    !title ||
    !pack ||
    !sourceAnchor ||
    !paths ||
    !audits ||
    value.status !== "predicate_matched_not_verdict"
  ) {
    return null;
  }
  const branches = [
    ...new Set(paths.map((path) => branchFromFactPath(path, palaces)).filter((branch): branch is string => Boolean(branch))),
  ];
  return {
    ruleId,
    localRuleId,
    title,
    packLabel: SOURCE_PACK_LABELS[pack] ?? null,
    sourceAnchor,
    audits,
    branches,
  };
}

function parsePatterns(value: unknown, palaces: readonly PalaceLike[]): readonly PatternView[] | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const patterns: PatternView[] = [];
  for (const item of value) {
    const parsed = parsePattern(item, palaces);
    if (!parsed) return null;
    patterns.push(parsed);
  }
  return patterns;
}

export function ZiweiSourcePatternDrawer({
  items,
  palaces,
  selectedBranch = null,
  onSelectPattern,
}: ZiweiSourcePatternDrawerProps) {
  const patterns = parsePatterns(items, palaces ?? []);
  if (!patterns) return null;

  return (
    <section aria-label="古法命中" className={styles.panel} data-slot="source-patterns">
      <details className={styles.drawer}>
        <summary className={styles.summary}>{`命中古法 ${patterns.length} 条 · 可核验`}</summary>
        <ul className={styles.list}>
          {patterns.map((pattern) => {
            const highlighted = Boolean(selectedBranch && pattern.branches.includes(selectedBranch));
            return (
              <li
                className={styles.item}
                data-highlight={highlighted ? "true" : undefined}
                key={pattern.ruleId}
              >
                {pattern.branches.length ? (
                  <button
                    className={styles.title}
                    type="button"
                    onClick={() => onSelectPattern?.(pattern.branches[0]!)}
                  >
                    {pattern.title}
                  </button>
                ) : (
                  <p className={styles.title}>{pattern.title}</p>
                )}
                {pattern.packLabel ? <p className={styles.pack}>{pattern.packLabel}</p> : null}
                <p className={styles.note}>条件命中，非断语</p>
                <p className={styles.anchor}>{pattern.sourceAnchor}</p>
                <ul className={styles.audits}>
                  {pattern.audits.map((audit) => (
                    <li key={audit}>{audit}</li>
                  ))}
                </ul>
              </li>
            );
          })}
        </ul>
      </details>
    </section>
  );
}
