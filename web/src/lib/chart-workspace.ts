import type { BaziChartView } from "./reading-display";

/**
 * Frontend-only display model for chart workspaces.
 *
 * This module is a pure view-model: it maps public facts already returned by
 * the backend Runtime into focusable workspace structures. It never runs chart
 * math, never detects patterns, and never invents layers or stars. Anything the
 * server did not provide renders as "unavailable" or "empty" with honest copy.
 */

export type WorkspaceLayerId =
  | "natal"
  | "decadal"
  | "yearly"
  | "monthly"
  | "daily"
  | "hourly";
export type WorkspaceLayerStatus =
  | "ready"
  | "locked-paywall"
  | "locked-unavailable"
  | "fail-closed-unknown"
  | "empty";
export type WorkspaceCellKind = "pillar" | "palace" | "meta";
export type WorkspaceHighlightTone = "neutral" | "emphasis" | "caution";

export type TimeLayerEntitlementResolution =
  | "granted"
  | "denied"
  | "unknown"
  | "unauthenticated"
  | "request_failed";
export type TimeLayerEntitlementAccess =
  | "readable"
  | "locked_paywall"
  | "fail_closed_unknown"
  | "unavailable";
export type TimeLayerEntitlementLayerId =
  | "life"
  | "luck_cycles"
  | "major_limits"
  | "year"
  | "month"
  | "day"
  | "hour";

export interface TimeLayerEntitlementLayer {
  layerId: TimeLayerEntitlementLayerId;
  tier: "free" | "paid";
  access: TimeLayerEntitlementAccess;
  upgradeCta: "professional_info" | null;
}

export interface TimeLayerEntitlement {
  schemaVersion: "time-layer-entitlement/v1";
  capabilityId: "bazi";
  resolution: TimeLayerEntitlementResolution;
  freeBoundaryLayerId: "year";
  paidLayerIds: readonly ["month", "day", "hour"];
  freeYearSet: number[];
  layers: TimeLayerEntitlementLayer[];
}

export interface WorkspaceLayer {
  id: WorkspaceLayerId;
  label: string;
  status: WorkspaceLayerStatus;
  summary?: string | null;
  upgradeCta?: "professional_info" | null;
}

export interface WorkspaceCell {
  id: string;
  label: string;
  value: string | null;
  kind: WorkspaceCellKind;
  badges?: string[];
  relatedFactKeys?: string[];
}

export interface WorkspaceFocusDetail {
  id: string;
  title: string;
  facts: Array<{ label: string; text: string }>;
  limits: string[];
  sources: string[];
  proseExcerpt?: string | null;
}

export interface WorkspaceHighlight {
  id: string;
  title: string;
  body: string;
  tone?: WorkspaceHighlightTone;
}

export interface ChartWorkspaceView {
  title: string;
  subtitle?: string | null;
  layers: WorkspaceLayer[];
  activeLayerId: WorkspaceLayerId;
  cells: WorkspaceCell[];
  highlights: WorkspaceHighlight[];
  basis?: Array<{ key: string; label: string; text: string }>;
}

export interface BaziWorkspacePillarFacts {
  year: string | null;
  month: string | null;
  day: string | null;
  hour: string | null;
}

export interface BaziWorkspaceHighlightFacts {
  label: string;
  text: string;
  tone?: WorkspaceHighlightTone;
}

/** Minimal public-fact projection consumed by the bazi workspace view. */
export interface BaziWorkspaceFacts {
  pillars?: BaziWorkspacePillarFacts | null;
  dayMaster?: string | null;
  monthCommand?: string | null;
  activeLuck?: string | null;
  birthTime?: string | null;
  gender?: string | null;
  location?: string | null;
  timeBasis?: string | null;
  ziHour?: string | null;
  timezone?: string | null;
  targetDay?: string | null;
  targetPeriod?: string | null;
  calendarSummary?: string | null;
  decadalReady?: boolean;
  decadalSummary?: string | null;
  yearlyReady?: boolean;
  yearlySummary?: string | null;
  monthlyReady?: boolean;
  monthlySummary?: string | null;
  dailyReady?: boolean;
  dailySummary?: string | null;
  hourlyReady?: boolean;
  hourlySummary?: string | null;
  entitlement?: TimeLayerEntitlement | null;
  highlights?: BaziWorkspaceHighlightFacts[] | null;
}

