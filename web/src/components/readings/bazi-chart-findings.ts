const BAZI_RUNTIME_FINDING_TITLES = {
  "bazi.month-order-state-v1": "月令状态",
  "bazi.day-master-root-support-v1": "日主根气与生扶证据",
  "bazi.ziping-pattern-entry-v1": "子平格局入口",
  "bazi.tiaohou-priority-v1": "调候候选次序",
  "bazi.pillar-roles-v1": "四柱判读次序",
  "bazi.three-yuan-structure-v1": "天地人三元结构",
  "bazi.element-flow-inventory-v1": "五行流通事实",
} as const;

type BaziRuntimeFindingId = keyof typeof BAZI_RUNTIME_FINDING_TITLES;

export type BaziRuntimeFinding = Readonly<{
  id: BaziRuntimeFindingId;
  title: string;
  publicText: string;
}>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasNonEmptyStringRefs(value: unknown): value is string[] {
  return Array.isArray(value)
    && value.length > 0
    && value.every((item) => typeof item === "string" && item.trim().length > 0);
}

function isAdmittedFindingId(value: unknown): value is BaziRuntimeFindingId {
  return typeof value === "string" && value in BAZI_RUNTIME_FINDING_TITLES;
}

/**
 * Project opaque Runtime findings into the small product-approved public set.
 * Unknown or weakly grounded units disappear instead of leaking identifiers or
 * turning provider-owned data into frontend-authored interpretation.
 */
export function projectBaziRuntimeFindings(
  findings: ReadonlyArray<unknown> | null | undefined,
): BaziRuntimeFinding[] {
  if (!findings?.length) return [];

  const projected: BaziRuntimeFinding[] = [];
  const seen = new Set<BaziRuntimeFindingId>();
  for (const raw of findings) {
    if (!isRecord(raw) || raw.kind_id !== "kind.tendency") continue;
    if (raw.support_mode !== "exact") continue;
    if (!hasNonEmptyStringRefs(raw.fact_refs) || !hasNonEmptyStringRefs(raw.evidence_refs)) {
      continue;
    }
    if (typeof raw.public_text !== "string" || !raw.public_text.trim()) continue;
    if (!isRecord(raw.data) || raw.data.hard_verdict !== null) continue;
    const id = raw.data.claim_unit_id;
    if (!isAdmittedFindingId(id) || seen.has(id)) continue;

    seen.add(id);
    projected.push({
      id,
      title: BAZI_RUNTIME_FINDING_TITLES[id],
      publicText: raw.public_text.trim(),
    });
  }
  return projected;
}
