import type {
  BaziChartViewModel,
  BaziCoreFacts,
  BaziInterpretiveCandidates,
} from "@/view-models/registry";

import type { ReadingFact, ReadingHorizon } from "./api";

const dateFormatter = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "UTC",
  year: "numeric",
  month: "long",
  day: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "long",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const capabilityLabels: Record<string, string> = {
  bazi: "八字",
  fortune: "日运与周运",
  liuyao: "六爻",
  meihua: "梅花易数",
  qimen: "奇门遁甲",
  liuren: "大六壬",
  "luming-nayin": "禄命/纳音",
  physiognomy: "相法",
  selection: "择日",
  taiyi: "太乙神数",
  xingming: "七政四余",
  ziwei: "紫微斗数",
  "time-check": "寻时定盘",
};

const objectLabels: Record<string, string> = {
  natal: "命理档案",
  near_time_personal: "近期个人趋势",
  concrete_event: "具体事项",
  macro_historical: "年度宏观事项",
  calendar_choice: "日期选择",
  spatial_observation: "空间观察",
  visible_observation: "可见观察",
};

const dimensionLabels: Record<string, string> = {
  overview: "概览",
  career: "事业",
  outcome: "结果",
  timing: "时机",
  health: "健康",
  location: "地点",
  relationship: "关系",
  state: "状态",
  current_state: "当前状态",
  direction: "方位",
  source_comparison: "来源对照",
  time_options: "时辰候选",
};

const genderLabels: Record<string, string> = {
  male: "男",
  female: "女",
  other: "其他",
  m: "男",
  f: "女",
};

const timeBasisLabels: Record<string, string> = {
  civil: "民用时",
  solar: "真太阳时",
  lunar: "农历时间口径",
};

const ziHourLabels: Record<string, string> = {
  midnight: "按午夜换日",
  substitute: "子时替代口径",
  solar: "按太阳时判断子时",
};

const fieldLabels: Record<string, string> = {
  birth_datetime: "出生时间",
  birth_time: "出生时间",
  gender: "性别",
  location: "地点",
  reference_time: "参考时间",
  "参考时间": "参考时间",
  time_basis: "时间口径",
  time_basis_policy: "时间口径",
  "时间口径": "时间口径",
  timezone: "时区",
  "时区": "时区",
  zi_hour_policy: "子时策略",
  "子时策略": "子时策略",
  active_luck_cycle: "当前大运",
  calculated_dates: "已计算日期",
  "已计算日期": "已计算日期",
  calendar_normalization: "历法口径",
  day_master: "日主",
  month_command: "月令",
  four_pillars: "四柱",
  natal_pillars: "四柱",
  target_day: "目标日期",
  target_period: "目标周期",
  "目标周期": "目标周期",
  period_markers: "周期标记",
  "周期确定性标记": "周期标记",
};

const SENSITIVE_KEY =
  /^(state_token|candidate|prompt|secret|token|raw_prompt|model_draft)$/i;

const ISO_DATE_TIME =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

const STRUCTURED_VALUE_KEYS = new Set([
  "four_pillars",
  "natal_pillars",
  "day_master",
  "month_command",
  "calendar_normalization",
  "target_period",
  "period_markers",
]);

export type FactPillars = {
  year: string;
  month: string;
  day: string;
  hour: string;
};

