"use client";

import { useMemo, useState } from "react";

import type { ZiweiCoreFacts } from "@/view-models/registry";

import styles from "./ziwei-star-fact-list.module.css";

type StarFact = NonNullable<ZiweiCoreFacts["star_facts"]>[number];

const BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"] as const;

export type ZiweiStarFactListProps = {
  items: ZiweiCoreFacts["star_facts"];
  selectedBranch?: string | null;
  onSelectStar?: (palaceBranch: string) => void;
};

function fieldText(value: string | null | undefined): string {
  return value ?? "";
}

function matchesQuery(item: StarFact, query: string): boolean {
  const needle = query.trim();
  if (!needle) return true;
  return [item.name, item.star_type, item.brightness, item.palace, item.palace_branch].some((value) =>
    fieldText(value).includes(needle),
  );
}

function groupByPalaceBranch(items: ReadonlyArray<StarFact>): ReadonlyArray<readonly [string, ReadonlyArray<StarFact>]> {
  const buckets = new Map<string, StarFact[]>();
  for (const item of items) {
    const bucket = buckets.get(item.palace_branch);
    if (bucket) {
      bucket.push(item);
      continue;
    }
    buckets.set(item.palace_branch, [item]);
  }

  const ordered: Array<readonly [string, ReadonlyArray<StarFact>]> = [];
  for (const branch of BRANCHES) {
    const rows = buckets.get(branch);
    if (rows?.length) ordered.push([branch, rows]);
  }
  for (const [branch, rows] of buckets) {
    if (!(BRANCHES as readonly string[]).includes(branch) && rows.length) {
      ordered.push([branch, rows]);
    }
  }
  return ordered;
}

export function ZiweiStarFactList({
  items,
  selectedBranch = null,
  onSelectStar,
}: ZiweiStarFactListProps) {
  const [query, setQuery] = useState("");

  const groups = useMemo(() => {
    if (!items?.length) return [];
    return groupByPalaceBranch(items.filter((item) => matchesQuery(item, query)));
  }, [items, query]);

  if (!items?.length) return null;

  return (
    <section aria-label="星曜明细" className={styles.panel} data-slot="star-facts">
      <details className={styles.details} open>
        <summary className={styles.summary}>星曜明细</summary>
        <label className={styles.filter} htmlFor="ziwei-star-fact-filter">
          过滤星曜
          <input
            className={styles.input}
            id="ziwei-star-fact-filter"
            onChange={(event) => setQuery(event.target.value)}
            type="search"
            value={query}
          />
        </label>
        {groups.map(([branch, rows]) => {
          const title = rows[0]?.palace ?? branch;
          return (
            <section aria-label={title} className={styles.group} key={branch} role="group">
              <p className={styles.palace}>{title}</p>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>星名</th>
                    <th>类型</th>
                    <th>范围</th>
                    <th>亮度</th>
                    <th>所在宫</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, index) => (
                    <tr
                      data-highlight={selectedBranch === row.palace_branch ? "true" : undefined}
                      data-palace-branch={row.palace_branch}
                      key={`${row.name}-${row.palace_branch}-${index}`}
                    >
                      <td>
                        <button
                          className={styles.star}
                          onClick={() => onSelectStar?.(row.palace_branch)}
                          type="button"
                        >
                          {row.name}
                        </button>
                      </td>
                      <td>{fieldText(row.star_type)}</td>
                      <td>{fieldText(row.scope)}</td>
                      <td className={styles.brightness}>{fieldText(row.brightness)}</td>
                      <td>{`${row.palace}${row.palace_branch}`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          );
        })}
      </details>
    </section>
  );
}
