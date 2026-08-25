"use client";

import { useRef, useState, type KeyboardEvent, type Ref } from "react";

import type { DaliurenChartViewModel } from "@/view-models/registry";

import styles from "./daliuren-heaven-earth-plate.module.css";

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;
type FactKind = "earth" | "heaven" | "general";
type PlateCellId = `${string}:${FactKind}`;
type PlateNavKey = "ArrowLeft" | "ArrowRight" | "ArrowUp" | "ArrowDown" | "Home" | "End";

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

const PLATE_NAV_KEYS: ReadonlySet<string> = new Set([
  "ArrowLeft",
  "ArrowRight",
  "ArrowUp",
  "ArrowDown",
  "Home",
  "End",
]);

function plateCellId(earth: string, kind: FactKind): PlateCellId {
  return `${earth}:${kind}`;
}

function parsePlateCell(id: PlateCellId): { earth: string; kind: FactKind } | null {
  const match = /^(.*):(earth|heaven|general)$/.exec(id);
  if (!match) return null;
  return { earth: match[1], kind: match[2] as FactKind };
}

function visibleKinds(showHeaven: boolean, showGeneral: boolean): FactKind[] {
  const kinds: FactKind[] = ["earth"];
  if (showHeaven) kinds.push("heaven");
  if (showGeneral) kinds.push("general");
  return kinds;
}

function plateNeighbor(
  id: PlateCellId,
  key: PlateNavKey,
  earths: readonly string[],
  kinds: readonly FactKind[],
  valueAt: (earth: string, kind: FactKind) => string | null,
): PlateCellId {
  const parsed = parsePlateCell(id);
  if (!parsed) return id;
  const cells: PlateCellId[] = [];
  for (const earth of earths) {
    for (const kind of kinds) {
      if (valueAt(earth, kind)) cells.push(plateCellId(earth, kind));
    }
  }
  if (cells.length === 0) return id;
  if (key === "Home") return cells[0];
  if (key === "End") return cells[cells.length - 1];

  const row = earths.indexOf(parsed.earth);
  const col = kinds.indexOf(parsed.kind);
  if (row < 0 || col < 0) return cells[0];

  if (key === "ArrowLeft" || key === "ArrowRight") {
    const step = key === "ArrowRight" ? 1 : -1;
    for (let nextCol = col + step; nextCol >= 0 && nextCol < kinds.length; nextCol += step) {
      if (valueAt(parsed.earth, kinds[nextCol])) return plateCellId(parsed.earth, kinds[nextCol]);
    }
    return id;
  }

  const step = key === "ArrowDown" ? 1 : -1;
  for (let nextRow = row + step; nextRow >= 0 && nextRow < earths.length; nextRow += step) {
    if (valueAt(earths[nextRow], parsed.kind)) return plateCellId(earths[nextRow], parsed.kind);
  }
  return id;
}

