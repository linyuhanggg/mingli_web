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

const ENTITLEMENT_LAYER_IDS = new Set<TimeLayerEntitlementLayerId>([
  "life",
  "luck_cycles",
  "major_limits",
  "year",
  "month",
  "day",
  "hour",
]);
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Parse only the frozen backend sibling contract. Unknown, partial, parallel,
 * or contradictory payloads deliberately collapse to null so paid layers stay
 * fail-closed; free chart facts never depend on this parser.
 */
export function parseTimeLayerEntitlement(value: unknown): TimeLayerEntitlement | null {
  if (!isRecord(value)) return null;
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
    !value.free_year_set.every((year) => Number.isInteger(year)) ||
    !Array.isArray(value.layers)
  ) {
    return null;
  }

  const resolution = value.resolution as TimeLayerEntitlementResolution;
  const layers: TimeLayerEntitlementLayer[] = [];
  const seen = new Set<TimeLayerEntitlementLayerId>();
  for (const item of value.layers) {
    if (!isRecord(item)) return null;
    const layerId = item.layer_id as TimeLayerEntitlementLayerId;
    const tier = item.tier;
    const access = item.access as TimeLayerEntitlementAccess;
    const upgradeCta = item.upgrade_cta;
    if (
      !ENTITLEMENT_LAYER_IDS.has(layerId) ||
      seen.has(layerId) ||
      (tier !== "free" && tier !== "paid") ||
      !ENTITLEMENT_ACCESS.has(access) ||
      (upgradeCta !== null && upgradeCta !== "professional_info")
    ) {
      return null;
    }
    if (tier === "free" && (upgradeCta !== null || !["readable", "unavailable"].includes(access))) {
      return null;
    }
    if (tier === "paid") {
      const allowed = resolution === "granted"
        ? new Set<TimeLayerEntitlementAccess>(["readable", "unavailable"])
        : resolution === "denied"
          ? new Set<TimeLayerEntitlementAccess>(["locked_paywall", "unavailable"])
          : new Set<TimeLayerEntitlementAccess>(["fail_closed_unknown", "unavailable"]);
      if (!allowed.has(access)) return null;
      if (access === "unavailable" && upgradeCta !== null) return null;
    }
    seen.add(layerId);
    layers.push({
      layerId,
      tier,
      access,
      upgradeCta: upgradeCta as "professional_info" | null,
    });
  }

  if (!["life", "luck_cycles", "year", "month", "day", "hour"].every(
    (layerId) => seen.has(layerId as TimeLayerEntitlementLayerId),
  )) {
    return null;
  }

  return {
    schemaVersion: "time-layer-entitlement/v1",
    capabilityId: "bazi",
    resolution,
    freeBoundaryLayerId: "year",
    paidLayerIds: ["month", "day", "hour"],
    freeYearSet: [...value.free_year_set] as number[],
    layers,
  };
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
    yearlyReady: Boolean(
      chart.coreFacts?.year_layers?.length ||
        chart.timeLayers?.some(
          (layer) => layer.layer_id === "year" && layer.available,
        ),
    ),
    yearlySummary: chart.coreFacts?.year_layers?.length
      ? chart.coreFacts.year_layers
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
