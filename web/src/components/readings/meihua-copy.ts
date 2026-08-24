export const MEIHUA_BODY_USE_STATUS: Record<string, string> = {
  calculated_relation_not_verdict: "已计算的五行关系，不是吉凶",
};

export const MEIHUA_SEASON: Record<string, string> = {
  spring: "春",
  summer: "夏",
  autumn: "秋",
  winter: "冬",
};

export const MEIHUA_INTERPRETATION_STATUS: Record<string, string> = {
  source_adjudicated_relations: "古籍已裁定关系极性",
  source_adjudicated_relation_polarity: "关系极性已裁定",
  relation_polarity_adjudicated: "关系极性已裁定",
};

export const MEIHUA_POLARITY: Record<string, string> = {
  supportive: "生扶体",
  depleting: "泄耗体",
  adverse: "克制体",
  favorable: "体所生克",
  harmonious: "比和",
  generating: "生扶体",
  draining: "泄耗体",
  controlling: "克制体",
  generated_or_controlled: "体所生克",
  matching: "比和",
};

export const MEIHUA_SEASONAL_CAPTION = "月令旺衰是按时令算出的事实，不是吉凶。";
export const MEIHUA_FACTS_ONLY_CAPTION =
  "下面是古籍已经裁定的关系，不是断这件事成不成。";
export const MEIHUA_POLARITY_FOOTER =
  "以上是古籍已裁定的关系极性。这件事成不成、吉凶、应期，本页不断。";
export const MEIHUA_JUDGMENT_EMPTY =
  "这一问还没有可发布的判断。上面的盘面和关系事实可以先看。";
export const MEIHUA_JUDGMENT_EMPTY_HINT = "不是加载失败。吉凶成败本来就不在这一页。";
export const MEIHUA_JUDGMENT_GENERATING = "正文还在生成。三卦盘面可以先看。";

const STRENGTH_STATES = new Set(["旺", "相", "休", "囚", "死", "平", "衰"]);
const SEASONS_ZH = new Set(["春", "夏", "秋", "冬"]);

export function looksInternal(value: string): boolean {
  const text = value.trim();
  if (!text) return false;
  if (/[_/]/.test(text)) return true;
  if (/body\/use|source-adjudicated/i.test(text)) return true;
  if (/^[a-z]+(?:_[a-z0-9]+)+$/i.test(text)) return true;
  if (/^[A-Za-z][A-Za-z ,.;:'"-]{12,}$/.test(text)) return true;
  if (/^[a-z]{4,}$/i.test(text) && !(text.toLowerCase() in MEIHUA_SEASON)) return true;
  return false;
}

export function mappedOrNull(
  map: Record<string, string>,
  raw: string | null | undefined,
): string | null {
  if (!raw) return null;
  return raw in map ? map[raw] : null;
}

export function seasonLabel(raw: string | null | undefined): string | null {
  if (!raw) return null;
  if (raw in MEIHUA_SEASON) return MEIHUA_SEASON[raw];
  if (SEASONS_ZH.has(raw)) return raw;
  if (looksInternal(raw)) return null;
  return raw;
}

export function strengthStateLabel(raw: string | null | undefined): string | null {
  if (!raw) return null;
  if (STRENGTH_STATES.has(raw)) return raw;
  if (looksInternal(raw)) return null;
  return raw;
}

export function displayBoundary(
  raw: string | null | undefined,
  footer: string,
): string | null {
  if (!raw) return null;
  const trimmed = raw.trim();
  if (!trimmed || trimmed === footer) return null;
  if (looksInternal(trimmed)) return null;
  if (/[A-Za-z]/.test(trimmed) && trimmed.split(/\s+/).length >= 4) return null;
  return trimmed;
}
