import type { MeihuaChartViewModel } from "@/view-models/registry";

export type MeihuaSlotId = "primary" | "mutual" | "changed";
export type MeihuaUnitId = `${MeihuaSlotId}-${"upper" | "lower"}`;

export type MeihuaS5Claim = {
  readonly claim_id: string;
  readonly text: string;
  readonly fact_refs: ReadonlyArray<string>;
  readonly finding_refs?: ReadonlyArray<string>;
};

export type MeihuaS5Anchor = {
  readonly unit: MeihuaUnitId;
  readonly slot: MeihuaSlotId;
  readonly polarityId: string | null;
  readonly label: string;
};

const SLOT_LABEL: Record<MeihuaSlotId, string> = {
  primary: "本卦",
  mutual: "互卦",
  changed: "变卦",
};

function unitLabel(unit: MeihuaUnitId): string {
  const slot = unit.startsWith("mutual")
    ? "mutual"
    : unit.startsWith("changed")
      ? "changed"
      : "primary";
  const position = unit.endsWith("lower") ? "下卦" : "上卦";
  return `${SLOT_LABEL[slot]}${position}`;
}

function plateFromSource(plate: string): MeihuaSlotId {
  if (plate.includes("mutual")) return "mutual";
  if (plate.includes("changed") || plate.includes("change")) return "changed";
  return "primary";
}

function plateFromRef(ref: string): MeihuaSlotId | null {
  if (/mutual|互卦/.test(ref)) return "mutual";
  if (/changed|change|变卦/.test(ref)) return "changed";
  if (/primary|本卦/.test(ref)) return "primary";
  return null;
}

function positionFromRef(ref: string): "upper" | "lower" | null {
  if (/lower|下卦/.test(ref)) return "lower";
  if (/upper|上卦/.test(ref)) return "upper";
  return null;
}

function presentSlots(view: MeihuaChartViewModel): ReadonlySet<MeihuaSlotId> {
  const slots = new Set<MeihuaSlotId>(["primary"]);
  if (view.mutual_hexagram) slots.add("mutual");
  if (view.changed_hexagram) slots.add("changed");
  return slots;
}

/** Map public claim refs onto S3 triad units / polarity rows. Do not invent targets. */
export function resolveMeihuaS5Anchors(
  refs: ReadonlyArray<string>,
  view: MeihuaChartViewModel,
): MeihuaS5Anchor[] {
  const allowed = presentSlots(view);
  const candidates = view.core_facts?.interpretive_candidates?.relation_candidates ?? [];
  const seen = new Set<string>();
  const anchors: MeihuaS5Anchor[] = [];

  function push(unit: MeihuaUnitId, polarityId: string | null, label: string) {
    const slot = plateFromSource(unit);
    if (!allowed.has(slot)) return;
    const key = `${unit}|${polarityId ?? ""}`;
    if (seen.has(key)) return;
    seen.add(key);
    anchors.push({ unit, slot, polarityId, label });
  }

  for (const ref of refs) {
    const candidate = candidates.find((item) => ref.includes(item.candidate_id));
    if (candidate) {
      push(
        `${plateFromSource(candidate.source_plate)}-${candidate.position}`,
        candidate.candidate_id,
        "极性证据",
      );
      continue;
    }
    if (/interpretive_candidates|relation_candidates|source_plate/.test(ref)) {
      const slot = plateFromRef(ref) ?? "primary";
      const position = positionFromRef(ref) ?? "upper";
      push(`${slot}-${position}`, null, "极性证据");
      continue;
    }
    if (/body_use/.test(ref)) {
      push(`primary-${view.body_use.body.position}`, null, unitLabel(`primary-${view.body_use.body.position}`));
      continue;
    }
    const slot = plateFromRef(ref);
    if (!slot) continue;
    const position = positionFromRef(ref) ?? "upper";
    const unit: MeihuaUnitId = `${slot}-${position}`;
    push(unit, null, unitLabel(unit));
  }

  return anchors;
}

export function meihuaS5ClaimRefs(claim: MeihuaS5Claim): string[] {
  return [...claim.fact_refs, ...(claim.finding_refs ?? [])];
}
