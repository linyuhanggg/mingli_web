import type { ReadingHorizon } from "./api";

const dateFormatter = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "UTC",
  year: "numeric",
  month: "long",
  day: "numeric",
});

const capabilityLabels: Record<string, string> = {
  bazi: "八字",
  fortune: "日运与周运",
  liuyao: "六爻",
};

const objectLabels: Record<string, string> = {
  natal: "命理档案",
  near_time_personal: "近期个人趋势",
  concrete_event: "具体事项",
};

const dimensionLabels: Record<string, string> = {
  overview: "概览",
  career: "事业",
  outcome: "结果",
  timing: "时机",
};

export function formatServerDate(value: string | null): string {
  if (!value) return "未指定";
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? value : dateFormatter.format(date);
}

export function formatHorizon(horizon: ReadingHorizon): string {
  const start = formatServerDate(horizon.start);
  const end = formatServerDate(horizon.end);
  if (horizon.start && horizon.start === horizon.end) return start;
  if (!horizon.start && !horizon.end) return "长期范围";
  return `${start} 至 ${end}`;
}

export function formatCapabilityIds(ids: string[]): string {
  return ids.map((id) => capabilityLabels[id] ?? id).join("、") || "未指定";
}

export function formatObjectId(id: string): string {
  return objectLabels[id] ?? id;
}

export function formatDimensionIds(ids: string[]): string {
  return ids.map((id) => dimensionLabels[id] ?? id).join("、") || "综合范围";
}