export type FactPresentation = {
  key: string;
  label: string;
  text: string;
  emphasis: "primary" | "secondary";
  pillars?: FactPillars;
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

export function formatDateTimeLike(value: string): string {
  const trimmed = value.trim();
  if (ISO_DATE.test(trimmed)) {
    return formatServerDate(trimmed);
  }
  if (ISO_DATE_TIME.test(trimmed)) {
    const date = new Date(trimmed);
    if (!Number.isNaN(date.getTime())) {
      return dateTimeFormatter.format(date);
    }
  }
  return trimmed;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function tryParseJson(raw: string): unknown {
  const text = raw.trim();
  if (
    !(
      (text.startsWith("{") && text.endsWith("}")) ||
      (text.startsWith("[") && text.endsWith("]"))
    )
  ) {
    return undefined;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

function labelForKey(key: string): string {
  return fieldLabels[key] ?? key.replaceAll("_", " ");
}

function structuredValueKey(fact: ReadingFact): string | null {
  const refKey = fact.ref.split("/").at(-1)?.trim() ?? "";
  if (STRUCTURED_VALUE_KEYS.has(refKey)) return refKey;

  const kindKey = fact.kind_id.replace(/^fact:/, "").split("/").at(-1) ?? "";
  return STRUCTURED_VALUE_KEYS.has(kindKey) ? kindKey : null;
}

function formatGender(value: string): string {
  return genderLabels[value.toLowerCase()] ?? value;
}

function formatTimeBasis(value: string): string {
  return timeBasisLabels[value.toLowerCase()] ?? value;
}

function formatZiHour(value: string): string {
  return ziHourLabels[value.toLowerCase()] ?? value;
}

function formatDayMaster(value: Record<string, unknown>): string {
  const stem = typeof value.stem === "string" ? value.stem : "";
  const element = typeof value.element === "string" ? value.element : "";
  const polarity = typeof value.polarity === "string" ? value.polarity : "";
  const polarityElement =
    polarity && element ? `${polarity}${element}` : element || polarity;
  const parts = [stem, polarityElement].filter(Boolean);
  return parts.join(" · ") || "日主已就绪";
}

function formatMonthCommand(value: Record<string, unknown>): string {
  const label = typeof value.label === "string" ? value.label : "";
  const mainQi = typeof value.main_qi === "string" ? value.main_qi : "";
  const element =
    typeof value.main_qi_element === "string" ? value.main_qi_element : "";
  if (label && mainQi && element) return `${label} · 主气${mainQi}（${element}）`;
  if (label) return label;
  return "月令已就绪";
}

function formatNatalPillars(value: Record<string, unknown>): FactPillars | null {
  const year = typeof value.year === "string" ? value.year : "";
  const month = typeof value.month === "string" ? value.month : "";
  const day = typeof value.day === "string" ? value.day : "";
  const hour = typeof value.hour === "string" ? value.hour : "";
  if (!year && !month && !day && !hour) return null;
  return { year, month, day, hour };
}

function formatCalendarNormalization(value: Record<string, unknown>): string {
  const algorithm =
    typeof value.algorithm_version === "string" ? value.algorithm_version : "";
  const convention = isPlainObject(value.calendar_convention)
    ? value.calendar_convention
    : null;
  const engine =
    convention && typeof convention.engine === "string" ? convention.engine : "";
  const engineVersion =
    convention && typeof convention.engine_version === "string"
      ? convention.engine_version
      : "";
  const hourBasis =
    convention && typeof convention.hour_basis === "string"
      ? formatTimeBasis(convention.hour_basis)
      : "";

  const bits = [
    algorithm || (engine && engineVersion ? `${engine} ${engineVersion}` : ""),
    hourBasis,
  ].filter(Boolean);
  return bits.length > 0 ? bits.join(" · ") : "服务端已规范化历法口径";
}

function formatTargetPeriod(value: Record<string, unknown>): string {
  const kind = typeof value.kind === "string" ? value.kind : "";
  const start = typeof value.start === "string" ? formatDateTimeLike(value.start) : "";
  const end = typeof value.end === "string" ? formatDateTimeLike(value.end) : "";
  if (start && end && start === end) {
    return kind === "day" ? `日：${start}` : start;
  }
  if (start && end) return `${start} 至 ${end}`;
  return start || end || "目标周期已就绪";
}

function formatPeriodMarkers(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) return "暂无额外周期标记";
  return value
    .map((marker, index) => {
      if (!isPlainObject(marker)) {
        return `第 ${index + 1} 项：${formatScalar(marker)}`;
      }
      const date =
        typeof marker.date === "string" && marker.date.trim()
          ? formatDateTimeLike(marker.date)
          : "";
      const dayRole =
        typeof marker.day_role === "string" ? marker.day_role.trim() : "";
      const dayPillar =
        typeof marker.day_pillar === "string" ? marker.day_pillar.trim() : "";
      const luck =
        typeof marker.active_luck_cycle === "string"
          ? marker.active_luck_cycle.trim()
          : "";
      const details = [
        dayPillar ? `日柱 ${dayPillar}` : "",
        dayRole ? `日主关系 ${dayRole}` : "",
        luck ? `大运 ${luck}` : "",
      ].filter(Boolean);
      const label = date || `第 ${index + 1} 日`;
      return details.length > 0
        ? `${label} · ${details.join(" · ")}`
        : `${label} · 公开标记已就绪`;
    })
    .join("；");
}

function formatScalar(value: unknown): string {
  if (value == null) return "未提供";
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return "未提供";
    if (ISO_DATE.test(trimmed) || ISO_DATE_TIME.test(trimmed)) {
      return formatDateTimeLike(trimmed);
    }
    return trimmed;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    if (value.every((item) => typeof item === "string" || typeof item === "number")) {
      return value
        .map((item) =>
          typeof item === "string" ? formatDateTimeLike(item) : String(item),
        )
        .join("、");
    }
    return `共 ${value.length} 项`;
  }
  if (isPlainObject(value)) {
    return "详见服务端摘要";
  }
  return "详见服务端摘要";
}

function formatKnownStructured(
  key: string,
  value: unknown,
): Omit<FactPresentation, "key"> | null {
  const label = labelForKey(key);
  if (value == null) {
    return { label, text: "未提供", emphasis: "secondary" };
  }

  if (typeof value === "string") {
    if (key === "gender" || key === "性别") {
      return { label, text: formatGender(value), emphasis: "primary" };
    }
    if (key === "time_basis" || key === "time_basis_policy" || key === "时间口径") {
      return { label, text: formatTimeBasis(value), emphasis: "primary" };
    }
    if (key === "zi_hour_policy" || key === "子时策略") {
      return { label, text: formatZiHour(value), emphasis: "primary" };
    }
    if (
      key === "birth_datetime" ||
      key === "birth_time" ||
      key === "出生时间" ||
      key === "reference_time" ||
      key === "参考时间" ||
      key === "target_day" ||
      key === "目标日期"
    ) {
      return {
        label,
        text: formatDateTimeLike(value),
        emphasis:
          key === "reference_time" || key === "参考时间" ? "secondary" : "primary",
      };
    }
    if (key === "active_luck_cycle" || key === "当前大运") {
      return { label: "当前大运", text: value, emphasis: "primary" };
    }
    return {
      label,
      text: formatScalar(value),
      emphasis: "primary",
    };
  }

  if (
    (key === "natal_pillars" || key === "four_pillars") &&
    isPlainObject(value)
  ) {
    const pillars = formatNatalPillars(value);
    if (!pillars) return null;
    return {
      label: "四柱",
      text: `年${pillars.year || "—"} 月${pillars.month || "—"} 日${pillars.day || "—"} 时${pillars.hour || "—"}`,
      emphasis: "primary",
      pillars,
    };
  }

  if (key === "day_master" && isPlainObject(value)) {
    return { label: "日主", text: formatDayMaster(value), emphasis: "primary" };
  }

  if (key === "month_command" && isPlainObject(value)) {
    return { label: "月令", text: formatMonthCommand(value), emphasis: "primary" };
  }

  if (key === "calendar_normalization" && isPlainObject(value)) {
    return {
      label: "历法口径",
      text: formatCalendarNormalization(value),
      emphasis: "secondary",
    };
  }

  if ((key === "目标周期" || key === "target_period") && isPlainObject(value)) {
    return {
      label: "目标周期",
      text: formatTargetPeriod(value),
      emphasis: "primary",
    };
  }

  if (
    (key === "周期确定性标记" || key === "period_markers") &&
    (Array.isArray(value) || isPlainObject(value))
  ) {
    return {
      label: "周期标记",
      text: formatPeriodMarkers(value),
      emphasis: "secondary",
    };
  }

  if (key === "已计算日期" || key === "calculated_dates") {
    return {
      label: "已计算日期",
      text: formatScalar(value),
      emphasis: "secondary",
    };
  }

  if (isPlainObject(value) || Array.isArray(value)) {
    return {
      label,
      text: formatScalar(value),
      emphasis: "secondary",
    };
  }

  return {
    label,
    text: formatScalar(value),
    emphasis: "primary",
  };
}

function splitDisplayText(
  displayText: string,
): { key: string; rawValue: string } | null {
  const match = displayText.match(/^([^:：]{1,40})\s*[:：]\s*([\s\S]+)$/);
  if (!match) return null;
  return { key: match[1].trim(), rawValue: match[2].trim() };
}

function looksLikeRawDump(text: string): boolean {
  return (
    /[{[]/.test(text) ||
    /_/.test(text) ||
    ISO_DATE_TIME.test(text) ||
    /^(male|female|other|civil|midnight|solar|lunar)$/i.test(text)
  );
}

/**
 * Turn a public ReadingFact into readable Chinese presentation.
 * Prefer display_text; never dump sensitive value payloads.
 */
export function formatReadingFact(fact: ReadingFact, index = 0): FactPresentation {
  const display = (fact.display_text ?? "").trim();
  const kindKey = fact.kind_id?.replace(/^fact:/, "") ?? "";
  const fallbackKey = `fact-${index}`;
  const valueKey = structuredValueKey(fact);

  if (valueKey && fact.value != null) {
    const structured = formatKnownStructured(valueKey, fact.value);
    if (structured) {
      return { key: `${valueKey}-${index}`, ...structured };
    }
  }

  const displayKey = display ? splitDisplayText(display)?.key : null;
  if (
    Array.isArray(fact.value) &&
    (kindKey === "period_markers" ||
      displayKey === "period_markers" ||
      displayKey === "周期确定性标记" ||
      displayKey === "周期标记")
  ) {
    return {
      key: `period_markers-${index}`,
      label: "周期标记",
      text: formatPeriodMarkers(fact.value),
      emphasis: "secondary",
    };
  }

  if (display) {
    const split = splitDisplayText(display);
    if (split) {
      if (SENSITIVE_KEY.test(split.key)) {
        return {
          key: fallbackKey,
          label: "公开事实",
          text: "此项仅供服务端使用，不在页面展示。",
          emphasis: "secondary",
        };
      }

      const parsed = tryParseJson(split.rawValue);
      const structured = formatKnownStructured(
        split.key,
        parsed === undefined ? split.rawValue : parsed,
      );
      if (structured) {
        return { key: `${split.key}-${index}`, ...structured };
      }

      return {
        key: `${split.key}-${index}`,
        label: labelForKey(split.key),
        text: formatScalar(split.rawValue),
        emphasis: looksLikeRawDump(split.rawValue) ? "secondary" : "primary",
      };
    }

    if (!looksLikeRawDump(display)) {
      return {
        key: fallbackKey,
        label: "关键事实",
        text: display,
        emphasis: "primary",
      };
    }

    const parsedWhole = tryParseJson(display);
    if (parsedWhole !== undefined) {
      const structured = formatKnownStructured(kindKey || "fact", parsedWhole);
      if (structured) {
        return { key: fallbackKey, ...structured };
      }
    }
  }

  // Only use non-sensitive, simple values as a last resort.
  if (
    fact.value != null &&
    (typeof fact.value === "string" ||
      typeof fact.value === "number" ||
      typeof fact.value === "boolean")
  ) {
    const structured = formatKnownStructured(kindKey || "fact", fact.value);
    if (structured) {
      return { key: fallbackKey, ...structured };
    }
  }

  if (display) {
    return {
      key: fallbackKey,
      label: labelForKey(kindKey || "公开事实"),
      text: display.length > 160 ? `${display.slice(0, 160)}…` : display,
      emphasis: "secondary",
    };
  }

  return {
    key: fallbackKey,
    label: "公开事实",
    text: "服务端已返回事实，但暂无可用的公开摘要。",
    emphasis: "secondary",
  };
}

export function formatReadingFacts(facts: ReadingFact[]): FactPresentation[] {
  return facts
    .map((fact, index) => formatReadingFact(fact, index))
    .filter((item) => item.text.trim().length > 0);
}

export type BaziChartView = {
  pillars: FactPillars | null;
  coreFacts?: BaziCoreFacts | null;
  timeLayers?: BaziChartViewModel["time_layers"];
  dayMaster: string | null;
  monthCommand: string | null;
  activeLuck: string | null;
  birthTime: string | null;
  gender: string | null;
  location: string | null;
  timeBasis: string | null;
  ziHour: string | null;
  timezone: string | null;
  targetDay: string | null;
  targetPeriod: string | null;
  calendarSummary: string | null;
  highlights: FactPresentation[];
  secondary: FactPresentation[];
};

const BAZI_ELEMENT_LABELS: Record<string, string> = {
  wood: "木",
  fire: "火",
  earth: "土",
  metal: "金",
  water: "水",
};

export function formatBaziInterpretiveCandidateRows(
  candidates: BaziInterpretiveCandidates,
): string[][] {
  const strength = candidates.strength;
  const inventory = strength.all_element_occurrences
    .map(
      (item) =>
        `${BAZI_ELEMENT_LABELS[item.element] ?? item.element}${item.value}`,
    )
    .join("、");
  const stemCandidates =
    candidates.following_and_transformation.stem_combination_candidates;
  const branchCandidates =
    candidates.following_and_transformation.branch_formation_candidates;
  return [
    [
      "强弱证据",
      `日主${BAZI_ELEMENT_LABELS[strength.day_element] ?? strength.day_element}；月令${BAZI_ELEMENT_LABELS[strength.month_command_element] ?? strength.month_command_element}；同类 ${strength.same_element_occurrences} 项；生扶 ${BAZI_ELEMENT_LABELS[strength.resource_element] ?? strength.resource_element} ${strength.resource_occurrences} 项；盘面 ${inventory}`,
    ],
    [
      "月令结构",
      `${candidates.structure.month_main_qi} · ${candidates.structure.month_main_qi_ten_god}；${candidates.structure.main_qi_visible ? "主气已透干" : "主气未透干"}；${candidates.structure.visible_positions.join("、") || "无可见位置"}`,
    ],
    [
      "合化 / 从格候选",
      `天干候选 ${stemCandidates.length} 项；地支成局候选 ${branchCandidates.length} 项；${candidates.following_and_transformation.status === "requires_classical_adjudication" ? "仍需经典裁决" : "状态未知"}`,
    ],
    [
      "显著信号",
      `${candidates.salience_signals.length} 项机械候选：${candidates.salience_signals.map((signal) => signal.signal_id).join("、") || "无"}`,
    ],
    ["证据边界", strength.boundary],
  ];
}

function presentationByLabel(
  items: FactPresentation[],
  labels: string[],
): FactPresentation | undefined {
  return items.find((item) => labels.includes(item.label));
}

export function buildBaziChartView(facts: ReadingFact[]): BaziChartView {
  const items = formatReadingFacts(facts);
  const pillarsItem = presentationByLabel(items, ["四柱"]);
  const dayMaster = presentationByLabel(items, ["日主"])?.text ?? null;
  const monthCommand = presentationByLabel(items, ["月令"])?.text ?? null;
  const activeLuck = presentationByLabel(items, ["当前大运"])?.text ?? null;
  const birthTime = presentationByLabel(items, ["出生时间"])?.text ?? null;
  const gender = presentationByLabel(items, ["性别"])?.text ?? null;
  const location = presentationByLabel(items, ["地点"])?.text ?? null;
  const timeBasis = presentationByLabel(items, ["时间口径"])?.text ?? null;
  const ziHour = presentationByLabel(items, ["子时策略"])?.text ?? null;
  const timezone = presentationByLabel(items, ["时区"])?.text ?? null;
  const targetDay = presentationByLabel(items, ["目标日期"])?.text ?? null;
  const targetPeriod = presentationByLabel(items, ["目标周期"])?.text ?? null;
  const calendarSummary = presentationByLabel(items, ["历法口径"])?.text ?? null;

  const used = new Set(
    [
      pillarsItem?.key,
      presentationByLabel(items, ["日主"])?.key,
      presentationByLabel(items, ["月令"])?.key,
      presentationByLabel(items, ["当前大运"])?.key,
      presentationByLabel(items, ["出生时间"])?.key,
      presentationByLabel(items, ["性别"])?.key,
      presentationByLabel(items, ["地点"])?.key,
      presentationByLabel(items, ["时间口径"])?.key,
      presentationByLabel(items, ["子时策略"])?.key,
      presentationByLabel(items, ["时区"])?.key,
      presentationByLabel(items, ["目标日期"])?.key,
      presentationByLabel(items, ["目标周期"])?.key,
      presentationByLabel(items, ["历法口径"])?.key,
    ].filter(Boolean),
  );

  const leftovers = items.filter((item) => !used.has(item.key));

  return {
    pillars: pillarsItem?.pillars ?? null,
    coreFacts: null,
    dayMaster,
    monthCommand,
    activeLuck,
    birthTime,
    gender,
    location,
    timeBasis,
    ziHour,
    timezone,
    targetDay,
    targetPeriod,
    calendarSummary,
    highlights: leftovers.filter((item) => item.emphasis === "primary"),
    secondary: leftovers.filter((item) => item.emphasis === "secondary"),
  };
}

export function buildBaziChartViewFromViewModel(
  viewModel: BaziChartViewModel,
): BaziChartView {
  const coreFacts = viewModel.core_facts ?? null;
  const pillars: FactPillars = {
    year: "",
    month: "",
    day: "",
    hour: "",
  };
  for (const pillar of viewModel.pillars) {
    pillars[pillar.position] = `${pillar.stem}${pillar.branch}`;
  }

  return {
    pillars,
    coreFacts,
    timeLayers: viewModel.time_layers,
    dayMaster: coreFacts?.day_master
      ? `${coreFacts.day_master.stem}（${coreFacts.day_master.element}·${coreFacts.day_master.polarity}）`
      : null,
    monthCommand: coreFacts?.month_command
      ? `${coreFacts.month_command.label} · 主气 ${coreFacts.month_command.main_qi}`
      : null,
    activeLuck: null,
    birthTime: null,
    gender: null,
    location: null,
    timeBasis: null,
    ziHour: null,
    timezone: null,
    targetDay: null,
    targetPeriod: coreFacts?.day_layers?.length
      ? coreFacts.day_layers.map((item) => item.period).join("、")
      : coreFacts?.month_layers?.length
        ? coreFacts.month_layers.map((item) => item.period).join("、")
        : coreFacts?.year_layers?.length
          ? coreFacts.year_layers.map((item) => String(item.year)).join("、")
          : null,
    calendarSummary: null,
    highlights: [],
    secondary: viewModel.element_balance.map((item) => ({
      key: `view-model:element-balance:${item.element}`,
      label: "五行计数",
      text: item.display_text,
      emphasis: "secondary" as const,
    })),
  };
}

export function splitAcceptedCopy(text: string | null | undefined): {
  headline: string | null;
  body: string | null;
} {
  if (!text || !text.trim()) {
    return { headline: null, body: null };
  }
  const normalized = text.replace(/\r\n/g, "\n").trim();
  const parts = normalized
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length === 0) return { headline: null, body: null };
  if (parts.length === 1) {
    const single = parts[0];
    if (single.length <= 28 && !single.includes("。")) {
      return { headline: single, body: null };
    }
    const firstSentence = single.split(/(?<=[。！？])/)[0]?.trim() ?? single;
    if (firstSentence && firstSentence.length <= 36 && firstSentence !== single) {
      return {
        headline: firstSentence.replace(/[。！？]$/, ""),
        body: single.slice(firstSentence.length).trim() || null,
      };
    }
    return { headline: null, body: single };
  }
  return {
    headline: parts[0].replace(/[。！？]$/, ""),
    body: parts.slice(1).join("\n\n"),
  };
}
