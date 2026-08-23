"use client";

import Link from "next/link";
import { useState } from "react";

import { Drawer } from "@/components/ui/drawer";
import { Status } from "@/components/ui/status";
import { LIUYAO_LINE_NAMES } from "@/components/task/liuyao-entry-copy";
import type { LiuyaoChartViewModel, StructuredFactObject } from "@/view-models/registry";

import {
  HexagramHeader,
  LineGlyph,
  hexagramLinesFromTrigrams,
} from "./hexagram-glyphs";
import {
  liuyaoS5ClaimRefs,
  liuyaoS5TargetId,
  resolveLiuyaoS5Anchors,
  type LiuyaoS5Anchor,
  type LiuyaoS5Claim,
} from "./liuyao-s5-anchors";
import styles from "./liuyao-line-tower.module.css";

type LineValue = LiuyaoChartViewModel["lines"][number]["value"];
type LinePosition = 1 | 2 | 3 | 4 | 5 | 6;
type ElementName = "木" | "火" | "土" | "金" | "水";
type NajiaCell = {
  readonly ganzhi: string;
  readonly branch: string;
  readonly element: ElementName;
};

const ELEMENTS: ReadonlyArray<ElementName> = ["木", "火", "土", "金", "水"];
const RELATIVES = ["兄弟", "子孙", "妻财", "官鬼", "父母"] as const;
type HiddenCell = {
  readonly relative: (typeof RELATIVES)[number];
  readonly branch: string;
  readonly element: ElementName;
};
const STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"] as const;
const SPIRITS = ["青龙", "朱雀", "勾陈", "螣蛇", "腾蛇", "白虎", "玄武"] as const;
const CASTING_LABELS: Record<string, string> = {
  coins: "三枚硬币记录",
  digital_coin: "三枚硬币记录",
  manual: "手动记录",
  supplied_complete_cast: "提供完整卦象",
};
const QUESTION_FOLD = 48;
const SKU_COPY =
  "一事一问：只深读当前这件已起之卦的用神与世应证据，不另起他事，也不把证据翻译成成败。";

export type LiuyaoS4Offer = {
  name: string;
  coverage: string;
  priceText: string;
  refundBoundary: string;
};

export type LiuyaoS4Phase = "entry" | "confirming" | "locked" | "gateway_unavailable";
export type { LiuyaoS5Claim };
const SOURCE_PACK_LABELS: Readonly<Record<string, string>> = {
  "divination/huangjin-ce": "黄金策",
  "divination/zengshan-buyi": "增删卜易",
  "divination/huozhu-lin": "火珠林",
  "divination/bushi-zhengzong": "卜筮正宗",
};
const LINE_PATH_PREFIXES = [
  "/chart_facts/output/line_facts",
  "/chart_facts/output/lines",
  "/chart_facts/output/najia",
  "/chart_facts/output/six_relatives",
  "/chart_facts/output/six_spirits",
  "/chart_facts/output/month_day_strength",
] as const;
const ELEMENT_TOKEN: Record<ElementName, string> = {
  木: "wood",
  火: "fire",
  土: "earth",
  金: "metal",
  水: "water",
};

function glyphFromValue(value: LineValue): { yang: boolean; moving: boolean } {
  return {
    yang: value === 7 || value === 9,
    moving: value === 6 || value === 9,
  };
}

