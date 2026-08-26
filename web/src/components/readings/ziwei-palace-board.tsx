"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

import type { ZiweiChartViewModel } from "@/view-models/registry";

import { ZiweiFreeSummary, type ZiweiS4Offer, type ZiweiS4Phase } from "./ziwei-free-summary";
import { ZiweiCaliberBar } from "./ziwei-caliber-bar";
import { ZiweiPalaceDetailDrawer } from "./ziwei-palace-detail-drawer";
import styles from "./ziwei-palace-board.module.css";
import { ZiweiMajorLimitTrack } from "./ziwei-major-limit-track";
import { ZiweiSourcePatternDrawer } from "./ziwei-source-pattern-drawer";
import { ZiweiStarFactList } from "./ziwei-star-fact-list";
import { ZiweiTransformationTable } from "./ziwei-transformation-table";

const BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"] as const;
const VISUAL_BRANCHES = ["巳", "午", "未", "申", "辰", "酉", "卯", "戌", "寅", "丑", "子", "亥"] as const;

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

const DIRECTION_MARK: Readonly<Record<string, string>> = {
  reverse: "逆行",
  forward: "顺行",
  逆: "逆行",
  顺: "顺行",
  逆行: "逆行",
  顺行: "顺行",
};

type Palace = ZiweiChartViewModel["palaces"][number];
type Mode = "ready" | "silhouette" | "loading";
type Layout = "ring" | "list";

const NARROW_LIST_QUERY = "(max-width: 22.5rem)";

function useResolvedLayout(explicit?: Layout): Layout {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    if (explicit) return;
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const media = window.matchMedia(NARROW_LIST_QUERY);
    const apply = () => setNarrow(media.matches);
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [explicit]);
  return explicit ?? (narrow ? "list" : "ring");
}

export type ZiweiPalaceBoardProps = {
  view?: ZiweiChartViewModel;
  mode?: Mode;
  layout?: Layout;
  offer?: ZiweiS4Offer | null;
  s4Phase?: ZiweiS4Phase;
  showInterpretiveSections?: boolean;
};

function GridOwnedCell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div role="row" style={{ display: "contents" }}>
      <div role="gridcell" style={{ display: "contents" }}>
        {children}
      </div>
    </div>
  );
}

function branchIndex(branch: string): number {
  return BRANCHES.indexOf(branch as (typeof BRANCHES)[number]);
}

function stepBranch(branch: string, delta: number): string {
  const index = branchIndex(branch);
  const start = index >= 0 ? index : 0;
  return BRANCHES[(start + delta + BRANCHES.length) % BRANCHES.length];
}

function relatedBranches(branch: string): readonly string[] {
  return [stepBranch(branch, 6), stepBranch(branch, 4), stepBranch(branch, -4)];
}

function decadeText(decadal: Palace["decadal"] | undefined): string | null {
  if (!decadal) return null;
  return `${decadal.age_start}–${decadal.age_end}`;
}

const GOD_KEYS = ["changsheng12", "boshi12", "jiangqian12", "suiqian12"] as const;
type GodKey = (typeof GOD_KEYS)[number];
type GodDensity = "compact" | "full";

function readGod(value: string | null | undefined): string | null {
  const text = value?.trim();
  return text ? text : null;
}

function palaceGods(palace: Palace, density: GodDensity): Array<{ key: GodKey; label: string }> {
  const keys: readonly GodKey[] = density === "compact" ? ["changsheng12"] : GOD_KEYS;
  return keys.flatMap((key) => {
    const label = readGod(palace[key]);
    return label ? [{ key, label }] : [];
  });
}

function boardHasGods(palaces: readonly Palace[] | undefined): boolean {
  return Boolean(palaces?.some((item) => GOD_KEYS.some((key) => readGod(item[key]))));
}

function GodFoot({ palace, density }: { palace: Palace; density: GodDensity }) {
  const gods = palaceGods(palace, density);
  if (!gods.length) return null;
  return (
    <p aria-label="十二神" className={styles.gods}>
      {gods.map((god) => (
        <span className={styles.god} data-god={god.key} key={god.key}>
          {god.label}
        </span>
      ))}
    </p>
  );
}