function PlateFactButton({
  kind,
  value,
  active,
  locked,
  tabIndex,
  buttonRef,
  onToggleFact,
  onFocusFact,
  onBlurFact,
  onHoverFact,
  onLeaveFact,
  onKeyDown,
}: {
  kind: FactKind;
  value: string;
  active: boolean;
  locked: boolean;
  tabIndex: number;
  buttonRef: Ref<HTMLButtonElement>;
  onToggleFact: (value: string) => void;
  onFocusFact: (value: string) => void;
  onBlurFact: (value: string) => void;
  onHoverFact: (value: string) => void;
  onLeaveFact: (value: string) => void;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
}) {
  return (
    <button
      className={styles.fact}
      type="button"
      ref={buttonRef}
      tabIndex={tabIndex}
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
  const earthPlateValues = asEarthPlate(earthPlate);
  const cellRefs = useRef<Partial<Record<PlateCellId, HTMLButtonElement | null>>>({});
  const [rovingId, setRovingId] = useState<PlateCellId | null>(null);
  if (!earthPlateValues) return null;
  const earth = earthPlateValues;

  const earthSet = new Set(earth);
  const heavens = mapByEarth(heavenPlate, earthSet, "heaven");
  const generals = mapByEarth(heavenlyGenerals, earthSet, "general");
  const timingAnchors = new Set([...anchorEarthBranches].filter((branch) => earthSet.has(branch)));
  const voids = voidBranches(xunkong);
  const showHeaven = heavens.size > 0;
  const showGeneral = generals.size > 0;
  const kinds = visibleKinds(showHeaven, showGeneral);
  const noble = readString(noblePerson, "earth_position");
  const nobleEarthPosition = noble && earthSet.has(noble) ? noble : null;
  const offset = typeof plateOffset === "number" && Number.isFinite(plateOffset) ? plateOffset : null;
  const active = factSet(activeFact);
  const locked = factSet(lockedFacts);
  const interactive = Boolean(onToggleFact && onFocusFact && onBlurFact && onHoverFact && onLeaveFact && onClearLock);

  function plateValue(branch: string, kind: FactKind): string | null {
    if (kind === "earth") return branch;
    if (kind === "heaven") return heavens.get(branch) ?? null;
    return generals.get(branch) ?? null;
  }

  const parsedRoving = rovingId ? parsePlateCell(rovingId) : null;
  const currentRoving: PlateCellId =
    parsedRoving && plateValue(parsedRoving.earth, parsedRoving.kind)
      ? plateCellId(parsedRoving.earth, parsedRoving.kind)
      : plateCellId(earth[0], "earth");

  function isActiveValue(value: string | null | undefined): boolean {
    return hasFact(active, value);
  }

  function focusPlateCell(id: PlateCellId) {
    setRovingId(id);
    cellRefs.current[id]?.focus();
  }

  function onFactKeyDown(event: KeyboardEvent<HTMLButtonElement>, id: PlateCellId) {
    if (event.key === "Escape") {
      event.preventDefault();
      onClearLock?.();
      return;
    }
    if (!PLATE_NAV_KEYS.has(event.key)) return;
    event.preventDefault();
    focusPlateCell(plateNeighbor(id, event.key as PlateNavKey, earth, kinds, plateValue));
  }

  function renderFact(kind: FactKind, value: string | null, branch: string) {
    if (!value) return null;
    if (!interactive || !onToggleFact || !onFocusFact || !onBlurFact || !onHoverFact || !onLeaveFact || !onClearLock) {
      return value;
    }
    const id = plateCellId(branch, kind);
    return (
      <PlateFactButton
        kind={kind}
        value={value}
        active={isActiveValue(value)}
        locked={hasFact(locked, value)}
        tabIndex={currentRoving === id ? 0 : -1}
        buttonRef={(node) => {
          cellRefs.current[id] = node;
        }}
        onBlurFact={onBlurFact}
        onFocusFact={(next) => {
          setRovingId(id);
          onFocusFact(next);
        }}
        onHoverFact={onHoverFact}
        onLeaveFact={onLeaveFact}
        onToggleFact={onToggleFact}
        onKeyDown={(event) => onFactKeyDown(event, id)}
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
                <span
                  className={styles.earth}
                  data-active={earthActive ? "true" : "false"}
                  data-fact="earth"
                  {...ringFactProps(branch)}
                >
                  {branch}
                  {timingAnchors.has(branch) ? <TimingMark /> : null}
                  {voids.has(branch) ? <span className={styles.voidBadge}>空</span> : null}
                </span>
                {showHeaven && heaven ? (
                  <span
                    className={styles.heaven}
                    data-active={heavenActive ? "true" : "false"}
                    data-fact="heaven"
                    {...ringFactProps(heaven)}
                  >
                    {heaven}
                  </span>
                ) : null}
                {showGeneral && general ? (
                  <span
                    className={styles.general}
                    data-active={generalActive ? "true" : "false"}
                    data-fact="general"
                    {...ringFactProps(general)}
                  >
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
                    {renderFact("earth", branch, branch)}
                    {nobleEarthPosition === branch ? (
                      <span className={styles.nobleBadge}>贵人落地</span>
                    ) : null}
                    {timingAnchors.has(branch) ? <TimingMark /> : null}
                    {voids.has(branch) ? <span className={styles.voidBadge}>空</span> : null}
                  </th>
                  {showHeaven ? (
                    <td data-active={heavenActive ? "true" : "false"}>{renderFact("heaven", heaven, branch)}</td>
                  ) : null}
                  {showGeneral ? (
                    <td data-active={generalActive ? "true" : "false"}>{renderFact("general", general, branch)}</td>
                  ) : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
}