function isRecord(value: unknown): value is StructuredFactObject {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function textField(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function parseElement(value: unknown): ElementName | null {
  return typeof value === "string" && ELEMENTS.includes(value as ElementName)
    ? (value as ElementName)
    : null;
}

function parsePosition(value: unknown): LinePosition | null {
  return value === 1 || value === 2 || value === 3 || value === 4 || value === 5 || value === 6
    ? value
    : null;
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

function lineFromFactPath(path: string): LinePosition | null {
  const normalized = normalizeFactPath(path);
  for (const prefix of LINE_PATH_PREFIXES) {
    if (normalized !== prefix && !normalized.startsWith(`${prefix}/`)) continue;
    const next = normalized.slice(prefix.length + 1).split("/")[0];
    if (!/^[0-5]$/.test(next)) return null;
    return (Number(next) + 1) as LinePosition;
  }
  return null;
}

function readableAudit(value: string): string {
  return /[\u3400-\u9fff]/u.test(value) ? value : "服务端已记录";
}

type SourcePatternView = {
  readonly ruleId: string;
  readonly localRuleId: string;
  readonly title: string;
  readonly packLabel: string | null;
  readonly sourceAnchor: string;
  readonly audits: readonly string[];
  readonly lines: readonly LinePosition[];
};

function parseSourcePattern(value: unknown): SourcePatternView | null {
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
  const lines = [...new Set(paths.map(lineFromFactPath).filter((line): line is LinePosition => line !== null))];
  return {
    ruleId,
    localRuleId,
    title,
    packLabel: SOURCE_PACK_LABELS[pack] ?? null,
    sourceAnchor,
    audits: audits.map(readableAudit),
    lines,
  };
}

function parseSourcePatterns(value: unknown): readonly SourcePatternView[] | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const patterns: SourcePatternView[] = [];
  for (const item of value) {
    const parsed = parseSourcePattern(item);
    if (!parsed) return null;
    patterns.push(parsed);
  }
  return patterns;
}

function parseNajiaColumn(value: unknown): readonly NajiaCell[] | null {
  if (!Array.isArray(value) || value.length !== 6) return null;
  const cells: NajiaCell[] = [];
  for (const item of value) {
    if (!isRecord(item)) return null;
    const element = parseElement(item.element);
    const stem = textField(item.stem);
    const branch = textField(item.branch);
    const ganzhi = textField(item.ganzhi);
    if (!element || !stem || !branch || !ganzhi) return null;
    cells.push({ ganzhi, branch, element });
  }
  return cells;
}

function parseRelativeColumn(value: unknown): readonly string[] | null {
  if (!Array.isArray(value) || value.length !== 6) return null;
  const cells: string[] = [];
  for (const item of value) {
    if (typeof item !== "string" || !RELATIVES.includes(item as (typeof RELATIVES)[number])) {
      return null;
    }
    cells.push(item);
  }
  return cells;
}

function parseSpiritColumn(value: unknown): readonly string[] | null {
  if (!Array.isArray(value) || value.length !== 6) return null;
  const cells: string[] = [];
  for (const item of value) {
    if (typeof item !== "string" || !SPIRITS.includes(item as (typeof SPIRITS)[number])) {
      return null;
    }
    cells.push(item);
  }
  return cells;
}

function parseShiYing(value: unknown): { readonly shi: LinePosition; readonly ying: LinePosition } | null {
  if (!isRecord(value)) return null;
  const shi = parsePosition(value.shi);
  const ying = parsePosition(value.ying);
  if (!shi || !ying) return null;
  return { shi, ying };
}

function parseChangedPlate(value: unknown): readonly boolean[] | null {
  if (!Array.isArray(value) || value.length !== 6) return null;
  const cells: boolean[] = [];
  for (let index = 0; index < 6; index += 1) {
    const item = value[index];
    if (!isRecord(item) || item.line !== index + 1) return null;
    if (item.yin_yang === "阳") cells.push(true);
    else if (item.yin_yang === "阴") cells.push(false);
    else return null;
  }
  return cells;
}

function parseCalendar(value: unknown): { readonly month_branch: string; readonly day_ganzhi: string } | null {
  if (!isRecord(value)) return null;
  const monthBranch = textField(value.month_branch);
  const dayGanzhi = textField(value.day_ganzhi);
  if (
    !monthBranch ||
    !dayGanzhi ||
    !textField(value.month_ganzhi) ||
    !textField(value.day_stem) ||
    !textField(value.day_branch)
  ) {
    return null;
  }
  return { month_branch: monthBranch, day_ganzhi: dayGanzhi };
}

function parseXunkong(value: unknown): readonly [string, string] | null {
  if (!isRecord(value) || !Array.isArray(value.void_branches) || value.void_branches.length !== 2) {
    return null;
  }
  if (!textField(value.day_ganzhi) || !textField(value.source_dependency_id)) return null;
  const first = textField(value.void_branches[0]);
  const second = textField(value.void_branches[1]);
  if (!first || !second) return null;
  return [first, second];
}

function parseCastingMethod(value: unknown): string | null {
  return typeof value === "string" && value in CASTING_LABELS ? CASTING_LABELS[value] : null;
}

type RelationFact = {
  readonly originalGanzhi: string;
  readonly changedGanzhi: string;
  readonly relations: readonly string[];
  readonly line: LinePosition | null;
  readonly sentence: string;
};

function parseNajiaEntry(value: unknown): { readonly ganzhi: string } | null {
  if (!isRecord(value)) return null;
  const element = parseElement(value.element);
  const stem = textField(value.stem);
  const branch = textField(value.branch);
  const ganzhi = textField(value.ganzhi);
  const source = textField(value.source_dependency_id);
  if (!element || !stem || !branch || !ganzhi || !source) return null;
  return { ganzhi };
}

function matchLineByGanzhi(najia: readonly NajiaCell[] | null, ganzhi: string): LinePosition | null {
  if (!najia) return null;
  let found: LinePosition | null = null;
  for (let index = 0; index < najia.length; index += 1) {
    if (najia[index]?.ganzhi !== ganzhi) continue;
    if (found) return null;
    found = (index + 1) as LinePosition;
  }
  return found;
}

function parseRelationFacts(
  value: unknown,
  najia: readonly NajiaCell[] | null,
): readonly RelationFact[] | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const rows: RelationFact[] = [];
  for (const item of value) {
    if (!isRecord(item) || item.fact_status !== "calculated_relation_not_verdict") return null;
    if (!textField(item.source_dependency_id) || !Array.isArray(item.relations) || item.relations.length < 1) {
      return null;
    }
    const original = parseNajiaEntry(item.original);
    const changed = parseNajiaEntry(item.changed);
    const relations: string[] = [];
    for (const relation of item.relations) {
      const label = textField(relation);
      if (!label) return null;
      relations.push(label);
    }
    if (!original || !changed) return null;
    const line = matchLineByGanzhi(najia, original.ganzhi);
    const joined = relations.join("、");
    rows.push({
      originalGanzhi: original.ganzhi,
      changedGanzhi: changed.ganzhi,
      relations,
      line,
      sentence: line
        ? `${LIUYAO_LINE_NAMES[line - 1]}动化${joined}`
        : `${original.ganzhi}化${changed.ganzhi} · ${joined}`,
    });
  }
  return rows;
}

const TARGET_SOURCES = ["visible_line", "changed_line", "hidden_line"] as const;
type TargetSource = (typeof TARGET_SOURCES)[number];
const TARGET_SOURCE_LABEL: Record<TargetSource, string | null> = {
  visible_line: null,
  changed_line: "变卦",
  hidden_line: "伏神",
};

type ShiYingMovingRow = {
  readonly sentence: string;
  readonly line: LinePosition;
};

function parseRoles(value: unknown): readonly string[] | null {
  if (!Array.isArray(value)) return null;
  const roles: string[] = [];
  for (const item of value) {
    if (item !== "世" && item !== "应") return null;
    roles.push(item);
  }
  return roles;
}

function parseSharedTrines(value: unknown): boolean {
  if (!Array.isArray(value)) return false;
  for (const group of value) {
    if (!Array.isArray(group) || group.length !== 3) return false;
    for (const item of group) {
      if (!textField(item)) return false;
    }
  }
  return true;
}

function parseTargetSource(value: unknown): TargetSource | null {
  return typeof value === "string" && TARGET_SOURCES.includes(value as TargetSource)
    ? (value as TargetSource)
    : null;
}

function relationClause(elementRelation: string, branchRelation: string): string {
  return branchRelation === "无直接冲合" ? elementRelation : `${elementRelation} · ${branchRelation}`;
}

function parseShiYingRelationFact(value: unknown, requireAnchor: boolean): ShiYingMovingRow | null {
  if (!isRecord(value) || value.fact_status !== "calculated_relation_not_verdict") return null;
  if (!textField(value.source_dependency_id)) return null;
  const sourceLine = parsePosition(value.source_line);
  const targetLine = parsePosition(value.target_line);
  const sourceLabel = textField(value.source_role_label);
  const targetLabel = textField(value.target_role_label);
  const elementRelation = textField(value.element_relation);
  const branchRelation = textField(value.branch_relation);
  const targetRelative =
    typeof value.target_relative === "string" && RELATIVES.includes(value.target_relative as (typeof RELATIVES)[number])
      ? value.target_relative
      : null;
  const targetSource = parseTargetSource(value.target_source);
  if (
    !sourceLine ||
    !targetLine ||
    !sourceLabel ||
    !targetLabel ||
    !elementRelation ||
    !branchRelation ||
    !targetRelative ||
    !targetSource ||
    !parseNajiaEntry(value.source_najia) ||
    !parseNajiaEntry(value.target_najia) ||
    !parseRoles(value.source_roles) ||
    !parseRoles(value.target_roles) ||
    !parseSharedTrines(value.shared_trines)
  ) {
    return null;
  }
  if (requireAnchor) {
    const shiLine = parsePosition(value.shi_line);
    const yingLine = parsePosition(value.ying_line);
    if (shiLine !== sourceLine || yingLine !== targetLine) return null;
  }
  const clause = relationClause(elementRelation, branchRelation);
  if (requireAnchor) {
    return {
      line: sourceLine,
      sentence: `${LIUYAO_LINE_NAMES[sourceLine - 1]}${sourceLabel}与${LIUYAO_LINE_NAMES[targetLine - 1]}${targetLabel} · ${clause}`,
    };
  }
  const where = TARGET_SOURCE_LABEL[targetSource];
  return {
    line: sourceLine,
    sentence: `${LIUYAO_LINE_NAMES[sourceLine - 1]}${sourceLabel}与${LIUYAO_LINE_NAMES[targetLine - 1]}${targetRelative}${where ? `（${where}）` : ""} · ${clause}`,
  };
}

function parseShiYingMovingRelations(value: unknown): readonly ShiYingMovingRow[] | null {
  if (!isRecord(value) || value.fact_status !== "calculated_relation_not_verdict") return null;
  if (!textField(value.source_dependency_id) || !Array.isArray(value.moving_to_candidates)) return null;
  const anchor = parseShiYingRelationFact(value.shi_ying, true);
  if (!anchor) return null;
  const rows: ShiYingMovingRow[] = [anchor];
  for (const item of value.moving_to_candidates) {
    const row = parseShiYingRelationFact(item, false);
    if (!row) return null;
    rows.push(row);
  }
  return rows;
}

const SEASONAL_STATES = ["旺", "相", "休", "囚", "死"] as const;
type SeasonalState = (typeof SEASONAL_STATES)[number];

type MonthDayRow = {
  readonly sentence: string;
  readonly line: LinePosition;
};

function parseSeasonalState(value: unknown): SeasonalState | null {
  return typeof value === "string" && SEASONAL_STATES.includes(value as SeasonalState)
    ? (value as SeasonalState)
    : null;
}

function parseLineBranchElement(
  value: unknown,
): readonly { readonly branch: string; readonly element: ElementName }[] | null {
  if (!Array.isArray(value) || value.length !== 6) return null;
  const cells: { readonly branch: string; readonly element: ElementName }[] = [];
  for (const item of value) {
    if (!isRecord(item)) return null;
    const branch = textField(item.branch);
    const element = parseElement(item.element);
    if (!branch || !element || !textField(item.stem) || !textField(item.ganzhi)) return null;
    cells.push({ branch, element });
  }
  return cells;
}

function parseMonthDaySide(value: unknown, kind: "month" | "day"): boolean {
  if (!isRecord(value)) return false;
  if (!textField(value.branch) || !textField(value.branch_relation) || !textField(value.element_relation)) {
    return false;
  }
  if (!parseElement(value.element) || !parseSharedTrines(value.shared_trines)) return false;
  return kind === "month" ? typeof value.break === "boolean" : typeof value.clash === "boolean";
}

function parseSixSpiritProfile(value: unknown): string | null {
  if (!isRecord(value)) return null;
  const stem = textField(value.day_stem);
  if (!stem || !STEMS.includes(stem as (typeof STEMS)[number])) return null;
  if (!textField(value.source_dependency_id)) return null;
  return `${stem}日起六神`;
}

const LINE_STATUS_LABEL = {
  adjudicated_unique_visible_line: "唯一可见候选已定位",
  adjudicated_single_moving_visible_line: "单一动爻候选已定位",
  unresolved_multiple_visible_lines: "多个候选并存",
  unresolved_no_visible_line: "卦中不现",
} as const;

const DERIVATION_LABEL = {
  verified_role_plus_runtime_unique_visible_candidate: "按已裁定角色与盘内唯一可见候选",
  verified_two_present_rule_plus_runtime_single_moving_candidate: "按两现取动爻规则与盘内单一发动候选",
  verified_role_plus_runtime_multiple_visible_candidates: "按已裁定角色，盘内多个可见候选并存",
  verified_role_plus_runtime_no_visible_candidate: "按已裁定角色，卦中不现",
} as const;

const SIGNAL_LABEL = {
  seasonal_support: "得令",
  seasonal_weakening: "失令",
  month_break: "月破",
  day_clash: "日冲",
  xunkong: "旬空",
  moving_line: "动爻",
} as const;

const PLACE_LABEL = {
  visible_line: "本卦",
  changed_line: "变爻",
  hidden_line: "伏神",
} as const;

const ROLE_ORDER = ["妻财", "子孙", "兄弟", "官鬼", "父母"] as const;
const STRENGTH_BANDS = ["旺相", "休囚"] as const;
const STRENGTH_BOUNDARY = "以上为月令强弱证据，取用与断事属流派裁定，本页不代作结论";

type SourceBadge = {
  readonly pack: string;
  readonly ruleId: string;
  readonly sourceAnchor: string;
};

type RoleCard = {
  readonly primary: string;
  readonly supporting: readonly string[];
  readonly obstacles: readonly string[];
  readonly source: SourceBadge;
  readonly unresolved: readonly string[];
};

type SpecificLineView = {
  readonly statusLabel: string;
  readonly derivation: string | null;
  readonly source: SourceBadge | null;
  readonly candidates: readonly LinePosition[];
  readonly hint: string | null;
  readonly usefulLine: LinePosition | null;
};

type StrengthRow = {
  readonly key: string;
  readonly line: LinePosition;
  readonly place: string;
  readonly najia: string | null;
  readonly seasonal: string;
  readonly band: string;
  readonly title: string;
  readonly signals: readonly string[];
  readonly source: SourceBadge | null;
};

type StrengthGroup = {
  readonly relative: string;
  readonly rows: readonly StrengthRow[];
};

type UsefulSpiritView = {
  readonly reason: string | null;
  readonly role: RoleCard | "not_requested" | null;
  readonly line: SpecificLineView | null;
  readonly usefulLine: LinePosition | null;
  readonly groups: readonly StrengthGroup[] | null;
};

function parseSourceBadge(value: unknown, ruleId: "HJC-R009" | "ZR-04-04" | "ZR-05-05"): SourceBadge | null {
  if (!isRecord(value) || value.verification_status !== "verified") return null;
  const pack = textField(value.pack);
  const anchor = textField(value.source_anchor);
  if (!pack || value.rule_id !== ruleId || !anchor || !textField(value.binding_digest)) return null;
  return { pack, ruleId, sourceAnchor: anchor };
}

function parseStringList(value: unknown): readonly string[] | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const items: string[] = [];
  for (const item of value) {
    const text = textField(item);
    if (!text) return null;
    items.push(text);
  }
  return items;
}

