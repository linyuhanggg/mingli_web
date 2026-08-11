import type { BaziChartView } from "./reading-display";

/**
 * Frontend-only display model for chart workspaces.
 *
 * This module is a pure view-model: it maps public facts already returned by
 * the backend Runtime into focusable workspace structures. It never runs chart
 * math, never detects patterns, and never invents layers or stars. Anything the
 * server did not provide renders as "unavailable" or "empty" with honest copy.
 */

export type WorkspaceLayerId = "natal" | "decadal" | "yearly";
export type WorkspaceLayerStatus = "ready" | "unavailable" | "empty";
export type WorkspaceCellKind = "pillar" | "palace" | "meta";
export type WorkspaceHighlightTone = "neutral" | "emphasis" | "caution";

export interface WorkspaceLayer {
  id: WorkspaceLayerId;
  label: string;
  status: WorkspaceLayerStatus;
  summary?: string | null;
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
  highlights?: BaziWorkspaceHighlightFacts[] | null;
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

function buildLayers(facts: BaziWorkspaceFacts): WorkspaceLayer[] {
  const natalStatus: WorkspaceLayerStatus = hasAnyPillarValue(facts.pillars)
    ? "ready"
    : "empty";
  const decadalStatus: WorkspaceLayerStatus = hasText(facts.activeLuck)
    ? "ready"
    : "unavailable";

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
      status: decadalStatus,
      summary: hasText(facts.activeLuck)
        ? `当前大运 ${facts.activeLuck}`
        : "此时间层未生成",
    },
    {
      id: "yearly",
      label: "流年",
      status: "unavailable",
      summary: "此时间层未生成",
    },
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
): WorkspaceFocusDetail | null {
  const cell = view.cells.find((candidate) => candidate.id === cellId);
  if (!cell) return null;

  const relatedKeys = new Set(cell.relatedFactKeys ?? []);
  const relatedFacts = (view.basis ?? [])
    .filter((row) => relatedKeys.has(row.key))
    .map((row) => ({ label: row.label, text: row.text }));

  return {
    id: cell.id,
    title: cell.value ? `${cell.label} · ${cell.value}` : cell.label,
    facts: relatedFacts,
    limits: [
      "此处仅重述服务端已公开的四柱与口径事实，前端不进行本地排盘或星曜推算。",
      "暂无与该柱直接关联的公开依据；请以下方依据卡标注的“支持事实”为准。",
    ],
    sources: [],
    proseExcerpt: null,
  };
}

/**
 * Adapt the existing reading-display BaziChartView into workspace facts.
 * Pure display-model composition; the BaziChartView public API is untouched.
 */
export function baziWorkspaceFactsFromChart(
  chart: BaziChartView,
): BaziWorkspaceFacts {
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
    highlights: chart.highlights.map((highlight) => ({
      label: highlight.label,
      text: highlight.text,
    })),
  };
}