function DensitySwitch({
  density,
  onChange,
}: {
  density: GodDensity;
  onChange: (next: GodDensity) => void;
}) {
  return (
    <div aria-label="十二神密度" className={styles.density} role="group">
      <button
        aria-pressed={density === "compact"}
        className={styles.densityButton}
        type="button"
        onClick={() => onChange("compact")}
      >
        精简
      </button>
      <button
        aria-pressed={density === "full"}
        className={styles.densityButton}
        type="button"
        onClick={() => onChange("full")}
      >
        完整
      </button>
    </div>
  );
}

function ganzhiText(palace: Pick<Palace, "heavenly_stem" | "earthly_branch"> | undefined): string | null {
  if (!palace?.heavenly_stem || !palace.earthly_branch) return null;
  return `${palace.heavenly_stem}${palace.earthly_branch}`;
}

function huaMark(value: string): string | null {
  return HUA_MARK[value] ?? (/[禄权科忌]/.test(value) ? value.replace("化", "") : null);
}

function directionMark(value: string | null | undefined): string | null {
  if (!value) return null;
  return DIRECTION_MARK[value] ?? (/[\u3400-\u9fff]/u.test(value) ? value : null);
}

function ringFrom(branch: string): readonly string[] {
  const index = branchIndex(branch);
  const start = index >= 0 ? index : 0;
  return BRANCHES.map((_, offset) => BRANCHES[(start + offset) % BRANCHES.length]);
}

function highlightFor(branch: string, selected: string | null): "primary" | "related" | undefined {
  if (!selected) return undefined;
  if (branch === selected) return "primary";
  return relatedBranches(selected).includes(branch) ? "related" : undefined;
}

function CenterFacts({
  view,
  emptyLabel,
}: {
  view?: ZiweiChartViewModel;
  emptyLabel: boolean;
}) {
  const facts = view?.core_facts;
  const soul = facts?.ming_shen?.soul_star?.trim() || null;
  const body = facts?.ming_shen?.body_star?.trim() || null;
  const wuXing = facts?.five_elements_class?.trim() || null;
  const startAge = facts?.major_limit_starting_age;
  const direction = directionMark(facts?.major_limit_direction?.direction);
  const hasAny = Boolean(soul || body || wuXing || startAge != null || direction);

  return (
    <div className={styles.center} data-slot="center" role="group" aria-label="中宫">
      {soul ? (
        <p className={styles.centerLine}>
          <span>命主 </span>
          <strong className={styles.centerName}>{soul}</strong>
        </p>
      ) : null}
      {body ? (
        <p className={styles.centerLine}>
          <span>身主 </span>
          <strong className={styles.centerName}>{body}</strong>
        </p>
      ) : null}
      {wuXing ? <p className={styles.centerLine}>{wuXing}</p> : null}
      {startAge != null ? <p className={styles.centerLine}>{startAge}</p> : null}
      {direction ? <p className={styles.centerLine}>{direction}</p> : null}
      {!hasAny && emptyLabel ? <p className={styles.centerLine}>命盘</p> : null}
    </div>
  );
}

function StarLine({
  name,
  brightness,
  hua,
  kind,
}: {
  name: string;
  brightness: string | null;
  hua: string | null;
  kind: "major" | "minor" | "adjective";
}) {
  return (
    <span className={styles[kind]}>
      {name}
      {brightness ? <sup className={styles.brightness}>{brightness}</sup> : null}
      {hua ? <span className={styles.hua}>{hua}</span> : null}
    </span>
  );
}

function PalaceBody({
  palace,
  brightnessOf,
  huaOf,
  density,
}: {
  palace: Palace;
  brightnessOf: (name: string, branch: string) => string | null;
  huaOf: (name: string, branch: string) => string | null;
  density: GodDensity;
}) {
  const ganzhi = ganzhiText(palace);
  const decade = decadeText(palace.decadal);
  const minors = palace.minor_stars ?? [];
  const adjectives = palace.adjective_stars ?? [];

  return (
    <>
      {palace.major_stars.length || minors.length || adjectives.length ? (
        <div className={styles.stars}>
          {palace.major_stars.map((name) => (
            <StarLine
              brightness={brightnessOf(name, palace.earthly_branch)}
              hua={huaOf(name, palace.earthly_branch)}
              kind="major"
              key={`major-${name}`}
              name={name}
            />
          ))}
          {minors.map((star) =>
            star.name ? (
              <StarLine
                brightness={star.brightness ?? brightnessOf(star.name, palace.earthly_branch)}
                hua={huaOf(star.name, palace.earthly_branch)}
                kind="minor"
                key={`minor-${star.name}`}
                name={star.name}
              />
            ) : null,
          )}
          {adjectives.map((star) =>
            star.name ? (
              <StarLine
                brightness={star.brightness ?? brightnessOf(star.name, palace.earthly_branch)}
                hua={huaOf(star.name, palace.earthly_branch)}
                kind="adjective"
                key={`adj-${star.name}`}
                name={star.name}
              />
            ) : null,
          )}
        </div>
      ) : null}
      <div className={styles.foot}>
        {palace.label ? <span className={styles.palaceName}>{palace.label}</span> : null}
        {decade ? <span className={styles.decade}>{decade}</span> : null}
      </div>
      {ganzhi ? <span className={styles.ganzhi}>{ganzhi}</span> : null}
      <GodFoot density={density} palace={palace} />
    </>
  );
}

