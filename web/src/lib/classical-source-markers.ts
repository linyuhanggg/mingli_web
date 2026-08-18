/**
 * DESIGN.md §21.3 第 1/2 级：盘面元素旁的来源标记与「有 N 条古法涉及此处」。
 *
 * 归属只依据下面这张**显式路径表**。§19.1 要求映射表是显式常量、不得用启发式
 * 猜测；§17 禁止把 `fact_paths` 这类内部引用展示给用户，所以本模块只输出计数，
 * 不输出任何路径本身。未登记的 fact path 一律不归属——宁可不标，不错标。
 */

export type PillarId = "year" | "month" | "day" | "hour";

export const PILLAR_IDS: readonly PillarId[] = ["year", "month", "day", "hour"];

export type PillarSourceCounts = Record<PillarId, number>;

/** 只承认 output 命名空间；其余 chart_facts 子树（如历法归一化）不归属到柱。 */
const OUTPUT_NAMESPACE = "/chart_facts/output";

/** 形如 `<prefix>/<pillar>/...`，柱名恰好在 prefix 之后一段。 */
const PILLAR_INDEXED_PREFIXES: readonly string[] = [
  "/four_pillars",
  "/hidden_stems",
  "/ten_gods/hidden_stems",
];

/** 形如 `<prefix>/...`，整段固定归属某一柱。 */
const FIXED_PILLAR_PREFIXES: ReadonlyArray<readonly [string, PillarId]> = [
  ["/day_master", "day"],
  ["/month_command", "month"],
];

/**
 * 真实 Runtime 返回 `fact:/chart_facts/output/...` 全路径，部分投影与夹具用
 * `/day_master/...` 短路径。两种都归一到 output 命名空间内的短路径；
 * 其它 `/chart_facts/*` 子树返回 null，不参与归属。
 */
function normalizePath(factPath: string): string | null {
  const raw = factPath.startsWith("fact:") ? factPath.slice("fact:".length) : factPath;
  if (raw.startsWith(`${OUTPUT_NAMESPACE}/`)) {
    return raw.slice(OUTPUT_NAMESPACE.length);
  }
  if (raw.startsWith("/chart_facts/")) return null;
  return raw;
}

export function isPillarId(value: string | undefined): value is PillarId {
  return value !== undefined && (PILLAR_IDS as readonly string[]).includes(value);
}

/** 单条 fact path 归属到的柱；未登记返回 null。 */
export function resolvePillarForFactPath(factPath: string): PillarId | null {
  const path = normalizePath(factPath);
  if (path === null) return null;

  for (const [prefix, pillar] of FIXED_PILLAR_PREFIXES) {
    if (path === prefix || path.startsWith(`${prefix}/`)) return pillar;
  }

  for (const prefix of PILLAR_INDEXED_PREFIXES) {
    if (!path.startsWith(`${prefix}/`)) continue;
    const next = path.slice(prefix.length + 1).split("/")[0];
    if (isPillarId(next)) return next;
  }

  return null;
}

/**
 * 每柱有多少条古法条目涉及。同一条 pattern 命中同一柱的多条路径只计一次。
 */
export function countClassicalSourcesByPillar(
  patterns: ReadonlyArray<{ readonly fact_paths?: readonly string[] | null }>,
): PillarSourceCounts {
  const counts: PillarSourceCounts = { year: 0, month: 0, day: 0, hour: 0 };

  for (const pattern of patterns) {
    const touched = new Set<PillarId>();
    for (const factPath of pattern.fact_paths ?? []) {
      const pillar = resolvePillarForFactPath(factPath);
      if (pillar) touched.add(pillar);
    }
    for (const pillar of touched) counts[pillar] += 1;
  }

  return counts;
}