function parseLineList(value: unknown): readonly LinePosition[] | null {
  if (!Array.isArray(value)) return null;
  const lines: LinePosition[] = [];
  for (const item of value) {
    const line = parsePosition(item);
    if (!line || lines.includes(line)) return null;
    lines.push(line);
  }
  return lines;
}

function parseRoleCard(value: unknown): RoleCard | "not_requested" | null {
  if (!isRecord(value)) return null;
  if (value.status === "not_requested") return "not_requested";
  if (value.status !== "adjudicated_question_role_set" || value.question_class !== "finance") return null;
  if (value.primary_relative !== "妻财" || value.hard_verdict != null) return null;
  const supporting = parseStringList(value.supporting_relatives);
  const obstacles = parseStringList(value.obstacle_attention_relatives);
  const unresolved = parseStringList(value.unresolved_checks);
  const source = parseSourceBadge(value.source_ref, "HJC-R009");
  if (!supporting || !obstacles || !unresolved || !source) return null;
  return {
    primary: "妻财",
    supporting,
    obstacles,
    source,
    unresolved,
  };
}

function parseSpecificLine(value: unknown): SpecificLineView | null {
  if (!isRecord(value) || value.hard_verdict != null) return null;
  const status = value.status;
  if (typeof status !== "string" || !(status in LINE_STATUS_LABEL)) return null;
  const derivationKey = value.derivation_basis;
  const derivation =
    typeof derivationKey === "string" && derivationKey in DERIVATION_LABEL
      ? DERIVATION_LABEL[derivationKey as keyof typeof DERIVATION_LABEL]
      : null;
  const candidates = parseLineList(value.visible_candidate_lines);
  if (!candidates || value.visible_candidate_count !== candidates.length) return null;
  const usefulLine = parsePosition(value.specific_line_selection);
  const source =
    parseSourceBadge(value.selection_source_ref, "HJC-R009") ??
    parseSourceBadge(value.selection_source_ref, "ZR-04-04");
  return {
    statusLabel: LINE_STATUS_LABEL[status as keyof typeof LINE_STATUS_LABEL],
    derivation,
    source: value.selection_source_ref == null ? null : source,
    candidates,
    hint: status === "unresolved_no_visible_line" ? "提示看伏神" : null,
    usefulLine: status === "unresolved_multiple_visible_lines" || status === "unresolved_no_visible_line"
      ? null
      : usefulLine,
  };
}