function SemanticTable({ view }: { view: ZiweiChartViewModel }) {
  return (
    <table className={`${styles.table} ${styles.srOnly}`} aria-label="十二宫星曜">
      <thead>
        <tr>
          <th>宫</th>
          <th>星曜</th>
          <th>干支</th>
          <th>大限</th>
        </tr>
      </thead>
      <tbody>
        {view.palaces.map((palace) => (
          <tr key={palace.palace_id}>
            <td>{palace.label}</td>
            <td>{palace.major_stars.join(" ")}</td>
            <td>{ganzhiText(palace) ?? ""}</td>
            <td>{decadeText(palace.decadal) ?? ""}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function ZiweiPalaceBoard({
  view,
  mode = "ready",
  layout,
  offer = null,
  s4Phase = "entry",
  showInterpretiveSections = true,
}: ZiweiPalaceBoardProps) {
  const resolvedLayout = useResolvedLayout(layout);
  const structural = mode !== "ready" || !view;
  const [selected, setSelected] = useState<string | null>(null);
  const [density, setDensity] = useState<GodDensity>("compact");
  const [detailBranch, setDetailBranch] = useState<string | null>(null);
  const buttonRefs = useRef<Partial<Record<string, HTMLButtonElement | null>>>({});
  const cardRefs = useRef<Partial<Record<string, HTMLLIElement | null>>>({});

  const palaceMap = useMemo(() => {
    const map = new Map<string, Palace>();
    for (const item of view?.palaces ?? []) {
      if (item.earthly_branch) map.set(item.earthly_branch, item);
    }
    return map;
  }, [view]);

  const lifePalace = view?.palaces.find((item) => item.palace_id === view.life_palace_id);
  const bodyPalace = view?.palaces.find((item) => item.palace_id === view.body_palace_id);
  const lifeBranch = lifePalace?.earthly_branch ?? null;
  const bodyBranch = bodyPalace?.earthly_branch ?? null;

  const brightnessOf = (name: string, branch: string): string | null => {
    const hit = view?.core_facts?.star_facts?.find(
      (fact) => fact.name === name && fact.palace_branch === branch && fact.brightness,
    );
    return hit?.brightness ?? null;
  };

  const huaOf = (name: string, branch: string): string | null => {
    const hit = view?.core_facts?.transformations?.find(
      (item) => item.star === name && item.palace_branch === branch,
    );
    return hit ? huaMark(hit.transformation) : null;
  };

  function moveTo(branch: string) {
    setSelected(branch);
    buttonRefs.current[branch]?.focus();
  }

  function onPalaceKey(event: KeyboardEvent<HTMLButtonElement>, branch: string) {
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      moveTo(stepBranch(branch, 1));
      return;
    }
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      moveTo(stepBranch(branch, -1));
      return;
    }
    if (event.key === "Home" && lifeBranch) {
      event.preventDefault();
      moveTo(lifeBranch);
      return;
    }
    if (event.key === "End" && bodyBranch) {
      event.preventDefault();
      moveTo(bodyBranch);
      return;
    }
    if (event.key === "Enter" && !structural) {
      event.preventDefault();
      setSelected(branch);
      setDetailBranch(branch);
    }
  }

  function onBoardKey(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "Escape" || detailBranch) return;
    event.preventDefault();
    setSelected(null);
  }

  function palaceName(palace: Palace | undefined, branch: string): string {
    if (!palace) return branch;
    const marks = [
      palace.palace_id === view?.life_palace_id ? "命" : null,
      palace.palace_id === view?.body_palace_id ? "身" : null,
    ].filter(Boolean);
    return [branch, palace.label, ...marks].filter(Boolean).join(" ");
  }

  function renderMarks(palace: Palace | undefined): ReactNode {
    if (!palace || !view) return null;
    const isLife = palace.palace_id === view.life_palace_id;
    const isBody = palace.palace_id === view.body_palace_id;
    if (!isLife && !isBody) return null;
    return (
      <div className={styles.marks}>
        {isLife ? <span className={styles.mark}>命</span> : null}
        {isBody ? <span className={styles.mark}>身</span> : null}
      </div>
    );
  }

  function openDetail(branch: string) {
    setSelected(branch);
    setDetailBranch(branch);
  }

  function selectListBranch(branch: string) {
    setSelected(branch);
    cardRefs.current[branch]?.scrollIntoView({ block: "nearest" });
  }

  const detailPalace = !structural && detailBranch ? palaceMap.get(detailBranch) ?? null : null;
  const detailDrawer =
    detailPalace && view ? (
      <ZiweiPalaceDetailDrawer
        brightnessOf={brightnessOf}
        huaOf={huaOf}
        isBody={detailPalace.palace_id === view.body_palace_id}
        isLife={detailPalace.palace_id === view.life_palace_id}
        onClose={() => setDetailBranch(null)}
        palace={detailPalace}
      />
    ) : null;

  const listOrder = ringFrom(lifeBranch ?? "子");
  const caliber =
    !structural ? <ZiweiCaliberBar chineseDate={view?.core_facts?.chinese_date ?? null} /> : null;
  const densitySwitch =
    !structural && boardHasGods(view?.palaces) ? <DensitySwitch density={density} onChange={setDensity} /> : null;

  if (resolvedLayout === "list") {
    return (
      <div className={styles.board} data-layout="list" data-mode={mode} onKeyDown={onBoardKey}>
        {caliber}
        {densitySwitch}
        <nav aria-label="宫位缩略" className={styles.thumbs} data-columns="3">
          {VISUAL_BRANCHES.map((branch) => {
            const palace = palaceMap.get(branch);
            const isLife = Boolean(palace && view && palace.palace_id === view.life_palace_id);
            const isBody = Boolean(palace && view && palace.palace_id === view.body_palace_id);
            const label = (palace?.label ?? branch).slice(0, 1);
            if (structural) {
              return (
                <span
                  className={styles.thumb}
                  data-body={isBody ? "true" : undefined}
                  data-branch={branch}
                  data-life={isLife ? "true" : undefined}
                  key={branch}
                >
                  {label}
                </span>
              );
            }
            return (
              <button
                aria-controls={`ziwei-list-${branch}`}
                aria-label={palaceName(palace, branch)}
                className={styles.thumb}
                data-body={isBody ? "true" : undefined}
                data-branch={branch}
                data-highlight={highlightFor(branch, selected)}
                data-life={isLife ? "true" : undefined}
                key={branch}
                type="button"
                onClick={() => selectListBranch(branch)}
              >
                {label}
              </button>
            );
          })}
        </nav>
        <ul aria-label="十二宫列表" className={styles.list}>
          <li className={styles.card} data-slot="center">
            <CenterFacts emptyLabel={!structural} view={structural ? undefined : view} />
          </li>
          {listOrder.map((branch) => {
            const palace = palaceMap.get(branch);
            return (
              <li
                className={styles.card}
                data-branch={branch}
                data-highlight={highlightFor(branch, selected)}
                id={`ziwei-list-${branch}`}
                key={branch}
                ref={(node) => {
                  cardRefs.current[branch] = node;
                }}
                tabIndex={structural ? undefined : 0}
                onClick={structural ? undefined : () => setSelected(branch)}
                onFocus={structural ? undefined : () => setSelected(branch)}
              >
                {renderMarks(palace)}
                {palace && !structural ? (
                  <PalaceBody brightnessOf={brightnessOf} density={density} huaOf={huaOf} palace={palace} />
                ) : null}
                {palace && !structural ? (
                  <button className={styles.detailTrigger} type="button" onClick={() => openDetail(branch)}>
                    详情
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
        {view && !structural ? <SemanticTable view={view} /> : null}
        {!structural ? (
          <ZiweiMajorLimitTrack
            limits={view?.core_facts?.major_limits ?? null}
            onSelectLimit={(branch) => setSelected((current) => (current === branch ? null : branch))}
            selectedBranch={selected}
            sequence={view?.core_facts?.major_limit_sequence ?? null}
          />
        ) : null}
        {!structural ? (
          <ZiweiTransformationTable
            items={view?.core_facts?.transformations ?? null}
            onSelectStar={(branch) => setSelected((current) => (current === branch ? null : branch))}
            selectedBranch={selected}
          />
        ) : null}
        {!structural ? (
          <ZiweiStarFactList
            items={view?.core_facts?.star_facts ?? null}
            onSelectStar={(branch) => setSelected((current) => (current === branch ? null : branch))}
            selectedBranch={selected}
          />
        ) : null}
        {!structural && showInterpretiveSections ? (
          <ZiweiSourcePatternDrawer
            items={view?.core_facts?.source_conditioned_patterns}
            onSelectPattern={(branch) => setSelected((current) => (current === branch ? null : branch))}
            palaces={view?.palaces}
            selectedBranch={selected}
          />
        ) : null}
        {view && !structural && showInterpretiveSections ? (
          <ZiweiFreeSummary offer={offer} s4Phase={s4Phase} view={view} />
        ) : null}
        {detailDrawer}
      </div>
    );
  }

  return (
    <div className={styles.board} data-layout="ring" data-mode={mode} onKeyDown={onBoardKey}>
      {caliber}
      {densitySwitch}
      <div
        aria-busy={mode === "loading" ? true : undefined}
        aria-label="十二宫环盘"
        className={styles.ring}
        role="grid"
      >
        {VISUAL_BRANCHES.map((branch) => {
          const palace = palaceMap.get(branch);
          const isLife = Boolean(palace && view && palace.palace_id === view.life_palace_id);
          const isBody = Boolean(palace && view && palace.palace_id === view.body_palace_id);
          if (structural) {
            return (
              <GridOwnedCell key={branch}>
                <div className={styles.cell} data-branch={branch} data-empty="true" />
              </GridOwnedCell>
            );
          }
          return (
            <GridOwnedCell key={branch}>
              <button
                aria-label={palaceName(palace, branch)}
                className={styles.cell}
                data-body={isBody ? "true" : undefined}
                data-branch={branch}
                data-highlight={highlightFor(branch, selected)}
                data-life={isLife ? "true" : undefined}
                onClick={() => setSelected((current) => (current === branch ? null : branch))}
                onKeyDown={(event) => onPalaceKey(event, branch)}
                ref={(node) => {
                  buttonRefs.current[branch] = node;
                }}
                tabIndex={selected ? (selected === branch ? 0 : -1) : isLife || (!lifeBranch && branch === "子") ? 0 : -1}
                type="button"
              >
                {renderMarks(palace)}
                {palace ? <PalaceBody brightnessOf={brightnessOf} density={density} huaOf={huaOf} palace={palace} /> : null}
              </button>
            </GridOwnedCell>
          );
        })}
        <GridOwnedCell>
          <CenterFacts emptyLabel={!structural} view={structural ? undefined : view} />
        </GridOwnedCell>
      </div>
      {view && !structural ? <SemanticTable view={view} /> : null}
      {!structural ? (
        <ZiweiMajorLimitTrack
          limits={view?.core_facts?.major_limits ?? null}
          onSelectLimit={(branch) => setSelected((current) => (current === branch ? null : branch))}
          selectedBranch={selected}
          sequence={view?.core_facts?.major_limit_sequence ?? null}
        />
      ) : null}
      {!structural ? (
        <ZiweiTransformationTable
          items={view?.core_facts?.transformations ?? null}
          onSelectStar={(branch) => setSelected((current) => (current === branch ? null : branch))}
          selectedBranch={selected}
        />
      ) : null}
      {!structural ? (
        <ZiweiStarFactList
          items={view?.core_facts?.star_facts ?? null}
          onSelectStar={(branch) => setSelected((current) => (current === branch ? null : branch))}
          selectedBranch={selected}
        />
      ) : null}
      {!structural && showInterpretiveSections ? (
        <ZiweiSourcePatternDrawer
          items={view?.core_facts?.source_conditioned_patterns}
          onSelectPattern={(branch) => setSelected((current) => (current === branch ? null : branch))}
          palaces={view?.palaces}
          selectedBranch={selected}
        />
      ) : null}
      {view && !structural && showInterpretiveSections ? (
        <ZiweiFreeSummary offer={offer} s4Phase={s4Phase} view={view} />
      ) : null}
      {detailDrawer}
    </div>
  );
}
