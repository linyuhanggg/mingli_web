import { LIUYAO_LINE_NAMES } from "@/components/task/liuyao-entry-copy";
import type { LiuyaoChartViewModel, StructuredFactObject } from "@/view-models/registry";

export type LiuyaoLinePosition = 1 | 2 | 3 | 4 | 5 | 6;

export type LiuyaoS5Claim = {
  readonly claim_id: string;
  readonly text: string;
  readonly fact_refs: ReadonlyArray<string>;
  readonly finding_refs?: ReadonlyArray<string>;
};

export type LiuyaoS5Anchor = {
  readonly kind: "line" | "relation" | "pattern";
  readonly line: LiuyaoLinePosition | null;
  readonly relationKey: string | null;
  readonly patternId: string | null;
  readonly label: string;
};

const LINE_PATH_PREFIXES = [
  "/chart_facts/output/line_facts",
  "/chart_facts/output/lines",
  "/chart_facts/output/najia",
  "/chart_facts/output/six_relatives",
  "/chart_facts/output/six_spirits",
  "/chart_facts/output/month_day_strength",
] as const;

const RELATION_KEYS = ["relation_facts", "returning_relations"] as const;

function isRecord(value: unknown): value is StructuredFactObject {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function textField(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function normalizeFactPath(path: string): string {
  const raw = path.startsWith("fact:") ? path.slice("fact:".length) : path;
  const slash = raw.indexOf("/chart_facts/");
  const chartPath = slash >= 0 ? raw.slice(slash) : raw.startsWith("/") ? raw : `/${raw}`;
  return chartPath;
}

function lineFromIndexedPath(path: string): LiuyaoLinePosition | null {
  const normalized = normalizeFactPath(path);
  for (const prefix of LINE_PATH_PREFIXES) {
    if (normalized !== prefix && !normalized.startsWith(`${prefix}/`)) continue;
    const next = normalized.slice(prefix.length + 1).split("/")[0];
    if (!/^[0-5]$/.test(next)) return null;
    return (Number(next) + 1) as LiuyaoLinePosition;
  }
  return null;
}

function indexFromKeyedPath(path: string, key: string): number | null {
  const normalized = normalizeFactPath(path);
  const prefix = `/chart_facts/output/${key}`;
  if (normalized !== prefix && !normalized.startsWith(`${prefix}/`)) return null;
  if (normalized === prefix) return 0;
  const next = normalized.slice(prefix.length + 1).split("/")[0];
  if (!/^\d+$/.test(next)) return 0;
  return Number(next);
}

function lineFromNajia(
  najia: unknown,
  original: unknown,
): LiuyaoLinePosition | null {
  if (!Array.isArray(najia) || !isRecord(original)) return null;
  const ganzhi = textField(original.ganzhi);
  if (!ganzhi) return null;
  let found: LiuyaoLinePosition | null = null;
  for (const [index, item] of najia.entries()) {
    if (!isRecord(item) || textField(item.ganzhi) !== ganzhi) continue;
    if (found) return null;
    found = (index + 1) as LiuyaoLinePosition;
  }
  return found;
}

function patternId(value: StructuredFactObject): string | null {
  return textField(value.local_rule_id) ?? textField(value.rule_id);
}

function presentLine(view: LiuyaoChartViewModel, line: LiuyaoLinePosition | null): boolean {
  return line !== null && view.lines.some((item) => item.position === line);
}

/** Map public claim refs onto existing S3 爻位 / 关系 / 古籍命中. Do not invent targets. */
export function resolveLiuyaoS5Anchors(
  refs: ReadonlyArray<string>,
  view: LiuyaoChartViewModel,
): LiuyaoS5Anchor[] {
  const facts = view.core_facts;
  const seen = new Set<string>();
  const anchors: LiuyaoS5Anchor[] = [];

  function push(anchor: LiuyaoS5Anchor) {
    if (anchor.line !== null && !presentLine(view, anchor.line)) return;
    const key = `${anchor.kind}|${anchor.line ?? ""}|${anchor.relationKey ?? ""}|${anchor.patternId ?? ""}`;
    if (seen.has(key)) return;
    seen.add(key);
    anchors.push(anchor);
  }

  for (const ref of refs) {
    const patterns = facts?.source_conditioned_patterns;
    if (Array.isArray(patterns) && patterns.length > 0) {
      const byId = patterns.find((item) => {
        const id = patternId(item);
        return Boolean(id && (ref.includes(id) || ref.includes(item.rule_id)));
      });
      const byIndex = indexFromKeyedPath(ref, "source_conditioned_patterns");
      const pattern =
        byId ??
        (byIndex !== null && isRecord(patterns[byIndex]) ? patterns[byIndex] : null);
      if (pattern && isRecord(pattern) && pattern.status === "predicate_matched_not_verdict") {
        const id = patternId(pattern);
        if (id) {
          const paths = Array.isArray(pattern.fact_paths)
            ? pattern.fact_paths.filter((item): item is string => typeof item === "string")
            : [];
          const line = paths.map(lineFromIndexedPath).find((item): item is LiuyaoLinePosition => item !== null) ?? null;
          push({
            kind: "pattern",
            line,
            relationKey: null,
            patternId: id,
            label: "古法命中",
          });
          continue;
        }
      }
    }

    let matchedRelation = false;
    for (const key of RELATION_KEYS) {
      const rows = facts?.[key];
      if (!Array.isArray(rows) || rows.length === 0) continue;
      const index = indexFromKeyedPath(ref, key);
      if (index === null || !isRecord(rows[index])) continue;
      const row = rows[index];
      if (row.fact_status !== "calculated_relation_not_verdict") continue;
      const relationKey = `${key === "relation_facts" ? "relation" : "returning"}:${index}`;
      push({
        kind: "relation",
        line: lineFromNajia(facts?.najia, row.original),
        relationKey,
        patternId: null,
        label: key === "relation_facts" ? "关系事实" : "回头生克",
      });
      matchedRelation = true;
      break;
    }
    if (matchedRelation) continue;

    const line = lineFromIndexedPath(ref);
    if (line) {
      push({
        kind: "line",
        line,
        relationKey: null,
        patternId: null,
        label: LIUYAO_LINE_NAMES[line - 1],
      });
    }
  }

  return anchors;
}

export function liuyaoS5ClaimRefs(claim: LiuyaoS5Claim): string[] {
  return [...claim.fact_refs, ...(claim.finding_refs ?? [])];
}

export function liuyaoS5TargetId(anchor: LiuyaoS5Anchor): string {
  if (anchor.kind === "pattern" && anchor.patternId) return `liuyao-pattern-${anchor.patternId}`;
  if (anchor.kind === "relation" && anchor.relationKey) return `liuyao-relation-${anchor.relationKey}`;
  if (anchor.line) return `liuyao-line-${anchor.line}`;
  return "liuyao-s3-board";
}
