"use client";

import type { ZiweiCoreFacts } from "@/view-models/registry";

import styles from "./ziwei-transformation-table.module.css";

type Transformation = NonNullable<ZiweiCoreFacts["transformations"]>[number];

const HUA_MARK: Readonly<Record<string, string>> = {
  禄: "禄",
  化禄: "禄",
  权: "权",
  化权: "权",
  科: "科",
  化科: "科",
  忌: "忌",
  化忌: "忌",
};

export type ZiweiTransformationTableProps = {
  items: ZiweiCoreFacts["transformations"];
  selectedBranch?: string | null;
  onSelectStar?: (palaceBranch: string) => void;
};

function huaMark(value: string): string | null {
  return HUA_MARK[value] ?? (/[禄权科忌]/.test(value) ? value.replace("化", "") : null);
}

function groupByScope(
  items: ReadonlyArray<Transformation>,
): ReadonlyArray<readonly [string, ReadonlyArray<Transformation>]> {
  const order: string[] = [];
  const buckets = new Map<string, Transformation[]>();
  for (const item of items) {
    const scope = item.scope;
    const bucket = buckets.get(scope);
    if (bucket) {
      bucket.push(item);
      continue;
    }
    buckets.set(scope, [item]);
    order.push(scope);
  }
  return order.map((scope) => [scope, buckets.get(scope) ?? []] as const);
}

export function ZiweiTransformationTable({
  items,
  selectedBranch = null,
  onSelectStar,
}: ZiweiTransformationTableProps) {
  if (!items?.length) return null;

  return (
    <section aria-label="四化" className={styles.panel} data-slot="transformations">
      {groupByScope(items).map(([scope, rows]) => (
        <section aria-label={scope} className={styles.group} key={scope} role="group">
          <p className={styles.scope}>{scope}</p>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>星</th>
                <th>化</th>
                <th>所在宫</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => {
                const hua = huaMark(row.transformation);
                return (
                  <tr
                    data-highlight={selectedBranch === row.palace_branch ? "true" : undefined}
                    data-palace-branch={row.palace_branch}
                    key={`${scope}-${row.star}-${row.palace_branch}-${index}`}
                  >
                    <td>
                      <button
                        className={styles.star}
                        onClick={() => onSelectStar?.(row.palace_branch)}
                        type="button"
                      >
                        {row.star}
                      </button>
                    </td>
                    <td>{hua ? <span className={styles.hua}>{hua}</span> : null}</td>
                    <td>{`${row.palace}${row.palace_branch}`}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      ))}
    </section>
  );
}
