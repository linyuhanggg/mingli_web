"use client";

import type { ZiweiCoreFacts } from "@/view-models/registry";

import styles from "./ziwei-major-limit-track.module.css";

type Limit = NonNullable<ZiweiCoreFacts["major_limits"]>[number];

export type ZiweiMajorLimitTrackProps = {
  limits: ZiweiCoreFacts["major_limits"];
  sequence?: ZiweiCoreFacts["major_limit_sequence"];
  selectedBranch?: string | null;
  onSelectLimit?: (palaceBranch: string) => void;
};

function resolveItems(
  limits: ZiweiCoreFacts["major_limits"],
  sequence: ZiweiCoreFacts["major_limit_sequence"],
): ReadonlyArray<Limit> | null {
  if (limits?.length) return limits;
  if (sequence?.length) return sequence;
  return null;
}

export function ZiweiMajorLimitTrack({
  limits,
  sequence = null,
  selectedBranch = null,
  onSelectLimit,
}: ZiweiMajorLimitTrackProps) {
  const items = resolveItems(limits, sequence);
  if (!items) return null;

  return (
    <section aria-label="大限" className={styles.panel} data-slot="major-limits">
      <div className={styles.viewport}>
        <ol aria-label="大限序列" className={styles.track}>
          {items.map((item, index) => {
            const ganzhi = `${item.heavenly_stem}${item.earthly_branch}`;
            const ages = `${item.age_start}–${item.age_end}`;
            return (
              <li className={styles.step} key={`${item.sequence}-${item.palace_branch}-${index}`}>
                <button
                  aria-label={`${item.sequence} ${item.palace} ${ganzhi} ${ages}`}
                  className={styles.cell}
                  data-highlight={selectedBranch === item.palace_branch ? "true" : undefined}
                  data-palace-branch={item.palace_branch}
                  onClick={() => onSelectLimit?.(item.palace_branch)}
                  type="button"
                >
                  <span className={styles.seq}>{item.sequence}</span>
                  <span className={styles.palace}>{item.palace}</span>
                  <span className={styles.ganzhi}>{ganzhi}</span>
                  <span className={styles.ages}>{ages}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
