import type { ReadingFact } from "./api";

export type BaziPillarPosition = "year" | "month" | "day" | "hour";

export type BaziStemTenGod = {
  stem: string;
  tenGod: string;
};

export type BaziPillarDetail = {
  position: BaziPillarPosition;
  label: string;
  pillar: string | null;
  branch: string | null;
  heavenlyStemTenGod: BaziStemTenGod | null;
  hiddenStems: string[];
  hiddenStemTenGods: BaziStemTenGod[];
  nayin: string | null;
};

export type BaziElement = "木" | "火" | "土" | "金" | "水";

export type BaziElementCount = {
  element: BaziElement;
  visibleCount: number;
  hiddenCount: number;
};

export type BaziAuxiliaryShenshaItem = {
  name: string;
  targetBranch: string | null;
  anchorPositions: BaziPillarPosition[];
  matchedPositions: BaziPillarPosition[];
};

export type BaziUnprojectedFact = {
  id: "kongwang" | "dishi" | "zizuo" | "sangong";
  label: string;
  status: "5.1 未投影";
};

export type BaziFactDisplay = {
  pillars: BaziPillarDetail[];
  elements: BaziElementCount[] | null;
  shenshaAuxiliary: { items: BaziAuxiliaryShenshaItem[] } | null;
  unprojected: BaziUnprojectedFact[];
};

const PILLAR_ORDER: Array<{ position: BaziPillarPosition; label: string }> = [
  { position: "year", label: "年柱" },
  { position: "month", label: "月柱" },
  { position: "day", label: "日柱" },
  { position: "hour", label: "时柱" },
];

const ELEMENT_ORDER: BaziElement[] = ["木", "火", "土", "金", "水"];

const UNPROJECTED_FACTS: BaziUnprojectedFact[] = [
  { id: "kongwang", label: "空亡", status: "5.1 未投影" },
  { id: "dishi", label: "地势", status: "5.1 未投影" },
  { id: "zizuo", label: "自坐", status: "5.1 未投影" },
  { id: "sangong", label: "三宫", status: "5.1 未投影" },
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nonEmptyString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function baziFactKey(ref: string): string | null {
  const match = ref.match(/\/calculated\/bazi\/([^/]+)$/);
  return match?.[1] ?? null;
}

function valuesByKey(facts: ReadingFact[]): Map<string, unknown> {
  const values = new Map<string, unknown>();
  for (const fact of facts) {
    const key = baziFactKey(fact.ref);
    if (key && !values.has(key)) {
      values.set(key, fact.value);
    }
  }
  return values;
}

function recordAt(value: unknown, key: BaziPillarPosition): Record<string, unknown> | null {
  if (!isRecord(value)) return null;
  const item = value[key];
  return isRecord(item) ? item : null;
}

function stringAt(value: unknown, key: BaziPillarPosition): string | null {
  return isRecord(value) ? nonEmptyString(value[key]) : null;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const text = nonEmptyString(item);
    return text ? [text] : [];
  });
}

function stemTenGod(value: unknown): BaziStemTenGod | null {
  if (!isRecord(value)) return null;
  const stem = nonEmptyString(value.stem);
  const tenGod = nonEmptyString(value.ten_god);
  return stem && tenGod ? { stem, tenGod } : null;
}

function stemTenGodList(value: unknown): BaziStemTenGod[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const mapped = stemTenGod(item);
    return mapped ? [mapped] : [];
  });
}

function inventoryCount(value: unknown, element: BaziElement): number {
  if (!isRecord(value)) return 0;
  const count = value[element];
  return typeof count === "number" && Number.isInteger(count) && count >= 0
    ? count
    : 0;
}

function pillarPositions(value: unknown): BaziPillarPosition[] {
  if (!Array.isArray(value)) return [];
  return value.filter(
    (item): item is BaziPillarPosition =>
      item === "year" ||
      item === "month" ||
      item === "day" ||
      item === "hour",
  );
}

function shenshaItems(value: unknown): BaziAuxiliaryShenshaItem[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!isRecord(item)) return [];
    const name = nonEmptyString(item.name);
    if (!name) return [];
    return [
      {
        name,
        targetBranch: nonEmptyString(item.target_branch),
        anchorPositions: pillarPositions(item.anchor_positions),
        matchedPositions: pillarPositions(item.matched_positions),
      },
    ];
  });
}

export function buildBaziFactDisplay(facts: ReadingFact[]): BaziFactDisplay {
  const values = valuesByKey(facts);
  const fourPillars = values.get("four_pillars");
  const hiddenStems = values.get("hidden_stems");
  const tenGods = values.get("ten_gods");
  const nayin = values.get("nayin");
  const elementInventory = values.get("element_inventory");
  const shenshaAuxiliary = values.get("shensha_auxiliary");
  const heavenlyStemTenGods = isRecord(tenGods)
    ? tenGods.heavenly_stems
    : null;
  const hiddenStemTenGods = isRecord(tenGods) ? tenGods.hidden_stems : null;
  const visibleElementCounts = isRecord(elementInventory)
    ? elementInventory.visible_stem_branch_counts
    : null;
  const hiddenElementCounts = isRecord(elementInventory)
    ? elementInventory.hidden_stem_occurrence_counts
    : null;

  return {
    pillars: PILLAR_ORDER.map(({ position, label }) => {
      const hiddenStem = recordAt(hiddenStems, position);
      const heavenlyTenGod = recordAt(heavenlyStemTenGods, position);
      const hiddenTenGods = isRecord(hiddenStemTenGods)
        ? hiddenStemTenGods[position]
        : null;
      return {
        position,
        label,
        pillar: stringAt(fourPillars, position),
        branch: hiddenStem ? nonEmptyString(hiddenStem.branch) : null,
        heavenlyStemTenGod: stemTenGod(heavenlyTenGod),
        hiddenStems: hiddenStem ? stringList(hiddenStem.stems) : [],
        hiddenStemTenGods: stemTenGodList(hiddenTenGods),
        nayin: stringAt(nayin, position),
      };
    }),
    elements: isRecord(elementInventory)
      ? ELEMENT_ORDER.map((element) => ({
          element,
          visibleCount: inventoryCount(visibleElementCounts, element),
          hiddenCount: inventoryCount(hiddenElementCounts, element),
        }))
      : null,
    shenshaAuxiliary: isRecord(shenshaAuxiliary)
      ? { items: shenshaItems(shenshaAuxiliary.calculated_items) }
      : null,
    unprojected: UNPROJECTED_FACTS.map((item) => ({ ...item })),
  };
}