function parseStrengthSignals(value: unknown): readonly string[] | null {
  if (!Array.isArray(value)) return null;
  const chips: string[] = [];
  for (const item of value) {
    if (!isRecord(item) || item.status !== "candidate_signal") return null;
    const key = item.signal;
    if (typeof key !== "string" || !(key in SIGNAL_LABEL)) return null;
    if (item.value === false) continue;
    if (item.value !== true && typeof item.value !== "string") return null;
    chips.push(SIGNAL_LABEL[key as keyof typeof SIGNAL_LABEL]);
  }
  return chips;
}

function parseStrengthCandidate(value: unknown): StrengthRow | null {
  if (!isRecord(value) || value.status !== "candidate_only" || value.hard_verdict != null) return null;
  const source = parseTargetSource(value.source);
  const line = parsePosition(value.line);
  const seasonal = isRecord(value.seasonal_adjudication) ? value.seasonal_adjudication : null;
  if (!source || !line || !seasonal || seasonal.line !== line) return null;
  const state = parseSeasonalState(seasonal.seasonal_state);
  const band =
    typeof seasonal.strength_band === "string" && STRENGTH_BANDS.includes(seasonal.strength_band as (typeof STRENGTH_BANDS)[number])
      ? seasonal.strength_band
      : null;
  const signals = parseStrengthSignals(value.signals);
  if (!state || !band || !signals || seasonal.status !== "adjudicated_seasonal_strength_band") return null;
  const najiaRecord = isRecord(value.najia) ? value.najia : null;
  const najia = najiaRecord ? parseNajiaEntry(najiaRecord) : null;
  const najiaElement = najiaRecord ? parseElement(najiaRecord.element) : null;
  const lineElement = parseElement(seasonal.line_element);
  const monthElement = parseElement(seasonal.month_element);
  const title = lineElement && monthElement ? `爻${lineElement} · 月${monthElement}` : "";
  const place = PLACE_LABEL[source];
  return {
    key: `${source}-${line}`,
    line,
    place,
    najia: najia && najiaElement ? `${najia.ganzhi}${najiaElement}` : najia?.ganzhi ?? null,
    seasonal: state,
    band,
    title,
    signals,
    source: parseSourceBadge(seasonal.source_ref, "ZR-05-05"),
  };
}

function parseStrengthGroups(value: unknown): readonly StrengthGroup[] | null {
  if (!isRecord(value) || value.status !== "candidate_only") return null;
  if (!isRecord(value.by_relative) || value.fact_status !== "calculated_relation_not_verdict") return null;
  if (value.hard_verdict != null || value.requires_school_adjudication !== true) return null;
  if (!textField(value.source_dependency_id)) return null;
  const groups: StrengthGroup[] = [];
  for (const relative of ROLE_ORDER) {
    const entry = value.by_relative[relative];
    if (!isRecord(entry)) continue;
    if (entry.status === "not_available") continue;
    if (entry.status !== "candidate_only" || entry.hard_verdict != null || !Array.isArray(entry.candidates)) {
      return null;
    }
    const rows: StrengthRow[] = [];
    for (const candidate of entry.candidates) {
      const row = parseStrengthCandidate(candidate);
      if (!row) return null;
      rows.push(row);
    }
    if (rows.length) groups.push({ relative, rows });
  }
  return groups.length ? groups : null;
}

function parseUsefulSpirit(value: unknown): UsefulSpiritView | null {
  if (!isRecord(value) || value.status !== "evidence_bound") return null;
  const reason = textField(value.reason);
  const role = parseRoleCard(value.role_adjudication);
  const line =
    isRecord(value.role_adjudication) && role !== "not_requested"
      ? parseSpecificLine(value.role_adjudication.specific_line_adjudication)
      : null;
  const groups = parseStrengthGroups(value.strength_evidence);
  if (!role && !line && !groups) return null;
  return {
    reason,
    role,
    line,
    usefulLine: line?.usefulLine ?? null,
    groups,
  };
}

function EvidenceBadge({
  pack,
  ruleId,
  sourceAnchor,
}: Readonly<{
  pack: string;
  ruleId: string;
  sourceAnchor: string;
}>) {
  const [open, setOpen] = useState(false);
  return (
    <Drawer
      open={open}
      onOpenChange={setOpen}
      title={`${ruleId} 出处`}
      description={pack}
      trigger={
        <button className={styles.evidenceBadge} type="button">
          {ruleId}
        </button>
      }
    >
      <p>{sourceAnchor}</p>
    </Drawer>
  );
}