const ENTITLEMENT_RESOLUTIONS = new Set<TimeLayerEntitlementResolution>([
  "granted",
  "denied",
  "unknown",
  "unauthenticated",
  "request_failed",
]);
const ENTITLEMENT_ACCESS = new Set<TimeLayerEntitlementAccess>([
  "readable",
  "locked_paywall",
  "fail_closed_unknown",
  "unavailable",
]);
const ENTITLEMENT_OBJECT_KEYS = [
  "schema_version",
  "capability_id",
  "resolution",
  "free_boundary_layer_id",
  "paid_layer_ids",
  "free_year_set",
  "capability",
  "layers",
] as const;
const ENTITLEMENT_CAPABILITY_KEYS = ["time_layers"] as const;
const ENTITLEMENT_CAPABILITY_LAYER_KEYS = [
  "layer_id",
  "label",
  "available",
  "unavailable_reason",
] as const;
const ENTITLEMENT_LAYER_KEYS = [
  "layer_id",
  "tier",
  "access",
  "upgrade_cta",
] as const;
const BAZI_CAPABILITY_LAYER_IDS = new Set([
  "life",
  "year",
  "month",
  "day",
  "hour",
]);
const BAZI_ENTITLEMENT_LAYER_TABLE = [
  { layerId: "life", tier: "free" },
  { layerId: "luck_cycles", tier: "free" },
  { layerId: "year", tier: "free" },
  { layerId: "month", tier: "paid" },
  { layerId: "day", tier: "paid" },
  { layerId: "hour", tier: "paid" },
] as const satisfies ReadonlyArray<{
  layerId: TimeLayerEntitlementLayerId;
  tier: "free" | "paid";
}>;
const PAID_ACCESS_BY_RESOLUTION: Record<
  TimeLayerEntitlementResolution,
  ReadonlySet<TimeLayerEntitlementAccess>
