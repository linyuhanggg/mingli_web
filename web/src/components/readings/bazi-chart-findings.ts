/**
 * 免费本命盘 findings / claim_units：只抽出可上屏的中文标题与正文。
 * 内部 id、snake_case、未知键一律不渲染；没有标题+正文则整条丢弃。
 */

export type NatalFindingCard = {
  title: string;
  body: string;
};

const TITLE_BY_UNIT: Readonly<Record<string, string>> = {
  "pillar-roles": "柱位职分",
  "three-yuan-structure": "三元结构",
  "element-flow-inventory": "五行流转盘点",
};

const BODY_KEYS = ["public_text", "text", "display_text", "body"] as const;
const TITLE_KEYS = ["title", "heading", "label"] as const;
const UNIT_KEYS = ["claim_unit_id", "unit_id", "kind_id", "kind", "id"] as const;

/** Runtime 工程边界句 → 中文产品语（禁止英文 / snake_case 上屏） */
const PRODUCT_BOUNDARY_LABELS: Readonly<Record<string, string>> = {
  "no Shensha item may override month command, structure, strength, Tiaohou, Ten Gods, or luck/transit facts":
    "神煞只作辅助标注，不覆盖月令、格局、旺衰、调候、十神或大运流年事实",
  "inventory only; these counts do not determine 旺衰 or 用神":
    "仅作五行计数陈列，不据此裁定旺衰或用神",
  "inventory only": "仅作五行计数陈列",
};

const FACT_DOMAIN_LABELS: Readonly<Record<string, string>> = {
  month_command: "月令",
  structure: "格局",
  strength: "旺衰",
  tiaohou: "调候",
  ten_gods: "十神",
  luck_cycles: "大运",
  transit_facts: "流年流月事实",
  four_pillars: "四柱",
  day_master: "日主",
  element_inventory: "五行盘点",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function hasChinese(text: string): boolean {
  return /[\u3400-\u9fff]/.test(text);
}

export function looksInternal(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) return true;
  if (/\b(?:finding|fact|evidence|claim)[:/]/i.test(trimmed)) return true;
  if (/\b[a-z]+(?:_[a-z0-9]+)+\b/i.test(trimmed)) return true;
  if (/\b[a-z][a-z0-9]*\.[a-z0-9._-]+\b/i.test(trimmed)) return true;
  if (!hasChinese(trimmed)) return true;
  return false;
}

function normalizeUnitId(raw: string): string {
  const withoutPrefix = raw.trim().replace(/^(?:finding|claim|kind|unit)[:/]/i, "");
  const last = withoutPrefix.split(/[./]/).pop() ?? withoutPrefix;
  return last.replace(/-v\d+$/i, "");
}

function titleForUnit(id: string): string | null {
  const normalized = normalizeUnitId(id);
  return TITLE_BY_UNIT[normalized] ?? TITLE_BY_UNIT[id] ?? null;
}

function unitIdFrom(record: Record<string, unknown>): string | null {
  const direct = firstString(...UNIT_KEYS.map((key) => record[key]));
  if (direct) return direct;
  if (isRecord(record.data)) {
    const nested = firstString(
      record.data.claim_unit_id,
      record.data.unit_id,
      record.data.kind_id,
    );
    if (nested) return nested;
  }
  const ref = firstString(record.ref);
  if (ref?.includes("/")) {
    const last = ref.split("/").pop();
    if (last) return last;
  }
  return null;
}

function chineseTitleFrom(record: Record<string, unknown>): string | null {
  for (const key of TITLE_KEYS) {
    const value = firstString(record[key]);
    if (value && !looksInternal(value)) return value;
  }
  return null;
}

function bodyFrom(record: Record<string, unknown>): string | null {
  for (const key of BODY_KEYS) {
    const value = firstString(record[key]);
    if (value && !looksInternal(value)) return value;
  }
  return null;
}

function toCard(item: unknown): NatalFindingCard | null {
  if (!isRecord(item)) return null;
  const body = bodyFrom(item);
  if (!body) return null;
  const unitId = unitIdFrom(item);
  const title = (unitId ? titleForUnit(unitId) : null) ?? chineseTitleFrom(item);
  if (!title) return null;
  return { title, body };
}

export function collectNatalFindingSource(...chunks: unknown[]): unknown[] {
  const items: unknown[] = [];
  for (const chunk of chunks) {
    if (chunk == null) continue;
    if (Array.isArray(chunk)) {
      items.push(...chunk);
      continue;
    }
    if (isRecord(chunk)) {
      if (Array.isArray(chunk.findings)) items.push(...chunk.findings);
      if (Array.isArray(chunk.claim_units)) items.push(...chunk.claim_units);
    }
  }
  return items;
}

export function natalFindingCards(source: unknown): NatalFindingCard[] {
  const items = Array.isArray(source) ? source : collectNatalFindingSource(source);
  const cards: NatalFindingCard[] = [];
  const seen = new Set<string>();
  for (const item of items) {
    const card = toCard(item);
    if (!card) continue;
    const key = `${card.title}\n${card.body}`;
    if (seen.has(key)) continue;
    seen.add(key);
    cards.push(card);
  }
  return cards;
}

/** 产品可见边界句：映射英文工程文案；未知非中文句降级为通用说明。 */
export function visibleProductBoundary(value: string): string {
  if (PRODUCT_BOUNDARY_LABELS[value]) return PRODUCT_BOUNDARY_LABELS[value];
  return hasChinese(value) ? value : "服务端已记录";
}

/** 内部域 key → 中文；未知 snake_case 丢弃，不原样上屏。 */
export function visibleFactDomainLabels(keys: ReadonlyArray<string>): string {
  return keys
    .map((key) => {
      const mapped = FACT_DOMAIN_LABELS[key];
      if (mapped) return mapped;
      if (looksInternal(key)) return null;
      return key;
    })
    .filter((item): item is string => Boolean(item))
    .join("、");
}