function UsefulSpiritEvidence({
  view,
  focus,
  onFocus,
}: Readonly<{
  view: UsefulSpiritView;
  focus: LinePosition | null;
  onFocus: (line: LinePosition) => void;
}>) {
  return (
    <section className={styles.relations} id="liuyao-s3-useful" aria-label="用神证据">
      <h2 className={styles.title}>用神证据</h2>
      {view.role === "not_requested" ? (
        <p className={styles.guide}>
          选择问题类别后可查看用神角色与古籍出处
          <a className={styles.guideLink} href="/liuyao">
            返回修改
          </a>
        </p>
      ) : null}
      {view.role && view.role !== "not_requested" ? (
        <div className={styles.roleCard}>
          <p className={styles.roleClass}>求财类问题</p>
          {view.reason ? <p className={styles.relationFact}>{view.reason}</p> : null}
          <p className={styles.roleLine}>
            <span className={styles.roleLabel}>用神</span>
            <span className={styles.roleTag} data-tone="primary">
              {view.role.primary}
            </span>
          </p>
          {view.role.supporting.map((item) => (
            <p className={styles.roleLine} key={item}>
              <span className={styles.roleLabel}>原神</span>
              <span className={styles.roleTag} data-tone="support">
                {item}
              </span>
            </p>
          ))}
          <p className={styles.attention}>传统上需留意的角色</p>
          <p className={styles.chipRow}>
            {view.role.obstacles.map((item) => (
              <span className={styles.roleTag} data-tone="attention" key={item}>
                {item}
              </span>
            ))}
          </p>
          <EvidenceBadge
            pack={view.role.source.pack}
            ruleId={view.role.source.ruleId}
            sourceAnchor={view.role.source.sourceAnchor}
          />
          <details className={styles.profileFold}>
            <summary>{`尚未裁定的检查 ${view.role.unresolved.length} 项`}</summary>
            <ul className={styles.relationList}>
              {view.role.unresolved.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </details>
        </div>
      ) : null}
      {view.line ? (
        <div className={styles.lineCard}>
          <p className={styles.relationFact}>{view.line.statusLabel}</p>
          {view.line.statusLabel === "多个候选并存" ? (
            <p className={styles.chipRow}>
              {view.line.candidates.map((line) => (
                <button
                  className={styles.relationFact}
                  key={line}
                  type="button"
                  onClick={() => onFocus(line)}
                >
                  {LIUYAO_LINE_NAMES[line - 1]}
                </button>
              ))}
            </p>
          ) : null}
          {view.line.hint ? <p className={styles.relationFact}>{view.line.hint}</p> : null}
          {view.line.derivation ? <p className={styles.relationFact}>{view.line.derivation}</p> : null}
          {view.line.source ? (
            <EvidenceBadge
              pack={view.line.source.pack}
              ruleId={view.line.source.ruleId}
              sourceAnchor={view.line.source.sourceAnchor}
            />
          ) : null}
        </div>
      ) : null}
      {view.groups ? (
        <div className={styles.strengthCard}>
          {view.groups.map((group) => (
            <div key={group.relative}>
              <h3 className={styles.groupTitle}>{group.relative}</h3>
              <table className={styles.strengthTable}>
                <tbody>
                  {group.rows.map((row) => (
                    <tr data-active={focus === row.line ? "true" : "false"} key={row.key} title={row.title || undefined}>
                      <th scope="row">
                        <button className={styles.relationFact} type="button" onClick={() => onFocus(row.line)}>
                          {`${LIUYAO_LINE_NAMES[row.line - 1]}（${row.place}）`}
                        </button>
                      </th>
                      <td>{row.najia ? <span className={styles.hidden}>{row.najia}</span> : null}</td>
                      <td>
                        <span className={styles.spirit}>{row.seasonal}</span>
                        <span className={styles.spirit}>{row.band}</span>
                        {row.source ? (
                          <EvidenceBadge
                            pack={row.source.pack}
                            ruleId={row.source.ruleId}
                            sourceAnchor={row.source.sourceAnchor}
                          />
                        ) : null}
                      </td>
                      <td>
                        {row.signals.map((signal) => (
                          <span className={styles.spirit} key={signal}>
                            {signal}
                          </span>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
          <p className={styles.note}>{STRENGTH_BOUNDARY}</p>
        </div>
      ) : null}
    </section>
  );
}

function parseMonthDayStrength(value: unknown, najia: unknown): readonly MonthDayRow[] | null {
  if (!Array.isArray(value) || value.length !== 6) return null;
  const labels = parseLineBranchElement(najia);
  const rows: MonthDayRow[] = [];
  for (let index = 0; index < 6; index += 1) {
    const item = value[index];
    if (!isRecord(item) || item.fact_status !== "calculated_relation_not_verdict") return null;
    if (!textField(item.source_dependency_id)) return null;
    const seasonal = parseSeasonalState(item.seasonal_state);
    const dayRelation = isRecord(item.day) ? textField(item.day.element_relation) : null;
    if (!seasonal || !dayRelation || !parseMonthDaySide(item.month, "month") || !parseMonthDaySide(item.day, "day")) {
      return null;
    }
    const line = (index + 1) as LinePosition;
    const stem = labels?.[index];
    const head = stem
      ? `${LIUYAO_LINE_NAMES[index]}${stem.branch}${stem.element}`
      : LIUYAO_LINE_NAMES[index];
    rows.push({
      line,
      sentence: `${head}：月${seasonal} · ${dayRelation}`,
    });
  }
  return rows;
}

function InquiryBar({ view }: Readonly<{ view: LiuyaoChartViewModel }>) {
  const question = view.question.trim();
  const casting = parseCastingMethod(view.core_facts?.casting_method);
  const calendar = parseCalendar(view.core_facts?.calendar ?? null);
  const xunkong = parseXunkong(view.core_facts?.xunkong ?? null);
  if (!question && !casting && !calendar && !xunkong) return null;
  const folded = question.length > QUESTION_FOLD;
  return (
    <section className={styles.inquiry} aria-label="求测信息">
      {question ? (
        folded ? (
          <details>
            <summary>展开</summary>
            <p>{question}</p>
          </details>
        ) : (
          <p>{question}</p>
        )
      ) : null}
      {casting ? <p>{casting}</p> : null}
      {calendar ? <p>{`月建${calendar.month_branch} · 日辰${calendar.day_ganzhi}`}</p> : null}
      {xunkong ? <p>{`旬空：${xunkong[0]}${xunkong[1]}`}</p> : null}
    </section>
  );
}

function parseHiddenLines(value: unknown): ReadonlyMap<LinePosition, HiddenCell> | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const cells = new Map<LinePosition, HiddenCell>();
  for (const item of value) {
    if (!isRecord(item) || item.status !== "source_derived_hidden_line_candidate") return null;
    const line = parsePosition(item.line);
    const relative =
      typeof item.six_relative === "string" && RELATIVES.includes(item.six_relative as (typeof RELATIVES)[number])
        ? (item.six_relative as (typeof RELATIVES)[number])
        : null;
    if (!line || !relative || cells.has(line) || !isRecord(item.najia)) return null;
    const stem = textField(item.najia.stem);
    const branch = textField(item.najia.branch);
    const ganzhi = textField(item.najia.ganzhi);
    const element = parseElement(item.najia.element);
    if (!stem || !branch || !ganzhi || !element) return null;
    cells.set(line, { relative, branch, element });
  }
  return cells.size ? cells : null;
}

function Head({
  slot,
  name,
  upper,
  lower,
}: Readonly<{
  slot: "primary" | "changed";
  name: string;
  upper: string;
  lower: string;
}>) {
  return (
    <div className={styles.head} data-slot={slot}>
      <p className={styles.slotLabel}>{slot === "primary" ? "本卦" : "变卦"}</p>
      <HexagramHeader name={name} upper={upper} lower={lower} />
      <p className={styles.compose}>
        上{upper}下{lower}
      </p>
    </div>
  );
}

function RelationFacts({
  label,
  facts,
  focus,
  focusKey,
  keyPrefix,
  onFocus,
}: Readonly<{
  label: string;
  facts: readonly RelationFact[];
  focus: LinePosition | null;
  focusKey: string | null;
  keyPrefix: "relation" | "returning";
  onFocus: (line: LinePosition) => void;
}>) {
  return (
    <section className={styles.relations} aria-label={label}>
      <h2 className={styles.title}>{label}</h2>
      <ul className={styles.relationList}>
        {facts.map((fact, index) => {
          const line = fact.line;
          const relationKey = `${keyPrefix}:${index}`;
          return (
            <li
              className={styles.relationRow}
              data-active={
                focusKey === relationKey || (focus !== null && focus === line) ? "true" : "false"
              }
              id={`liuyao-relation-${relationKey}`}
              key={`${fact.originalGanzhi}-${fact.changedGanzhi}-${fact.relations.join("、")}`}
            >
              {line ? (
                <button className={styles.relationFact} type="button" onClick={() => onFocus(line)}>
                  {fact.sentence}
                </button>
              ) : (
                <p className={styles.relationFact}>{fact.sentence}</p>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function ShiYingMovingRelations({
  facts,
  focus,
  onFocus,
}: Readonly<{
  facts: readonly ShiYingMovingRow[];
  focus: LinePosition | null;
  onFocus: (line: LinePosition) => void;
}>) {
  return (
    <section className={styles.relations} aria-label="世应动爻关系">
      <h2 className={styles.title}>世应动爻关系</h2>
      <ul className={styles.relationList}>
        {facts.map((fact) => (
          <li
            className={styles.relationRow}
            data-active={focus === fact.line ? "true" : "false"}
            key={fact.sentence}
          >
            <button className={styles.relationFact} type="button" onClick={() => onFocus(fact.line)}>
              {fact.sentence}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SixSpiritProfile({ sentence }: Readonly<{ sentence: string }>) {
  return (
    <section className={styles.relations} aria-label="六神档案">
      <details className={styles.profileFold}>
        <summary>六神档案</summary>
        <p className={styles.relationFact}>{sentence}</p>
      </details>
    </section>
  );
}

function SourcePatterns({
  patterns,
  open,
  focusId,
  onOpenChange,
  onFocus,
}: Readonly<{
  patterns: readonly SourcePatternView[];
  open: boolean;
  focusId: string | null;
  onOpenChange: (open: boolean) => void;
  onFocus: (line: LinePosition) => void;
}>) {
  return (
    <section className={styles.relations} id="liuyao-s3-patterns" aria-label="古法命中">
      <details
        className={styles.evidenceDrawer}
        open={open}
        onToggle={(event) => onOpenChange(event.currentTarget.open)}
      >
        <summary className={styles.evidenceSummary}>{`命中古法 ${patterns.length} 条 · 可核验`}</summary>
        <ul className={styles.evidenceList}>
          {patterns.map((pattern) => (
            <li
              className={styles.evidenceItem}
              data-active={focusId === pattern.localRuleId ? "true" : "false"}
              id={`liuyao-pattern-${pattern.localRuleId}`}
              key={pattern.ruleId}
            >
              {pattern.lines.length ? (
                <button
                  className={styles.relationFact}
                  type="button"
                  onClick={() => onFocus(pattern.lines[0]!)}
                >
                  {pattern.title}
                </button>
              ) : (
                <p className={styles.relationFact}>{pattern.title}</p>
              )}
              {pattern.packLabel ? <p className={styles.packName}>{pattern.packLabel}</p> : null}
              <p className={styles.note}>条件命中，非断语</p>
              <p className={styles.anchor}>{pattern.sourceAnchor}</p>
              <ul className={styles.auditList}>
                {pattern.audits.map((audit) => (
                  <li key={audit}>{audit}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}

function MonthDayStrength({
  facts,
  focus,
  onFocus,
}: Readonly<{
  facts: readonly MonthDayRow[];
  focus: LinePosition | null;
  onFocus: (line: LinePosition) => void;
}>) {
  return (
    <section className={styles.relations} aria-label="月日对爻强弱">
      <h2 className={styles.title}>月日对爻强弱</h2>
      <ul className={styles.relationList}>
        {facts.map((fact) => (
          <li
            className={styles.relationRow}
            data-active={focus === fact.line ? "true" : "false"}
            key={fact.sentence}
          >
            <button className={styles.relationFact} type="button" onClick={() => onFocus(fact.line)}>
              {fact.sentence}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function shiYingClause(shiYing: { readonly shi: LinePosition; readonly ying: LinePosition } | null): string | null {
  if (!shiYing) return null;
  return `${LIUYAO_LINE_NAMES[shiYing.shi - 1]}世、${LIUYAO_LINE_NAMES[shiYing.ying - 1]}应`;
}

function usefulSpiritClause(role: UsefulSpiritView["role"]): string | null {
  return role && role !== "not_requested" ? `用神${role.primary}` : null;
}

function freeSummaryText(
  view: LiuyaoChartViewModel,
  shiYing: { readonly shi: LinePosition; readonly ying: LinePosition } | null,
  role: UsefulSpiritView["role"],
): string | null {
  const parts: string[] = [];
  const primary = textField(view.primary_hexagram.name);
  if (primary) parts.push(`本卦${primary}`);
  const changed = view.changed_hexagram ? textField(view.changed_hexagram.name) : null;
  if (changed) parts.push(`变卦${changed}`);
  const movingCount = view.lines.filter((line) => line.moving).length;
  if (movingCount > 0) parts.push(`动爻 ${movingCount} 爻`);
  const shiYingText = shiYingClause(shiYing);
  if (shiYingText) parts.push(shiYingText);
  const useful = usefulSpiritClause(role);
  if (useful) parts.push(useful);
  return parts.length ? `${parts.join("；")}。` : null;
}

function FreeSummary({
  view,
  shiYing,
  role,
}: Readonly<{
  view: LiuyaoChartViewModel;
  shiYing: { readonly shi: LinePosition; readonly ying: LinePosition } | null;
  role: UsefulSpiritView["role"];
}>) {
  const text = freeSummaryText(view, shiYing, role);
  if (!text) return null;
  return (
    <section className={styles.relations} aria-label="基础摘要">
      <h2 className={styles.title}>基础摘要</h2>
      <p className={styles.freeSummary}>{text}</p>
    </section>
  );
}

function jumpToS3(anchor: LiuyaoS5Anchor) {
  const targetId = liuyaoS5TargetId(anchor);
  const node = document.getElementById(targetId) ?? document.getElementById("liuyao-s3-board");
  if (typeof node?.scrollIntoView === "function") {
    node.scrollIntoView({ block: "nearest" });
  }
  if (anchor.line) {
    document.getElementById(`liuyao-line-${anchor.line}`)?.focus();
  }
}

function ReportSection({
  claims,
  view,
  onJump,
}: Readonly<{
  claims: ReadonlyArray<LiuyaoS5Claim>;
  view: LiuyaoChartViewModel;
  onJump: (anchor: LiuyaoS5Anchor) => void;
}>) {
  const cards = claims
    .filter((claim) => claim.text.trim())
    .map((claim) => ({
      claim,
      anchors: resolveLiuyaoS5Anchors(liuyaoS5ClaimRefs(claim), view),
    }));
  if (!cards.length) return null;
  return (
    <section className={styles.relations} id="liuyao-s5-report" aria-labelledby="liuyao-s5-report-title">
      <h2 className={styles.title} id="liuyao-s5-report-title">
        报告
      </h2>
      <ul className={styles.claimList}>
        {cards.map(({ claim, anchors }) => (
          <li className={styles.claimCard} key={claim.claim_id}>
            <p>{claim.text}</p>
            {anchors.length ? (
              <div className={styles.anchorRow}>
                {anchors.map((anchor) => (
                  <button
                    className={styles.anchorJump}
                    key={`${claim.claim_id}-${anchor.kind}-${anchor.line ?? ""}-${anchor.relationKey ?? ""}-${anchor.patternId ?? ""}`}
                    type="button"
                    onClick={() => onJump(anchor)}
                  >
                    {anchor.label}
                  </button>
                ))}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function DeepReadEntry({
  offer,
  s4Phase,
  quotes,
}: Readonly<{
  offer?: LiuyaoS4Offer | null;
  s4Phase?: LiuyaoS4Phase;
  quotes: readonly string[];
}>) {
  if (s4Phase === "confirming") {
    return (
      <section className={styles.relations} id="liuyao-s4-deep" aria-labelledby="liuyao-s4-deep-title">
        <h2 className={styles.title} id="liuyao-s4-deep-title">
          深读
        </h2>
        <Status state="processing" title="确认中" description="正在等待服务端支付事实，不回显任何编号。" />
      </section>
    );
  }

  if (s4Phase === "locked") {
    return (
      <section className={styles.relations} id="liuyao-s4-deep" aria-labelledby="liuyao-s4-deep-title">
        <h2 className={styles.title} id="liuyao-s4-deep-title">
          深读
        </h2>
        <Status state="locked" />
      </section>
    );
  }

  if (s4Phase === "gateway_unavailable") {
    return (
      <section className={styles.relations} id="liuyao-s4-deep" aria-labelledby="liuyao-s4-deep-title">
        <h2 className={styles.title} id="liuyao-s4-deep-title">
          深读
        </h2>
        <Status
          state="unavailable"
          title="支付暂时不可用"
          description="当前 Fake/不可用适配器不会被当成成功付款，也不会发起结账。"
        />
      </section>
    );
  }

  return (
    <section className={styles.relations} id="liuyao-s4-deep" aria-labelledby="liuyao-s4-deep-title">
      <h2 className={styles.title} id="liuyao-s4-deep-title">
        深读
      </h2>
      <p className={styles.skuCopy}>{SKU_COPY}</p>
      {quotes.length ? (
        <div>
          <p className={styles.kicker}>样例引用（已上屏事实）</p>
          <ul className={styles.quoteList}>
            {quotes.map((quote) => (
              <li key={quote}>
                <blockquote className={styles.quote}>{quote}</blockquote>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {offer ? (
        <div className={styles.offerCard}>
          <p className={styles.offerName}>{offer.name}</p>
          <p>{offer.coverage}</p>
          <p>{offer.priceText}</p>
          <p className={styles.note}>{offer.refundBoundary}</p>
          <p className={styles.note}>绑定当前这张已起之卦。未登录不会发起结账。</p>
          <Link className={styles.loginLink} href="/auth/login">
            登录后继续
          </Link>
        </div>
      ) : (
        <Status
          state="unavailable"
          title="测试期未开放"
          description="当前没有可购买的六爻深读，不会显示价格，也不会发起结账。"
        />
      )}
    </section>
  );
}

export function LiuyaoLineTower({
  view,
  offer = null,
  s4Phase = "entry",
  reportClaims = [],
}: Readonly<{
  view: LiuyaoChartViewModel;
  offer?: LiuyaoS4Offer | null;
  s4Phase?: LiuyaoS4Phase;
  reportClaims?: ReadonlyArray<LiuyaoS5Claim>;
}>) {
  const changed = view.changed_hexagram;
  const [showChanged, setShowChanged] = useState(false);
  const [focusLine, setFocusLine] = useState<LinePosition | null>(null);
  const [focusRelation, setFocusRelation] = useState<string | null>(null);
  const [focusPattern, setFocusPattern] = useState<string | null>(null);
  const [patternOpen, setPatternOpen] = useState(false);
  const changedGlyphs = changed
    ? hexagramLinesFromTrigrams(changed.upper_trigram, changed.lower_trigram, [])
    : null;
  const visualRows = [...view.lines].sort((left, right) => right.position - left.position);
  const spirits = parseSpiritColumn(view.core_facts?.six_spirits);
  const hidden = parseHiddenLines(view.core_facts?.hidden_lines);
  const najia = parseNajiaColumn(view.core_facts?.najia);
  const relatives = parseRelativeColumn(view.core_facts?.six_relatives);
  const shiYing = parseShiYing(view.core_facts?.shi_ying);
  const changedPlate = parseChangedPlate(view.core_facts?.changed_plate_lines);
  const changedNajia = parseNajiaColumn(view.core_facts?.changed_najia);
  const changedRelatives = parseRelativeColumn(view.core_facts?.changed_six_relatives);
  const relationFacts = parseRelationFacts(view.core_facts?.relation_facts, najia);
  const returningRelations = parseRelationFacts(view.core_facts?.returning_relations, najia);
  const shiYingMoving = parseShiYingMovingRelations(view.core_facts?.shi_ying_moving_relations);
  const monthDayStrength = parseMonthDayStrength(view.core_facts?.month_day_strength, view.core_facts?.najia);
  const sixSpiritProfile = parseSixSpiritProfile(view.core_facts?.six_spirit_profile);
  const usefulSpirit = parseUsefulSpirit(view.core_facts?.useful_spirit_selection);
  const sourcePatterns = parseSourcePatterns(view.core_facts?.source_conditioned_patterns);
  const xunkong = parseXunkong(view.core_facts?.xunkong ?? null);
  const voidBranches = xunkong ? new Set(xunkong) : null;
  const hasRelations = Boolean(
    relationFacts || returningRelations || shiYingMoving || monthDayStrength,
  );
  const deliverableClaims = reportClaims.filter((claim) => claim.text.trim());
  const nav = [
    { id: "liuyao-s3-board", label: "卦盘" },
    usefulSpirit ? { id: "liuyao-s3-useful", label: "用神证据" } : null,
    hasRelations ? { id: "liuyao-s3-relations", label: "关系事实" } : null,
    sourcePatterns ? { id: "liuyao-s3-patterns", label: "古法命中" } : null,
    { id: "liuyao-s4-deep", label: "深读" },
    deliverableClaims.length ? { id: "liuyao-s5-report", label: "报告" } : null,
  ].filter((item): item is { id: string; label: string } => item !== null);
  const quotes = [
    usefulSpiritClause(usefulSpirit?.role ?? null),
    shiYingClause(shiYing),
  ].filter((item): item is string => item !== null);

  function jumpFromReport(anchor: LiuyaoS5Anchor) {
    setFocusLine(anchor.line);
    setFocusRelation(anchor.relationKey);
    setFocusPattern(anchor.patternId);
    if (anchor.kind === "pattern") setPatternOpen(true);
    jumpToS3(anchor);
  }

  return (
    <div className={styles.wrap}>
      <nav className={styles.sectionNav} aria-label="盘面章节">
        <ul>
          {nav.map((item) => (
            <li key={item.id}>
              <a href={`#${item.id}`}>{item.label}</a>
            </li>
          ))}
        </ul>
      </nav>
      <InquiryBar view={view} />
      <section className={styles.tower} id="liuyao-s3-board" aria-labelledby="liuyao-tower-title">
      <div className={styles.toolbar}>
        <h2 className={styles.title} id="liuyao-tower-title">
          卦盘
        </h2>
        {changed ? (
          <button
            className={styles.toggle}
            type="button"
            onClick={() => setShowChanged((open) => !open)}
          >
            {showChanged ? "收起变卦" : "查看变卦"}
          </button>
        ) : null}
      </div>
      <div className={styles.heads}>
        <Head
          slot="primary"
          name={view.primary_hexagram.name}
          upper={view.primary_hexagram.upper_trigram}
          lower={view.primary_hexagram.lower_trigram}
        />
        {changed ? (
          <Head
            slot="changed"
            name={changed.name}
            upper={changed.upper_trigram}
            lower={changed.lower_trigram}
          />
        ) : null}
      </div>
      <div className={styles.tableWrap}>
        <table
          className={styles.table}
          aria-label="六爻爻塔"
          data-show-changed={showChanged ? "true" : "false"}
        >
          <thead>
            <tr>
              <th scope="col">爻位</th>
              {spirits ? <th scope="col">六神</th> : null}
              {hidden ? <th scope="col">伏神</th> : null}
              <th scope="col">本卦</th>
              {najia ? <th scope="col">纳甲</th> : null}
              {relatives ? <th scope="col">六亲</th> : null}
              {shiYing ? <th scope="col">世应</th> : null}
              {changed ? (
                <th className={styles.changedCol} scope="col">
                  变卦
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {visualRows.map((line) => {
              const primary = glyphFromValue(line.value);
              const changedGlyph = changedGlyphs?.[line.position - 1];
              const role =
                shiYing?.shi === line.position
                  ? "shi"
                  : shiYing?.ying === line.position
                    ? "ying"
                    : undefined;
              const spiritCell = spirits?.[line.position - 1];
              const hiddenCell = hidden?.get(line.position);
              const najiaCell = najia?.[line.position - 1];
              const relativeCell = relatives?.[line.position - 1];
              const changedYang = changedPlate
                ? changedPlate[line.position - 1]
                : changedGlyph?.yang;
              const changedNajiaCell = changedNajia?.[line.position - 1];
              const changedRelativeCell = changedRelatives?.[line.position - 1];
              return (
                <tr
                  key={line.position}
                  id={`liuyao-line-${line.position}`}
                  tabIndex={-1}
                  data-role={role}
                  data-focus={focusLine === line.position ? "true" : undefined}
                  data-useful={usefulSpirit?.usefulLine === line.position ? "true" : undefined}
                >
                  <th scope="row">
                    <span className={styles.lineHead}>
                      {LIUYAO_LINE_NAMES[line.position - 1]}
                      {usefulSpirit?.usefulLine === line.position ? (
                        <span className={styles.usefulMark}>用神</span>
                      ) : null}
                    </span>
                  </th>
                  {spirits ? (
                    <td>{spiritCell ? <span className={styles.spirit}>{spiritCell}</span> : null}</td>
                  ) : null}
                  {hidden ? (
                    <td>
                      {hiddenCell ? (
                        <span className={styles.hidden}>
                          {`伏：${hiddenCell.relative}${hiddenCell.branch}${hiddenCell.element}`}
                        </span>
                      ) : null}
                    </td>
                  ) : null}
                  <td>
                    <LineGlyph yang={primary.yang} moving={primary.moving} size="l" />
                  </td>
                  {najia ? (
                    <td>
                      {najiaCell ? (
                        <span className={styles.najiaWrap}>
                          <span
                            className={styles.najia}
                            data-element={ELEMENT_TOKEN[najiaCell.element]}
                          >
                            {najiaCell.ganzhi}
                          </span>
                          {voidBranches?.has(najiaCell.branch) ? (
                            <span className={styles.voidMark}>空</span>
                          ) : null}
                        </span>
                      ) : null}
                    </td>
                  ) : null}
                  {relatives ? (
                    <td>{relativeCell ? <span className={styles.relative}>{relativeCell}</span> : null}</td>
                  ) : null}
                  {shiYing ? (
                    <td>
                      {role === "shi" ? (
                        <span className={styles.seal} data-mark="shi">
                          世
                        </span>
                      ) : null}
                      {role === "ying" ? (
                        <span className={styles.seal} data-mark="ying">
                          应
                        </span>
                      ) : null}
                    </td>
                  ) : null}
                  {changed ? (
                    <td className={styles.changedCol}>
                      <div
                        className={styles.changedFact}
                        data-tone={line.moving ? "focus" : "muted"}
                      >
                        {changedYang === undefined ? null : (
                          <LineGlyph yang={changedYang} moving={false} size="l" />
                        )}
                        {changedNajiaCell ? (
                          <span className={styles.najiaWrap}>
                            <span
                              className={styles.najia}
                              data-element={ELEMENT_TOKEN[changedNajiaCell.element]}
                            >
                              {changedNajiaCell.ganzhi}
                            </span>
                            {voidBranches?.has(changedNajiaCell.branch) ? (
                              <span className={styles.voidMark}>空</span>
                            ) : null}
                          </span>
                        ) : null}
                        {changedRelativeCell ? (
                          <span className={styles.relative}>{changedRelativeCell}</span>
                        ) : null}
                      </div>
                    </td>
                  ) : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      </section>
      {usefulSpirit ? (
        <UsefulSpiritEvidence view={usefulSpirit} focus={focusLine} onFocus={setFocusLine} />
      ) : null}
      {hasRelations ? (
        <div id="liuyao-s3-relations">
          {relationFacts ? (
            <RelationFacts
              label="关系事实"
              facts={relationFacts}
              focus={focusLine}
              focusKey={focusRelation}
              keyPrefix="relation"
              onFocus={setFocusLine}
            />
          ) : null}
          {returningRelations ? (
            <RelationFacts
              label="回头生克"
              facts={returningRelations}
              focus={focusLine}
              focusKey={focusRelation}
              keyPrefix="returning"
              onFocus={setFocusLine}
            />
          ) : null}
          {shiYingMoving ? (
            <ShiYingMovingRelations facts={shiYingMoving} focus={focusLine} onFocus={setFocusLine} />
          ) : null}
          {monthDayStrength ? (
            <MonthDayStrength facts={monthDayStrength} focus={focusLine} onFocus={setFocusLine} />
          ) : null}
        </div>
      ) : null}
      {sixSpiritProfile ? <SixSpiritProfile sentence={sixSpiritProfile} /> : null}
      {sourcePatterns ? (
        <SourcePatterns
          patterns={sourcePatterns}
          open={patternOpen}
          focusId={focusPattern}
          onOpenChange={setPatternOpen}
          onFocus={setFocusLine}
        />
      ) : null}
      <FreeSummary view={view} shiYing={shiYing} role={usefulSpirit?.role ?? null} />
      <DeepReadEntry offer={offer} s4Phase={s4Phase} quotes={quotes} />
      {deliverableClaims.length ? (
        <ReportSection claims={deliverableClaims} view={view} onJump={jumpFromReport} />
      ) : null}
    </div>
  );
}
