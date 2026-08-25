"use client";

import type { KeyboardEvent } from "react";

import type { DaliurenChartViewModel } from "@/view-models/registry";

import styles from "./daliuren-heaven-earth-plate.module.css";

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;
type FactKind = "earth" | "heaven" | "general";

const FACT_KIND_LABEL: Readonly<Record<FactKind, string>> = {
  earth: "地盘",
  heaven: "天盘",
  general: "天将",
};

export type DaliurenHeavenEarthPlateProps = {
  activeFact?: string | readonly string[] | null;
  lockedFacts?: string | readonly string[] | null;
  anchorEarthBranches?: ReadonlySet<string>;
  earthPlate: CoreFacts["earth_plate"];
  heavenPlate?: CoreFacts["heaven_plate"];
  heavenlyGenerals?: CoreFacts["heavenly_generals"];
  plateOffset?: CoreFacts["plate_offset"];
  noblePerson?: CoreFacts["noble_person"];
  xunkong?: CoreFacts["xunkong"];
  onToggleFact?: (value: string) => void;
  onFocusFact?: (value: string) => void;
  onBlurFact?: (value: string) => void;
  onHoverFact?: (value: string) => void;
  onLeaveFact?: (value: string) => void;
  onClearLock?: () => void;
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

function factSet(value: string | readonly string[] | null | undefined): ReadonlySet<string> {
  const items = value == null ? [] : typeof value === "string" ? [value] : value;
  return new Set(items.map((item) => item.trim()).filter(Boolean));
}

function hasFact(facts: ReadonlySet<string>, value: string | null | undefined): boolean {
  return typeof value === "string" && value.length > 0 && facts.has(value);
}

function PlateFactButton({
  kind,
  value,
  active,
  locked,
  onToggleFact,
  onFocusFact,
  onBlurFact,
  onHoverFact,
  onLeaveFact,
  onClearLock,
}: {
  kind: FactKind;
  value: string;
  active: boolean;
  locked: boolean;
  onToggleFact: (value: string) => void;
  onFocusFact: (value: string) => void;
  onBlurFact: (value: string) => void;
  onHoverFact: (value: string) => void;
  onLeaveFact: (value: string) => void;
  onClearLock: () => void;
}) {
  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key !== "Escape") return;
    event.preventDefault();
    onClearLock();
  }

  return (
    <button
      className={styles.fact}
      type="button"
      data-active={active ? "true" : "false"}
      data-chip={kind === "general" ? "general" : undefined}
      data-fact={kind}
      aria-label={`${FACT_KIND_LABEL[kind]} ${value}`}
      aria-pressed={locked}
      onBlur={() => onBlurFact(value)}
      onClick={() => onToggleFact(value)}
      onFocus={() => onFocusFact(value)}
      onKeyDown={onKeyDown}
      onPointerEnter={() => onHoverFact(value)}
      onPointerLeave={() => onLeaveFact(value)}
    >
      {value}
    </button>
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
  activeFact = null,
  lockedFacts = null,
  anchorEarthBranches = new Set(),
  earthPlate,
  heavenPlate = null,
  heavenlyGenerals = null,
  plateOffset = null,
  noblePerson = null,
  xunkong = null,
  onToggleFact,
  onFocusFact,
  onBlurFact,
  onHoverFact,
  onLeaveFact,
  onClearLock,
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
  const active = factSet(activeFact);
  const locked = factSet(lockedFacts);
  const interactive = Boolean(onToggleFact && onFocusFact && onBlurFact && onHoverFact && onLeaveFact && onClearLock);

  function isActiveValue(value: string | null | undefined): boolean {
    return hasFact(active, value);
  }

  function renderFact(kind: FactKind, value: string | null) {
    if (!value) return null;
    if (!interactive || !onToggleFact || !onFocusFact || !onBlurFact || !onHoverFact || !onLeaveFact || !onClearLock) {
      return value;
    }
    return (
      <PlateFactButton
        kind={kind}
        value={value}
        active={isActiveValue(value)}
        locked={hasFact(locked, value)}
        onBlurFact={onBlurFact}
        onClearLock={onClearLock}
        onFocusFact={onFocusFact}
        onHoverFact={onHoverFact}
        onLeaveFact={onLeaveFact}
        onToggleFact={onToggleFact}
      />
    );
  }

  function ringFactProps(value: string | null) {
    if (!value || !interactive || !onToggleFact || !onHoverFact || !onLeaveFact) return {};
    return {
      role: "presentation" as const,
      onClick: () => onToggleFact(value),
      onPointerEnter: () => onHoverFact(value),
      onPointerLeave: () => onLeaveFact(value),
    };
  }

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
          {earth.map((branch, index) => {
            const heaven = heavens.get(branch) ?? null;
            const general = generals.get(branch) ?? null;
            const earthActive = isActiveValue(branch);
            const heavenActive = isActiveValue(heaven);
            const generalActive = isActiveValue(general);
            return (
              <li
                className={styles.spoke}
                data-active={earthActive || heavenActive || generalActive ? "true" : "false"}
                data-branch={branch}
                data-noble={nobleEarthPosition === branch ? "true" : undefined}
                data-timing={timingAnchors.has(branch) ? "true" : undefined}
                data-void={voids.has(branch) ? "true" : undefined}
                key={branch}
                style={{ ["--spoke" as string]: String(index) }}
              >
                <span className={styles.earth} data-active={earthActive ? "true" : "false"} {...ringFactProps(branch)}>
                  {branch}
                </span>
                {timingAnchors.has(branch) ? <TimingMark /> : null}
                {voids.has(branch) ? <span className={styles.voidBadge}>空</span> : null}
                {showHeaven && heaven ? (
                  <span className={styles.heaven} data-active={heavenActive ? "true" : "false"} {...ringFactProps(heaven)}>
                    {heaven}
                  </span>
                ) : null}
                {showGeneral && general ? (
                  <span className={styles.general} data-active={generalActive ? "true" : "false"} {...ringFactProps(general)}>
                    {general}
                  </span>
                ) : null}
              </li>
            );
          })}
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
            {earth.map((branch) => {
              const heaven = heavens.get(branch) ?? null;
              const general = generals.get(branch) ?? null;
              const earthActive = isActiveValue(branch);
              const heavenActive = isActiveValue(heaven);
              const generalActive = isActiveValue(general);
              return (
                <tr
                  data-active={earthActive || heavenActive || generalActive ? "true" : "false"}
                  data-branch={branch}
                  data-noble={nobleEarthPosition === branch ? "true" : undefined}
                  data-timing={timingAnchors.has(branch) ? "true" : undefined}
                  data-void={voids.has(branch) ? "true" : undefined}
                  key={branch}
                >
                  <th data-active={earthActive ? "true" : "false"} scope="row">
                    {renderFact("earth", branch)}
                    {nobleEarthPosition === branch ? (
                      <span className={styles.nobleBadge}>贵人落地</span>
                    ) : null}
                    {timingAnchors.has(branch) ? <TimingMark /> : null}
                    {voids.has(branch) ? <span className={styles.voidBadge}>空</span> : null}
                  </th>
                  {showHeaven ? <td data-active={heavenActive ? "true" : "false"}>{renderFact("heaven", heaven)}</td> : null}
                  {showGeneral ? <td data-active={generalActive ? "true" : "false"}>{renderFact("general", general)}</td> : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
}