> = {
  granted: new Set(["readable", "unavailable"]),
  denied: new Set(["locked_paywall", "unavailable"]),
  unknown: new Set(["fail_closed_unknown", "unavailable"]),
  unauthenticated: new Set(["fail_closed_unknown", "unavailable"]),
  request_failed: new Set(["fail_closed_unknown", "unavailable"]),
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(
  value: Record<string, unknown>,
  expected: readonly string[],
): boolean {
  const keys = Object.keys(value);
  return (
    keys.length === expected.length &&
    expected.every((key) => Object.prototype.hasOwnProperty.call(value, key))
  );
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function hasValidBaziCapabilitySnapshot(value: unknown): boolean {
  if (!isRecord(value) || !hasExactKeys(value, ENTITLEMENT_CAPABILITY_KEYS)) {
    return false;
  }
  if (!Array.isArray(value.time_layers)) return false;

  const seen = new Set<string>();
  for (const item of value.time_layers) {
    if (
      !isRecord(item) ||
      !hasExactKeys(item, ENTITLEMENT_CAPABILITY_LAYER_KEYS) ||
      !isNonEmptyString(item.layer_id) ||
      !BAZI_CAPABILITY_LAYER_IDS.has(item.layer_id) ||
      seen.has(item.layer_id) ||
      !isNonEmptyString(item.label) ||
      typeof item.available !== "boolean" ||
      (item.unavailable_reason !== null &&
        !isNonEmptyString(item.unavailable_reason)) ||
      item.available === (item.unavailable_reason !== null)
    ) {
      return false;
    }
    seen.add(item.layer_id);
  }

  return true;
}

/**
 * Parse only the frozen backend sibling contract. Unknown, partial, parallel,
 * or contradictory payloads deliberately collapse to null so paid layers stay
 * fail-closed; free chart facts never depend on this parser.
 */
export function parseTimeLayerEntitlement(value: unknown): TimeLayerEntitlement | null {
  if (!isRecord(value) || !hasExactKeys(value, ENTITLEMENT_OBJECT_KEYS)) {
    return null;
  }
  if (
    value.schema_version !== "time-layer-entitlement/v1" ||
    value.capability_id !== "bazi" ||
    !ENTITLEMENT_RESOLUTIONS.has(value.resolution as TimeLayerEntitlementResolution) ||
    value.free_boundary_layer_id !== "year" ||
    !Array.isArray(value.paid_layer_ids) ||
    value.paid_layer_ids.length !== 3 ||
    value.paid_layer_ids[0] !== "month" ||
    value.paid_layer_ids[1] !== "day" ||
    value.paid_layer_ids[2] !== "hour" ||
    !Array.isArray(value.free_year_set) ||
    !hasValidBaziCapabilitySnapshot(value.capability) ||
    !Array.isArray(value.layers) ||
    value.layers.length !== BAZI_ENTITLEMENT_LAYER_TABLE.length
  ) {
    return null;
  }

  const resolution = value.resolution as TimeLayerEntitlementResolution;
  const freeYearSet: number[] = [];
  const seenYears = new Set<number>();
  for (const year of value.free_year_set) {
    if (
      typeof year !== "number" ||
      !Number.isInteger(year) ||
      year < 1800 ||
      year > 2199 ||
      seenYears.has(year)
    ) {
      return null;
    }
    seenYears.add(year);
    freeYearSet.push(year);
  }

  const layers: TimeLayerEntitlementLayer[] = [];
  for (const [index, item] of value.layers.entries()) {
    if (!isRecord(item) || !hasExactKeys(item, ENTITLEMENT_LAYER_KEYS)) {
      return null;
    }
    const expected = BAZI_ENTITLEMENT_LAYER_TABLE[index];
    const layerId = item.layer_id as TimeLayerEntitlementLayerId;
    const tier = item.tier;
    const access = item.access as TimeLayerEntitlementAccess;
    const upgradeCta = item.upgrade_cta;
    if (
      layerId !== expected.layerId ||
      tier !== expected.tier ||
      !ENTITLEMENT_ACCESS.has(access) ||
      upgradeCta !== (
        tier === "paid" &&
        (access === "locked_paywall" || access === "fail_closed_unknown")
          ? "professional_info"
          : null
      )
    ) {
      return null;
    }
    if (tier === "free" && access !== "readable" && access !== "unavailable") {
      return null;
    }
    if (tier === "paid" && !PAID_ACCESS_BY_RESOLUTION[resolution].has(access)) {
      return null;
    }
    layers.push({
      layerId: expected.layerId,
      tier: expected.tier,
      access,
      upgradeCta: upgradeCta as "professional_info" | null,
    });
  }

  return {
    schemaVersion: "time-layer-entitlement/v1",
    capabilityId: "bazi",
    resolution,
    freeBoundaryLayerId: "year",
    paidLayerIds: ["month", "day", "hour"],
    freeYearSet,
    layers,
  };
}

/**
 * The backend owns the free yearly window. When no entitlement sibling is
 * available, returned free facts remain readable; once present, free_year_set
 * is the authoritative allow-list and extra returned years stay hidden.
 */
export function filterBaziYearLayersByEntitlement<T extends { year: number }>(
  layers: readonly T[] | null | undefined,
  entitlement?: TimeLayerEntitlement | null,
): T[] {
  const returnedLayers = layers ?? [];
  if (!entitlement) return [...returnedLayers];

  const readableYears = new Set(entitlement.freeYearSet);
  return returnedLayers.filter((layer) => readableYears.has(layer.year));
}

const PILLAR_ORDER = [
  { key: "year" as const, label: "年柱" },
  { key: "month" as const, label: "月柱" },
  { key: "day" as const, label: "日柱" },
  { key: "hour" as const, label: "时柱" },
];

const PILLAR_RELATED_FACT_KEYS: Record<
  keyof BaziWorkspacePillarFacts,
  Array<keyof BaziWorkspaceFacts>
> = {
  year: ["birthTime", "timezone", "timeBasis", "location", "gender"],
  month: ["monthCommand", "calendarSummary"],
  day: ["dayMaster", "calendarSummary"],
  hour: ["birthTime", "timezone", "timeBasis", "ziHour", "location"],
};

const BASIS_ROWS: Array<{ label: string; key: keyof BaziWorkspaceFacts }> = [
  { label: "出生时间", key: "birthTime" },
  { label: "时区", key: "timezone" },
  { label: "时间口径", key: "timeBasis" },
  { label: "子时策略", key: "ziHour" },
  { label: "地点", key: "location" },
  { label: "性别", key: "gender" },
  { label: "日主", key: "dayMaster" },
  { label: "月令", key: "monthCommand" },
  { label: "目标日期", key: "targetDay" },
  { label: "目标周期", key: "targetPeriod" },
  { label: "历法口径", key: "calendarSummary" },
];

function hasText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function pillarValue(
  pillars: BaziWorkspacePillarFacts | null | undefined,
  key: keyof BaziWorkspacePillarFacts,
): string | null {
  const raw = pillars?.[key];
  return hasText(raw) ? raw.trim() : null;
}

function hasAnyPillarValue(
  pillars: BaziWorkspacePillarFacts | null | undefined,
): boolean {
  return Boolean(
    pillars &&
      PILLAR_ORDER.some(({ key }) => hasText(pillars[key] as string | null)),
  );
}

function hasAnyFact(facts: BaziWorkspaceFacts): boolean {
  return Object.entries(facts).some(([, value]) => {
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === "object" && value !== null) {
      return hasAnyPillarValue(value as BaziWorkspacePillarFacts);
    }
    return hasText(value as string);
  });
}

function unavailableLayer(
  id: WorkspaceLayerId,
  label: string,
  summary = "待接入",
): WorkspaceLayer {
  return { id, label, status: "locked-unavailable", summary, upgradeCta: null };
}

function paidLayer(
  id: Extract<WorkspaceLayerId, "monthly" | "daily" | "hourly">,
  label: string,
  factsReady: boolean,
  readySummary: string | null | undefined,
  entitlement: TimeLayerEntitlement | null | undefined,
): WorkspaceLayer {
  if (!factsReady) return unavailableLayer(id, label);
  const entitlementId = id === "monthly" ? "month" : id === "daily" ? "day" : "hour";
  const entry = entitlement?.layers.find((item) => item.layerId === entitlementId);
  if (!entry) {
    return {
      id,
      label,
      status: "fail-closed-unknown",
      summary: "权益状态未确认",
      upgradeCta: "professional_info",
    };
  }
  if (entry.access === "readable" && entitlement?.resolution === "granted") {
    return { id, label, status: "ready", summary: readySummary ?? null, upgradeCta: null };
  }
  if (entry.access === "unavailable") return unavailableLayer(id, label);
  if (entry.access === "locked_paywall") {
    return {
      id,
      label,
      status: "locked-paywall",
      summary: "专业版时间层",
      upgradeCta: entry.upgradeCta,
    };
  }
  return {
    id,
    label,
    status: "fail-closed-unknown",
    summary: "权益状态未确认",
    upgradeCta: entry.upgradeCta,
  };
}

function buildLayers(facts: BaziWorkspaceFacts): WorkspaceLayer[] {
  const natalStatus: WorkspaceLayerStatus = hasAnyPillarValue(facts.pillars)
    ? "ready"
    : "empty";
  const decadalReady = Boolean(facts.decadalReady || hasText(facts.activeLuck));
  const yearlyReady = Boolean(facts.yearlyReady);

  return [
    {
      id: "natal",
      label: "本命",
      status: natalStatus,
      summary:
        natalStatus === "empty"
          ? "服务端尚未返回可展示的四柱结构"
          : null,
    },
    {
      id: "decadal",
      label: "大运",
      status: decadalReady ? "ready" : "locked-unavailable",
      summary:
        facts.decadalSummary ??
        (hasText(facts.activeLuck) ? `当前大运 ${facts.activeLuck}` : "待接入"),
      upgradeCta: null,
    },
    {
      id: "yearly",
      label: "流年",
      status: yearlyReady ? "ready" : "locked-unavailable",
      summary: yearlyReady ? facts.yearlySummary ?? null : "待接入",
      upgradeCta: null,
    },
    paidLayer("monthly", "流月", Boolean(facts.monthlyReady), facts.monthlySummary, facts.entitlement),
    paidLayer("daily", "流日", Boolean(facts.dailyReady), facts.dailySummary, facts.entitlement),
    paidLayer("hourly", "流时", Boolean(facts.hourlyReady), facts.hourlySummary, facts.entitlement),
  ];
}

function buildCells(facts: BaziWorkspaceFacts): WorkspaceCell[] {
  if (!hasAnyPillarValue(facts.pillars)) return [];
  return PILLAR_ORDER.map(({ key, label }) => {
    const value = pillarValue(facts.pillars, key);
    return {
      id: key,
      label,
      value,
      kind: "pillar" as const,
      badges: value ? undefined : key === "hour" ? ["时辰未知"] : ["未提供"],
      relatedFactKeys: PILLAR_RELATED_FACT_KEYS[key],
    };
  });
}

function buildBasis(
  facts: BaziWorkspaceFacts,
): Array<{ key: string; label: string; text: string }> {
  return BASIS_ROWS.filter(({ key }) => hasText(facts[key] as string))
    .map(({ label, key }) => ({
      key,
      label,
      text: (facts[key] as string).trim(),
    }));
}

function buildHighlights(
  facts: BaziWorkspaceFacts,
): WorkspaceHighlight[] {
  return (facts.highlights ?? []).map((highlight, index) => ({
    id: `highlight-${index}`,
    title: highlight.label,
    body: highlight.text,
    tone: highlight.tone ?? "neutral",
  }));
}

/**
 * Build the bazi workspace view strictly from server-provided public facts.
 * Missing layers stay present but marked unavailable; nothing is fabricated.
 */
export function buildBaziWorkspaceView(facts: BaziWorkspaceFacts): ChartWorkspaceView {
  return {
    title: "八字命盘",
    subtitle: hasAnyFact(facts) ? null : "服务端尚未返回可展示的公开事实",
    layers: buildLayers(facts),
    activeLayerId: "natal",
    cells: buildCells(facts),
    highlights: buildHighlights(facts),
    basis: buildBasis(facts),
  };
}

/**
 * Resolve focus detail for a workspace cell from public facts only.
 * Returns null for unknown cell ids; never invents stars or palaces.
 */
export function resolveBaziFocusDetail(
  view: ChartWorkspaceView,
  cellId: string,
  extras?: {
    facts?: Array<{ label: string; text: string }>;
    sources?: string[];
  },
): WorkspaceFocusDetail | null {
  const cell = view.cells.find((candidate) => candidate.id === cellId);
  if (!cell) return null;

  const relatedKeys = new Set(cell.relatedFactKeys ?? []);
  const relatedFacts = (view.basis ?? [])
    .filter((row) => relatedKeys.has(row.key))
    .map((row) => ({ label: row.label, text: row.text }));

  const extraFacts = extras?.facts ?? [];
  const extraSources = extras?.sources ?? [];
  const facts = [...relatedFacts];
  for (const fact of extraFacts) {
    if (!facts.some((row) => row.label === fact.label && row.text === fact.text)) {
      facts.push(fact);
    }
  }

  const limits = [
    "此处仅重述服务端已公开的四柱与口径事实，前端不进行本地排盘或星曜推算。",
  ];
  if (extraFacts.length === 0 && extraSources.length === 0) {
    limits.push(
      "暂无与该柱直接关联的公开依据；请以下方依据卡标注的“支持事实”为准。",
    );
  }

  return {
    id: cell.id,
    title: cell.value ? `${cell.label} · ${cell.value}` : cell.label,
    facts,
    limits,
    sources: extraSources,
    proseExcerpt: null,
  };
}

/**
 * Adapt the existing reading-display BaziChartView into workspace facts.
 * Pure display-model composition; the BaziChartView public API is untouched.
 */
export function baziWorkspaceFactsFromChart(
  chart: BaziChartView,
  entitlement?: TimeLayerEntitlement | null,
): BaziWorkspaceFacts {
  const luckStatusLabels: Readonly<Record<string, string>> = {
    calculated: "已计算",
    sequence_only: "仅返回大运序列",
    not_calculated_missing_gender: "缺少性别，暂未计算",
  };
  const readableYearLayers = filterBaziYearLayersByEntitlement(
    chart.coreFacts?.year_layers,
    entitlement,
  );
  const yearlyReady = entitlement
    ? readableYearLayers.length > 0
    : readableYearLayers.length > 0 ||
      Boolean(
        chart.timeLayers?.some(
          (layer) => layer.layer_id === "year" && layer.available,
        ),
      );

  return {
    pillars: chart.pillars
      ? {
          year: chart.pillars.year || null,
          month: chart.pillars.month || null,
          day: chart.pillars.day || null,
          hour: chart.pillars.hour || null,
        }
      : null,
    dayMaster: chart.dayMaster,
    monthCommand: chart.monthCommand,
    activeLuck: chart.activeLuck,
    birthTime: chart.birthTime,
    gender: chart.gender,
    location: chart.location,
    timeBasis: chart.timeBasis,
    ziHour: chart.ziHour,
    timezone: chart.timezone,
    targetDay: chart.targetDay,
    targetPeriod: chart.targetPeriod,
    calendarSummary: chart.calendarSummary,
    decadalReady: Boolean(chart.coreFacts?.luck_cycles),
    decadalSummary: chart.coreFacts?.luck_cycles
      ? `状态：${luckStatusLabels[chart.coreFacts.luck_cycles.status] ?? "已记录"}`
      : null,
    yearlyReady,
    yearlySummary: readableYearLayers.length
      ? readableYearLayers
          .map((item) => `${item.year} ${item.ganzhi}（${item.ganzhi_segments.length} 个节气分段）`)
          .join("；")
      : null,
    monthlyReady: Boolean(
      chart.coreFacts?.month_layers?.length ||
        chart.timeLayers?.some(
          (layer) => layer.layer_id === "month" && layer.available,
        ),
    ),
    monthlySummary: chart.coreFacts?.month_layers?.length
      ? chart.coreFacts.month_layers
          .map((item) => `${item.period}（${item.ganzhi_segments.length} 个节气分段）`)
          .join("；")
      : null,
    dailyReady: Boolean(
      chart.coreFacts?.day_layers?.length ||
        chart.timeLayers?.some(
          (layer) => layer.layer_id === "day" && layer.available,
        ),
    ),
    dailySummary: chart.coreFacts?.day_layers?.length
      ? chart.coreFacts.day_layers
          .map((item) => `${item.period}（${item.ganzhi_segments.length} 个日界分段）`)
          .join("；")
      : null,
    hourlyReady: false,
    hourlySummary: null,
    entitlement,
    highlights: chart.highlights.map((highlight) => ({
      label: highlight.label,
      text: highlight.text,
    })),
  };
}
