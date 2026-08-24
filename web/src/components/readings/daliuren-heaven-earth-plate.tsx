"use client";

import type { DaliurenChartViewModel } from "@/view-models/registry";

import styles from "./daliuren-heaven-earth-plate.module.css";

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;

export type DaliurenHeavenEarthPlateProps = {
  anchorEarthBranches?: ReadonlySet<string>;
  earthPlate: CoreFacts["earth_plate"];
  heavenPlate?: CoreFacts["heaven_plate"];
  heavenlyGenerals?: CoreFacts["heavenly_generals"];
  plateOffset?: CoreFacts["plate_offset"];
  noblePerson?: CoreFacts["noble_person"];
  xunkong?: CoreFacts["xunkong"];
};

function TimingMark() {
  return (
    <span className={styles.timingBadge} data-badge="timing">
      应期
    </span>
  );
}

function readString(value: unknown, key: string): string | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const field = (value as Record<string, unknown>)[key];
  return typeof field === "string" && field.trim() ? field.trim() : null;
}

function asEarthPlate(value: CoreFacts["earth_plate"]): readonly string[] | null {
  if (!value || value.length !== 12) return null;
  const items: string[] = [];
  for (const item of value) {
    if (typeof item !== "string" || !item.trim()) return null;
    items.push(item);
  }
  return items;
}

function voidBranches(value: unknown): ReadonlySet<string> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return new Set();
  const branches = (value as { branches?: unknown }).branches;
  if (!Array.isArray(branches)) return new Set();
  return new Set(
    branches.filter((item): item is string => typeof item === "string" && Boolean(item.trim())).map((item) => item.trim()),
  );
}

function mapByEarth(
  items: ReadonlyArray<unknown> | null | undefined,
  earthSet: ReadonlySet<string>,
  valueKey: "heaven" | "general",
): ReadonlyMap<string, string> {
  const mapped = new Map<string, string>();
  if (!items) return mapped;
  for (const item of items) {
    const earth = readString(item, "earth");
    const value = readString(item, valueKey);
    if (!earth || !value || !earthSet.has(earth) || mapped.has(earth)) continue;
    mapped.set(earth, value);
  }
  return mapped;
}

export function DaliurenHeavenEarthPlate({
  anchorEarthBranches = new Set(),
  earthPlate,
  heavenPlate = null,
  heavenlyGenerals = null,
  plateOffset = null,
  noblePerson = null,
  xunkong = null,
}: DaliurenHeavenEarthPlateProps) {
  const earth = asEarthPlate(earthPlate);
  if (!earth) return null;

  const earthSet = new Set(earth);
  const heavens = mapByEarth(heavenPlate, earthSet, "heaven");
  const generals = mapByEarth(heavenlyGenerals, earthSet, "general");
  const timingAnchors = new Set([...anchorEarthBranches].filter((branch) => earthSet.has(branch)));
  const voids = voidBranches(xunkong);
  const showHeaven = heavens.size > 0;
  const showGeneral = generals.size > 0;
  const noble = readString(noblePerson, "earth_position");
  const nobleEarthPosition = noble && earthSet.has(noble) ? noble : null;
  const offset = typeof plateOffset === "number" && Number.isFinite(plateOffset) ? plateOffset : null;

  return (
    <details
      className={styles.panel}
      data-offset={offset == null ? undefined : String(offset)}
      data-slot="heaven-earth"
    >
      <summary className={styles.summary}>天地盘</summary>
      <div className={styles.body}>
        <ol
          aria-hidden="true"
          className={styles.ring}
          data-ring="earth"
        >
          {earth.map((branch, index) => (
            <li
              className={styles.spoke}
              data-branch={branch}
              data-noble={nobleEarthPosition === branch ? "true" : undefined}
              data-timing={timingAnchors.has(branch) ? "true" : undefined}
              data-void={voids.has(branch) ? "true" : undefined}
              key={branch}
              style={{ ["--spoke" as string]: String(index) }}
            >
              <span className={styles.earth}>{branch}</span>
              {timingAnchors.has(branch) ? <TimingMark /> : null}
              {voids.has(branch) ? <span className={styles.voidBadge}>空</span> : null}
              {showHeaven && heavens.get(branch) ? (
                <span className={styles.heaven}>{heavens.get(branch)}</span>
              ) : null}
              {showGeneral && generals.get(branch) ? (
                <span className={styles.general}>{generals.get(branch)}</span>
              ) : null}
            </li>
          ))}
        </ol>
        <table className={styles.table} aria-label="天地盘">
          <thead>
            <tr>
              <th scope="col">地盘支</th>
              {showHeaven ? <th scope="col">天盘支</th> : null}
              {showGeneral ? <th scope="col">天将</th> : null}
            </tr>
          </thead>
          <tbody>
            {earth.map((branch) => (
              <tr
                data-branch={branch}
                data-noble={nobleEarthPosition === branch ? "true" : undefined}
                data-timing={timingAnchors.has(branch) ? "true" : undefined}
                data-void={voids.has(branch) ? "true" : undefined}
                key={branch}
              >
                <th scope="row">
                  {branch}
                  {nobleEarthPosition === branch ? (
                    <span className={styles.nobleBadge}>贵人落地</span>
                  ) : null}
                  {timingAnchors.has(branch) ? <TimingMark /> : null}
                  {voids.has(branch) ? <span className={styles.voidBadge}>空</span> : null}
                </th>
                {showHeaven ? <td>{heavens.get(branch) ?? ""}</td> : null}
                {showGeneral ? <td>{generals.get(branch) ?? ""}</td> : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
