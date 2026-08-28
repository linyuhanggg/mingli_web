"use client";

import Link from "next/link";
import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import type {
  ChartWorkspaceView,
  WorkspaceFocusDetail,
  WorkspaceLayer,
  WorkspaceLayerId,
} from "@/lib/chart-workspace";
import type { TimeLayerEntitlementResponse } from "@/lib/api/contracts";
import type { ZiweiChartViewModel } from "@/view-models/registry";

import {
  ZiweiFreeSummary,
  type ZiweiS4Offer,
  type ZiweiS4Phase,
} from "./ziwei-free-summary";
import { ZiweiCaliberBar } from "./ziwei-caliber-bar";
import { ZiweiPalaceDetailDrawer } from "./ziwei-palace-detail-drawer";
import styles from "./ziwei-palace-board.module.css";
import { ZiweiMajorLimitTrack } from "./ziwei-major-limit-track";
import { ZiweiSourcePatternDrawer } from "./ziwei-source-pattern-drawer";
import { ZiweiStarFactList } from "./ziwei-star-fact-list";
import { ZiweiTransformationTable } from "./ziwei-transformation-table";

const BRANCHES = [
  "子",
  "丑",
  "寅",
  "卯",
  "辰",
  "巳",
  "午",
  "未",
  "申",
  "酉",
  "戌",
  "亥",
] as const;
const VISUAL_BRANCHES = [
  "巳",
  "午",
  "未",
  "申",
  "辰",
  "酉",
  "卯",
  "戌",
  "寅",
  "丑",
  "子",
  "亥",
] as const;

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
    if (
      typeof window === "undefined" ||
      typeof window.matchMedia !== "function"
    )
      return;
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
  selectedBranch?: string | null;
  onSelectedBranchChange?: (branch: string | null) => void;
  onActiveBranchChange?: (branch: string | null) => void;
  showLocator?: boolean;
  showSupportingSections?: boolean;
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

const GOD_KEYS = [
  "changsheng12",
  "boshi12",
  "jiangqian12",
  "suiqian12",
] as const;
type GodKey = (typeof GOD_KEYS)[number];
type GodDensity = "compact" | "full";

function readGod(value: string | null | undefined): string | null {
  const text = value?.trim();
  return text ? text : null;
}

function palaceGods(
  palace: Palace,
  density: GodDensity,
): Array<{ key: GodKey; label: string }> {
  const keys: readonly GodKey[] =
    density === "compact" ? ["changsheng12"] : GOD_KEYS;
  return keys.flatMap((key) => {
    const label = readGod(palace[key]);
    return label ? [{ key, label }] : [];
  });
}

function boardHasGods(palaces: readonly Palace[] | undefined): boolean {
  return Boolean(
    palaces?.some((item) => GOD_KEYS.some((key) => readGod(item[key]))),
  );
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

function ganzhiText(
  palace: Pick<Palace, "heavenly_stem" | "earthly_branch"> | undefined,
): string | null {
  if (!palace?.heavenly_stem || !palace.earthly_branch) return null;
  return `${palace.heavenly_stem}${palace.earthly_branch}`;
}

function huaMark(value: string): string | null {
  return (
    HUA_MARK[value] ??
    (/[禄权科忌]/.test(value) ? value.replace("化", "") : null)
  );
}

function directionMark(value: string | null | undefined): string | null {
  if (!value) return null;
  return (
    DIRECTION_MARK[value] ?? (/[\u3400-\u9fff]/u.test(value) ? value : null)
  );
}

function ringFrom(branch: string): readonly string[] {
  const index = branchIndex(branch);
  const start = index >= 0 ? index : 0;
  return BRANCHES.map(
    (_, offset) => BRANCHES[(start + offset) % BRANCHES.length],
  );
}

function highlightFor(
  branch: string,
  selected: string | null,
): "primary" | "related" | undefined {
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
  const hasAny = Boolean(
    soul || body || wuXing || startAge != null || direction,
  );

  return (
    <div
      className={styles.center}
      data-slot="center"
      role="group"
      aria-label="中宫"
    >
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
      {startAge != null ? (
        <p className={styles.centerLine}>{startAge}</p>
      ) : null}
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
      {brightness ? (
        <sup className={styles.brightness}>{brightness}</sup>
      ) : null}
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
                brightness={
                  star.brightness ??
                  brightnessOf(star.name, palace.earthly_branch)
                }
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
                brightness={
                  star.brightness ??
                  brightnessOf(star.name, palace.earthly_branch)
                }
                hua={huaOf(star.name, palace.earthly_branch)}
                kind="adjective"
                key={`adj-${star.name}`}
                name={star.name}
              />
            ) : null,
          )}
        </div>
      ) : (
        <span className={styles.missingPalace}>无主星</span>
      )}
      <div className={styles.foot}>
        {palace.label ? (
          <span className={styles.palaceName}>{palace.label}</span>
        ) : null}
        {decade ? <span className={styles.decade}>{decade}</span> : null}
      </div>
      {ganzhi ? <span className={styles.ganzhi}>{ganzhi}</span> : null}
      <GodFoot density={density} palace={palace} />
    </>
  );
}

function SemanticTable({ view }: { view: ZiweiChartViewModel }) {
  return (
    <table
      className={`${styles.table} ${styles.srOnly}`}
      aria-label="十二宫星曜"
    >
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

function locatorPalaceName(palace: Palace, view: ZiweiChartViewModel): string {
  const marks = [
    palace.palace_id === view.life_palace_id ? "命" : null,
    palace.palace_id === view.body_palace_id ? "身" : null,
  ].filter(Boolean);
  return [palace.earthly_branch, palace.label, ...marks]
    .filter(Boolean)
    .join(" ");
}

function ZiweiPalaceLocator({
  view,
  selectedBranch,
  onSelect,
}: Readonly<{
  view: ZiweiChartViewModel;
  selectedBranch: string | null;
  onSelect: (branch: string) => void;
}>) {
  const refs = useRef<Partial<Record<string, HTMLButtonElement | null>>>({});
  const palaceMap = useMemo(
    () =>
      new Map(view.palaces.map((palace) => [palace.earthly_branch, palace])),
    [view.palaces],
  );
  const lifePalace = view.palaces.find(
    (palace) => palace.palace_id === view.life_palace_id,
  );
  const orderedBranches = ringFrom(lifePalace?.earthly_branch ?? "子");
  const locatorReady =
    palaceMap.size === BRANCHES.length &&
    orderedBranches.every((branch) => {
      const palace = palaceMap.get(branch);
      return Boolean(palace?.label.trim() && ganzhiText(palace));
    });
  const activeBranch =
    selectedBranch && palaceMap.has(selectedBranch)
      ? selectedBranch
      : (lifePalace?.earthly_branch ?? orderedBranches[0]);

  if (!locatorReady) return null;

  function moveFocus(branch: string) {
    onSelect(branch);
    const target = refs.current[branch];
    target?.focus();
    if (target && typeof target.scrollIntoView === "function") {
      target.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  }

  function handleKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    branch: string,
  ) {
    const index = orderedBranches.indexOf(branch);
    if (index < 0) return;
    let target: string | null = null;
    if (event.key === "ArrowRight") {
      target = orderedBranches[(index + 1) % orderedBranches.length];
    } else if (event.key === "ArrowLeft") {
      target =
        orderedBranches[
          (index - 1 + orderedBranches.length) % orderedBranches.length
        ];
    } else if (event.key === "Home") {
      target = orderedBranches[0];
    } else if (event.key === "End") {
      target = orderedBranches[orderedBranches.length - 1];
    }
    if (!target) return;
    event.preventDefault();
    moveFocus(target);
  }

  return (
    <nav
      aria-label="十二宫定位"
      className={styles.locator}
      data-testid="ziwei-palace-locator"
    >
      <div className={styles.locatorHeading}>
        <span>十二宫定位</span>
        <small>左右方向键移动，选择后联动盘面与阅读</small>
      </div>
      <div className={styles.locatorTrack}>
        {orderedBranches.map((branch) => {
          const palace = palaceMap.get(branch);
          if (!palace) return null;
          const active = activeBranch === branch;
          return (
            <button
              aria-current={active ? "true" : undefined}
              aria-label={`${locatorPalaceName(palace, view)}，定位至该宫`}
              className={styles.locatorButton}
              data-branch={branch}
              key={branch}
              onClick={() => onSelect(branch)}
              onKeyDown={(event) => handleKeyDown(event, branch)}
              ref={(node) => {
                refs.current[branch] = node;
              }}
              tabIndex={active ? 0 : -1}
              type="button"
            >
              <span>{palace.label}</span>
              <span className={styles.locatorBranch}>{ganzhiText(palace)}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

export function ZiweiPalaceBoard({
  view,
  mode = "ready",
  layout,
  offer = null,
  s4Phase = "entry",
  showInterpretiveSections = true,
  selectedBranch,
  onSelectedBranchChange,
  onActiveBranchChange,
  showLocator = true,
  showSupportingSections = true,
}: ZiweiPalaceBoardProps) {
  const resolvedLayout = useResolvedLayout(layout);
  const structural = mode !== "ready" || !view;
  const [internalSelected, setInternalSelected] = useState<string | null>(null);
  const selected =
    selectedBranch === undefined ? internalSelected : selectedBranch;
  const [previewedBranch, setPreviewedBranch] = useState<string | null>(null);
  const [density, setDensity] = useState<GodDensity>("compact");
  const [detailBranch, setDetailBranch] = useState<string | null>(null);
  const [detailReturnFocusTo, setDetailReturnFocusTo] =
    useState<HTMLElement | null>(null);
  const buttonRefs = useRef<Partial<Record<string, HTMLButtonElement | null>>>(
    {},
  );
  const cardRefs = useRef<Partial<Record<string, HTMLLIElement | null>>>({});

  function updateSelected(
    next: string | null | ((current: string | null) => string | null),
  ) {
    const resolved = typeof next === "function" ? next(selected) : next;
    if (selectedBranch === undefined) setInternalSelected(resolved);
    onSelectedBranchChange?.(resolved);
  }

  const palaceMap = useMemo(() => {
    const map = new Map<string, Palace>();
    for (const item of view?.palaces ?? []) {
      if (item.earthly_branch) map.set(item.earthly_branch, item);
    }
    return map;
  }, [view]);

  const lifePalace = view?.palaces.find(
    (item) => item.palace_id === view.life_palace_id,
  );
  const bodyPalace = view?.palaces.find(
    (item) => item.palace_id === view.body_palace_id,
  );
  const lifeBranch = lifePalace?.earthly_branch ?? null;
  const bodyBranch = bodyPalace?.earthly_branch ?? null;

  const brightnessOf = (name: string, branch: string): string | null => {
    const hit = view?.core_facts?.star_facts?.find(
      (fact) => fact.name === name && fact.palace_branch === branch,
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
    updateSelected(branch);
    buttonRefs.current[branch]?.focus();
  }

  function onPalaceKey(
    event: KeyboardEvent<HTMLButtonElement>,
    branch: string,
  ) {
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
      setDetailReturnFocusTo(event.currentTarget);
      setPreviewedBranch(null);
      updateSelected(branch);
      setDetailBranch(branch);
    }
  }

  function onBoardKey(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "Escape" || detailBranch) return;
    event.preventDefault();
    setPreviewedBranch(null);
    updateSelected(null);
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

  function openDetail(branch: string, trigger: HTMLElement) {
    setDetailReturnFocusTo(trigger);
    updateSelected(branch);
    setDetailBranch(branch);
  }

  function closeDetail() {
    const returnTarget = detailReturnFocusTo;
    setDetailBranch(null);
    setDetailReturnFocusTo(null);
    queueMicrotask(() => returnTarget?.focus());
  }

  function toggleLockedBranch(branch: string) {
    setPreviewedBranch(null);
    updateSelected((current) => (current === branch ? null : branch));
  }

  function selectListBranch(branch: string) {
    updateSelected(branch);
    cardRefs.current[branch]?.scrollIntoView({ block: "nearest" });
  }

  const detailPalace =
    !structural && detailBranch ? (palaceMap.get(detailBranch) ?? null) : null;
  const highlightedBranch =
    resolvedLayout === "ring" ? (previewedBranch ?? selected) : selected;

  useEffect(() => {
    onActiveBranchChange?.(highlightedBranch);
  }, [highlightedBranch, onActiveBranchChange]);
  const detailDrawer =
    detailPalace && view ? (
      <ZiweiPalaceDetailDrawer
        brightnessOf={brightnessOf}
        huaOf={huaOf}
        isBody={detailPalace.palace_id === view.body_palace_id}
        isLife={detailPalace.palace_id === view.life_palace_id}
        onClose={closeDetail}
        palace={detailPalace}
        returnFocusTo={detailReturnFocusTo}
      />
    ) : null;

  const listOrder = ringFrom(lifeBranch ?? "子");
  const caliber = !structural ? (
    <ZiweiCaliberBar chineseDate={view?.core_facts?.chinese_date ?? null} />
  ) : null;
  const densitySwitch =
    !structural && boardHasGods(view?.palaces) ? (
      <DensitySwitch density={density} onChange={setDensity} />
    ) : null;
  const locator =
    view && !structural && showLocator ? (
      <ZiweiPalaceLocator
        onSelect={updateSelected}
        selectedBranch={selected}
        view={view}
      />
    ) : null;

  if (resolvedLayout === "list") {
    return (
      <div
        className={styles.board}
        data-layout="list"
        data-mode={mode}
        onKeyDown={onBoardKey}
      >
        {locator}
        {caliber}
        {densitySwitch}
        <nav aria-label="宫位缩略" className={styles.thumbs} data-columns="3">
          {VISUAL_BRANCHES.map((branch) => {
            const palace = palaceMap.get(branch);
            const isLife = Boolean(
              palace && view && palace.palace_id === view.life_palace_id,
            );
            const isBody = Boolean(
              palace && view && palace.palace_id === view.body_palace_id,
            );
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
                data-highlight={highlightFor(branch, highlightedBranch)}
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
            <CenterFacts
              emptyLabel={!structural}
              view={structural ? undefined : view}
            />
          </li>
          {listOrder.map((branch) => {
            const palace = palaceMap.get(branch);
            return (
              <li
                className={styles.card}
                data-branch={branch}
                data-highlight={highlightFor(branch, highlightedBranch)}
                id={`ziwei-list-${branch}`}
                key={branch}
                ref={(node) => {
                  cardRefs.current[branch] = node;
                }}
                tabIndex={structural ? undefined : 0}
                onClick={structural ? undefined : () => updateSelected(branch)}
                onFocus={structural ? undefined : () => updateSelected(branch)}
              >
                {renderMarks(palace)}
                {palace && !structural ? (
                  <PalaceBody
                    brightnessOf={brightnessOf}
                    density={density}
                    huaOf={huaOf}
                    palace={palace}
                  />
                ) : !structural ? (
                  <span className={styles.missingPalace}>
                    {branch}宫 · 未返回
                  </span>
                ) : null}
                {palace && !structural ? (
                  <button
                    className={styles.detailTrigger}
                    type="button"
                    onClick={(event) => openDetail(branch, event.currentTarget)}
                  >
                    详情
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
        {view && !structural ? <SemanticTable view={view} /> : null}
        {!structural && showSupportingSections ? (
          <ZiweiMajorLimitTrack
            limits={view?.core_facts?.major_limits ?? null}
            onSelectLimit={(branch) =>
              updateSelected((current) => (current === branch ? null : branch))
            }
            selectedBranch={highlightedBranch}
            sequence={view?.core_facts?.major_limit_sequence ?? null}
          />
        ) : null}
        {!structural && showSupportingSections ? (
          <ZiweiTransformationTable
            items={view?.core_facts?.transformations ?? null}
            onSelectStar={(branch) =>
              updateSelected((current) => (current === branch ? null : branch))
            }
            selectedBranch={highlightedBranch}
          />
        ) : null}
        {!structural && showSupportingSections ? (
          <ZiweiStarFactList
            items={view?.core_facts?.star_facts ?? null}
            onSelectStar={(branch) =>
              updateSelected((current) => (current === branch ? null : branch))
            }
            selectedBranch={highlightedBranch}
          />
        ) : null}
        {!structural && showSupportingSections && showInterpretiveSections ? (
          <ZiweiSourcePatternDrawer
            items={view?.core_facts?.source_conditioned_patterns}
            onSelectPattern={(branch) =>
              updateSelected((current) => (current === branch ? null : branch))
            }
            palaces={view?.palaces}
            selectedBranch={highlightedBranch}
          />
        ) : null}
        {view &&
        !structural &&
        showSupportingSections &&
        showInterpretiveSections ? (
          <ZiweiFreeSummary offer={offer} s4Phase={s4Phase} view={view} />
        ) : null}
        {detailDrawer}
      </div>
    );
  }

  return (
    <div
      className={styles.board}
      data-layout="ring"
      data-mode={mode}
      onKeyDown={onBoardKey}
    >
      {locator}
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
          const isLife = Boolean(
            palace && view && palace.palace_id === view.life_palace_id,
          );
          const isBody = Boolean(
            palace && view && palace.palace_id === view.body_palace_id,
          );
          if (structural) {
            return (
              <GridOwnedCell key={branch}>
                <div
                  className={styles.cell}
                  data-branch={branch}
                  data-empty="true"
                />
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
                data-highlight={highlightFor(branch, highlightedBranch)}
                data-life={isLife ? "true" : undefined}
                id={`ziwei-ring-${branch}`}
                onBlur={() =>
                  setPreviewedBranch((current) =>
                    current === branch ? null : current,
                  )
                }
                onClick={() => toggleLockedBranch(branch)}
                onFocus={() => setPreviewedBranch(branch)}
                onMouseEnter={() => setPreviewedBranch(branch)}
                onMouseLeave={() =>
                  setPreviewedBranch((current) =>
                    current === branch ? null : current,
                  )
                }
                onKeyDown={(event) => onPalaceKey(event, branch)}
                ref={(node) => {
                  buttonRefs.current[branch] = node;
                }}
                tabIndex={
                  selected
                    ? selected === branch
                      ? 0
                      : -1
                    : isLife || (!lifeBranch && branch === "子")
                      ? 0
                      : -1
                }
                type="button"
              >
                {renderMarks(palace)}
                {palace ? (
                  <PalaceBody
                    brightnessOf={brightnessOf}
                    density={density}
                    huaOf={huaOf}
                    palace={palace}
                  />
                ) : (
                  <span className={styles.missingPalace}>
                    {branch}宫 · 未返回
                  </span>
                )}
              </button>
            </GridOwnedCell>
          );
        })}
        <GridOwnedCell>
          <CenterFacts
            emptyLabel={!structural}
            view={structural ? undefined : view}
          />
        </GridOwnedCell>
      </div>
      {view && !structural ? <SemanticTable view={view} /> : null}
      {!structural && showSupportingSections ? (
        <ZiweiMajorLimitTrack
          limits={view?.core_facts?.major_limits ?? null}
          onSelectLimit={(branch) =>
            updateSelected((current) => (current === branch ? null : branch))
          }
          selectedBranch={highlightedBranch}
          sequence={view?.core_facts?.major_limit_sequence ?? null}
        />
      ) : null}
      {!structural && showSupportingSections ? (
        <ZiweiTransformationTable
          items={view?.core_facts?.transformations ?? null}
          onSelectStar={(branch) =>
            updateSelected((current) => (current === branch ? null : branch))
          }
          selectedBranch={highlightedBranch}
        />
      ) : null}
      {!structural && showSupportingSections ? (
        <ZiweiStarFactList
          items={view?.core_facts?.star_facts ?? null}
          onSelectStar={(branch) =>
            updateSelected((current) => (current === branch ? null : branch))
          }
          selectedBranch={highlightedBranch}
        />
      ) : null}
      {!structural && showSupportingSections && showInterpretiveSections ? (
        <ZiweiSourcePatternDrawer
          items={view?.core_facts?.source_conditioned_patterns}
          onSelectPattern={(branch) =>
            updateSelected((current) => (current === branch ? null : branch))
          }
          palaces={view?.palaces}
          selectedBranch={highlightedBranch}
        />
      ) : null}
      {view &&
      !structural &&
      showSupportingSections &&
      showInterpretiveSections ? (
        <ZiweiFreeSummary offer={offer} s4Phase={s4Phase} view={view} />
      ) : null}
      {detailDrawer}
    </div>
  );
}

const WORKSPACE_LAYER_META: Readonly<
  Record<WorkspaceLayerId, { label: string; tier: "free" | "paid" }>
> = {
  natal: { label: "原局", tier: "free" },
  decadal: { label: "大限", tier: "free" },
  yearly: { label: "流年", tier: "free" },
  monthly: { label: "流月", tier: "paid" },
  daily: { label: "流日", tier: "paid" },
  hourly: { label: "流时", tier: "paid" },
};

const WORKSPACE_LAYER_ALIASES: Readonly<Record<string, WorkspaceLayerId>> = {
  life: "natal",
  natal: "natal",
  original: "natal",
  luck_cycles: "decadal",
  major_limit: "decadal",
  major_limits: "decadal",
  decadal: "decadal",
  year: "yearly",
  yearly: "yearly",
  annual: "yearly",
  month: "monthly",
  monthly: "monthly",
  day: "daily",
  daily: "daily",
  hour: "hourly",
  hourly: "hourly",
};

const ZIWEI_ENTITLEMENT_KEYS = [
  "schema_version",
  "capability_id",
  "resolution",
  "free_boundary_layer_id",
  "paid_layer_ids",
  "free_year_set",
  "capability",
  "layers",
] as const;
const ZIWEI_CAPABILITY_KEYS = ["time_layers"] as const;
const ZIWEI_CAPABILITY_LAYER_KEYS = [
  "layer_id",
  "label",
  "available",
  "unavailable_reason",
] as const;
const ZIWEI_ENTITLEMENT_LAYER_KEYS = [
  "layer_id",
  "tier",
  "access",
  "upgrade_cta",
] as const;
const ZIWEI_CAPABILITY_LAYER_IDS = new Set([
  "life",
  "year",
  "month",
  "day",
  "hour",
]);
const ZIWEI_ENTITLEMENT_LAYER_TABLE = [
  { layerId: "life", tier: "free" },
  { layerId: "major_limits", tier: "free" },
  { layerId: "year", tier: "free" },
  { layerId: "month", tier: "paid" },
  { layerId: "day", tier: "paid" },
  { layerId: "hour", tier: "paid" },
] as const;
const ZIWEI_ENTITLEMENT_RESOLUTIONS = new Set([
  "granted",
  "denied",
  "unknown",
  "unauthenticated",
  "request_failed",
]);
const ZIWEI_ENTITLEMENT_ACCESS = new Set([
  "readable",
  "locked_paywall",
  "fail_closed_unknown",
  "unavailable",
]);
const ZIWEI_PAID_ACCESS_BY_RESOLUTION: Readonly<
  Record<
    TimeLayerEntitlementResponse["resolution"],
    ReadonlySet<TimeLayerEntitlementResponse["layers"][number]["access"]>
  >
> = {
  granted: new Set(["readable", "unavailable"]),
  denied: new Set(["locked_paywall", "unavailable"]),
  unknown: new Set(["fail_closed_unknown", "unavailable"]),
  unauthenticated: new Set(["fail_closed_unknown", "unavailable"]),
  request_failed: new Set(["fail_closed_unknown", "unavailable"]),
};

type ZiweiEntitlementLayer = TimeLayerEntitlementResponse["layers"][number];
type ZiweiCapabilityLayer =
  TimeLayerEntitlementResponse["capability"]["time_layers"][number];

type ParsedZiweiEntitlement = {
  layers: ReadonlyMap<string, ZiweiEntitlementLayer>;
  capability: ReadonlyMap<string, ZiweiCapabilityLayer>;
  freeYears: ReadonlySet<number>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(
  value: Record<string, unknown>,
  expected: readonly string[],
): boolean {
  const keys = Object.keys(value);
  return (
    keys.length === expected.length &&
    expected.every((key) => Object.prototype.hasOwnProperty.call(value, key))
  );
}

function isNonEmptyText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

type ZiweiTemporalStar = {
  name: string;
  starType: string | null;
  scope: string | null;
  brightness: string | null;
};

type ZiweiTemporalPalace = {
  index: number;
  branch: string;
  label: string;
  stars: readonly ZiweiTemporalStar[];
};

type ZiweiTemporalTransformation = {
  star: string;
  transformation: string;
  palace: string;
  palace_branch: string;
  scope: string;
};

type ZiweiTemporalLayerId = "yearly" | "monthly";

type ZiweiTemporalSegmentOption = {
  id: string;
  label: string;
  startInclusive: string;
  endExclusive: string;
  view: ZiweiChartViewModel;
};

type ZiweiTemporalOption = {
  id: string;
  label: string;
  rangeLabel: string;
  segments: readonly ZiweiTemporalSegmentOption[];
  initialSegmentId: string;
};

type ZiweiTemporalSelection = {
  options: readonly ZiweiTemporalOption[];
  initialId: string;
};

const EMPTY_FREE_YEAR_SET: ReadonlySet<number> = new Set();

function isEarthlyBranch(value: unknown): value is (typeof BRANCHES)[number] {
  return (
    typeof value === "string" &&
    BRANCHES.includes(value as (typeof BRANCHES)[number])
  );
}

function optionalText(value: unknown): string | null | undefined {
  if (value === undefined || value === null) return null;
  return isNonEmptyText(value) ? value.trim() : undefined;
}

function parseTemporalStar(value: unknown): ZiweiTemporalStar | null {
  if (!isRecord(value) || !isNonEmptyText(value.name)) return null;
  const starTypeField = optionalText(value.star_type);
  const typeField = optionalText(value.type);
  if (
    starTypeField === undefined ||
    typeField === undefined ||
    (starTypeField && typeField && starTypeField !== typeField)
  ) {
    return null;
  }
  const starType = starTypeField ?? typeField;
  const scope = optionalText(value.scope);
  const brightness = optionalText(value.brightness);
  if (!starType || !scope || brightness === undefined) {
    return null;
  }
  return {
    name: value.name.trim(),
    starType,
    scope,
    brightness,
  };
}

function parseTemporalPalaces(
  view: ZiweiChartViewModel,
  value: Readonly<Record<string, unknown>>,
): readonly ZiweiTemporalPalace[] | null {
  const rawAssignments = value.palace_assignments;
  if (
    !Array.isArray(rawAssignments) ||
    rawAssignments.length !== BRANCHES.length
  ) {
    return null;
  }
  const baseBranches = new Set(
    view.palaces.map((palace) => palace.earthly_branch),
  );
  if (
    view.palaces.length !== BRANCHES.length ||
    baseBranches.size !== BRANCHES.length ||
    !BRANCHES.every((branch) => baseBranches.has(branch))
  ) {
    return null;
  }

  const indexes = new Set<number>();
  const branches = new Set<string>();
  const assignments: ZiweiTemporalPalace[] = [];
  for (const raw of rawAssignments) {
    if (
      !isRecord(raw) ||
      typeof raw.index !== "number" ||
      !Number.isInteger(raw.index) ||
      raw.index < 0 ||
      raw.index >= BRANCHES.length ||
      indexes.has(raw.index) ||
      !isEarthlyBranch(raw.natal_branch) ||
      branches.has(raw.natal_branch) ||
      !isNonEmptyText(raw.natal_palace) ||
      !isNonEmptyText(raw.temporal_palace) ||
      !Array.isArray(raw.dynamic_stars) ||
      !isRecord(raw.chart_palace) ||
      raw.chart_palace.branch !== raw.natal_branch ||
      raw.chart_palace.name !== raw.natal_palace
    ) {
      return null;
    }
    const stars = raw.dynamic_stars.map(parseTemporalStar);
    if (stars.some((star) => star === null)) return null;
    indexes.add(raw.index);
    branches.add(raw.natal_branch);
    assignments.push({
      index: raw.index,
      branch: raw.natal_branch,
      label: raw.temporal_palace.trim(),
      stars: stars as ZiweiTemporalStar[],
    });
  }
  if (!BRANCHES.every((branch) => branches.has(branch))) return null;
  return assignments;
}

function parseTemporalTransformations(
  value: Readonly<Record<string, unknown>>,
): readonly ZiweiTemporalTransformation[] | null {
  const rawFacts = value.transformation_facts;
  if (rawFacts === undefined || rawFacts === null) return [];
  if (!Array.isArray(rawFacts)) return null;
  const transformations: ZiweiTemporalTransformation[] = [];
  const seen = new Set<string>();
  for (const raw of rawFacts) {
    if (
      !isRecord(raw) ||
      !isNonEmptyText(raw.star) ||
      !isNonEmptyText(raw.transformation) ||
      !isNonEmptyText(raw.palace) ||
      !isEarthlyBranch(raw.palace_branch) ||
      !isNonEmptyText(raw.scope)
    ) {
      return null;
    }
    const item = {
      star: raw.star.trim(),
      transformation: raw.transformation.trim(),
      palace: raw.palace.trim(),
      palace_branch: raw.palace_branch,
      scope: raw.scope.trim(),
    };
    const identity = [
      item.star,
      item.transformation,
      item.palace_branch,
      item.scope,
    ].join("\u0000");
    if (seen.has(identity)) return null;
    seen.add(identity);
    transformations.push(item);
  }
  return transformations;
}

function mergeTemporalStars<T extends { readonly name: string }>(
  natal: readonly T[],
  temporal: readonly T[],
): readonly T[] {
  const temporalNames = new Set(temporal.map((star) => star.name));
  return [
    ...natal.filter((star) => !temporalNames.has(star.name)),
    ...temporal,
  ];
}

function projectTemporalPalaceView(
  view: ZiweiChartViewModel,
  value: Readonly<Record<string, unknown>>,
): ZiweiChartViewModel | null {
  const declaresAssignments = Object.prototype.hasOwnProperty.call(
    value,
    "palace_assignments",
  );
  const assignments = parseTemporalPalaces(view, value);
  const transformations = parseTemporalTransformations(value);
  if (transformations === null || (declaresAssignments && !assignments)) {
    return null;
  }
  if (assignments) {
    const byBranch = new Map(
      assignments.map((assignment) => [assignment.branch, assignment]),
    );
    const lifeAssignments = assignments.filter(
      (assignment) => assignment.label === "命宫",
    );
    if (lifeAssignments.length !== 1) return null;
    const lifePalace = view.palaces.find(
      (palace) => palace.earthly_branch === lifeAssignments[0].branch,
    );
    if (!lifePalace) return null;

    const temporalStarFacts = assignments.flatMap((assignment) =>
      assignment.stars.map((star) => ({
        name: star.name,
        star_type: star.starType,
        scope: star.scope,
        brightness: star.brightness,
        palace: assignment.label,
        palace_branch: assignment.branch,
        palace_index: assignment.index,
      })),
    );
    const temporalStarKeys = new Set(
      temporalStarFacts.map(
        (star) => `${star.palace_branch}\u0000${star.name}`,
      ),
    );

    return {
      ...view,
      life_palace_id: lifePalace.palace_id,
      core_facts: view.core_facts
        ? {
            ...view.core_facts,
            transformations: transformations.length ? transformations : null,
            star_facts: [
              ...temporalStarFacts,
              ...(view.core_facts.star_facts ?? []).filter(
                (star) =>
                  !temporalStarKeys.has(
                    `${star.palace_branch}\u0000${star.name}`,
                  ),
              ),
            ],
          }
        : view.core_facts,
      palaces: view.palaces.map((palace) => {
        const assignment = byBranch.get(palace.earthly_branch);
        if (!assignment) return palace;
        const temporalMajorStars = assignment.stars
          .filter((star) => star.starType === "major")
          .map((star) => star.name);
        const temporalMinorStars = assignment.stars
          .filter((star) => star.starType !== "major")
          .map((star) => ({
            name: star.name,
            star_type: star.starType,
            scope: star.scope,
            brightness: star.brightness,
          }));
        return {
          ...palace,
          label: assignment.label,
          major_stars: mergeTemporalStars(
            palace.major_stars.map((name) => ({ name })),
            temporalMajorStars.map((name) => ({ name })),
          ).map((star) => star.name),
          minor_stars: mergeTemporalStars(
            palace.minor_stars ?? [],
            temporalMinorStars,
          ),
        };
      }),
    };
  }

  if (!isEarthlyBranch(value.life_palace)) return null;
  const lifePalace = view.palaces.find(
    (palace) => palace.earthly_branch === value.life_palace,
  );
  return lifePalace
    ? {
        ...view,
        life_palace_id: lifePalace.palace_id,
        core_facts: view.core_facts
          ? {
              ...view.core_facts,
              transformations: transformations.length ? transformations : null,
            }
          : view.core_facts,
      }
    : null;
}

function activeMajorLimitPalaceView(
  view: ZiweiChartViewModel,
): ZiweiChartViewModel | null {
  const activeMajorLimit = view.core_facts?.active_major_limit;
  if (
    !isRecord(activeMajorLimit) ||
    !Array.isArray(activeMajorLimit.palace_assignments)
  ) {
    return null;
  }
  return projectTemporalPalaceView(view, activeMajorLimit);
}

type ZiweiTemporalTarget =
  { status: "none" } | { status: "valid"; id: string } | { status: "invalid" };

function isIsoCivilDate(value: unknown): value is string {
  if (
    typeof value !== "string" ||
    !/^(18|19|20|21)\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/.test(value)
  ) {
    return false;
  }
  const [year, month, day] = value.split("-").map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return (
    parsed.getUTCFullYear() === year &&
    parsed.getUTCMonth() === month - 1 &&
    parsed.getUTCDate() === day
  );
}

function targetFromRecord(
  value: unknown,
  layerId: ZiweiTemporalLayerId,
): ZiweiTemporalTarget {
  if (!isRecord(value)) return { status: "none" };
  if (layerId === "yearly") {
    if (!Object.prototype.hasOwnProperty.call(value, "target_year")) {
      return { status: "none" };
    }
    return typeof value.target_year === "number" &&
      Number.isInteger(value.target_year) &&
      value.target_year >= 1800 &&
      value.target_year <= 2199
      ? { status: "valid", id: String(value.target_year) }
      : { status: "invalid" };
  }
  if (!Object.prototype.hasOwnProperty.call(value, "target_month")) {
    return { status: "none" };
  }
  if (
    typeof value.target_month === "string" &&
    /^(18|19|20|21)\d{2}-(0[1-9]|1[0-2])$/.test(value.target_month)
  ) {
    return { status: "valid", id: value.target_month };
  }
  if (
    typeof value.target_month === "number" &&
    Number.isInteger(value.target_month) &&
    value.target_month >= 1 &&
    value.target_month <= 12 &&
    typeof value.target_year === "number" &&
    Number.isInteger(value.target_year) &&
    value.target_year >= 1800 &&
    value.target_year <= 2199
  ) {
    return {
      status: "valid",
      id: `${value.target_year}-${String(value.target_month).padStart(2, "0")}`,
    };
  }
  return { status: "invalid" };
}

function dateTargetFromRecord(value: unknown): ZiweiTemporalTarget {
  if (!isRecord(value)) return { status: "none" };
  const dates = new Set<string>();
  for (const key of ["target_date", "requested_target_date"] as const) {
    if (!Object.prototype.hasOwnProperty.call(value, key)) continue;
    if (!isIsoCivilDate(value[key])) return { status: "invalid" };
    dates.add(value[key]);
  }
  if (dates.size > 1) return { status: "invalid" };
  const date = [...dates][0];
  return date ? { status: "valid", id: date } : { status: "none" };
}

function temporalSegmentsForRange(
  view: ZiweiChartViewModel,
  rangeId: string,
  rawSegments: readonly Readonly<Record<string, unknown>>[],
  outputKey: "liu_nian" | "liu_yue",
): ZiweiTemporalSegmentOption[] | null {
  if (!rawSegments.length) return null;
  const identities = new Set<string>();
  const segments: ZiweiTemporalSegmentOption[] = [];
  let previousEnd: string | null = null;
  for (const raw of rawSegments) {
    if (
      !isRecord(raw) ||
      !isIsoCivilDate(raw.start_inclusive) ||
      !isIsoCivilDate(raw.end_exclusive) ||
      raw.start_inclusive >= raw.end_exclusive ||
      (previousEnd !== null && raw.start_inclusive !== previousEnd) ||
      !isRecord(raw[outputKey]) ||
      !Array.isArray(raw[outputKey].palace_assignments)
    ) {
      return null;
    }
    const id = `${rangeId}:${raw.start_inclusive}/${raw.end_exclusive}`;
    const temporalView = projectTemporalPalaceView(view, raw[outputKey]);
    if (identities.has(id) || !temporalView) return null;
    identities.add(id);
    previousEnd = raw.end_exclusive;
    segments.push({
      id,
      label: `${raw.start_inclusive}—${raw.end_exclusive}`,
      startInclusive: raw.start_inclusive,
      endExclusive: raw.end_exclusive,
      view: temporalView,
    });
  }
  return segments;
}

function temporalSelectionForLayer(
  view: ZiweiChartViewModel,
  layerId: ZiweiTemporalLayerId,
  freeYears: ReadonlySet<number> = EMPTY_FREE_YEAR_SET,
): ZiweiTemporalSelection | null {
  const options: ZiweiTemporalOption[] = [];
  const identities = new Set<string>();
  const targetRecords: unknown[] = [view.core_facts?.chart_convention];
  if (layerId === "yearly") {
    const layers = view.core_facts?.annual_layers;
    if (!layers?.length) return null;
    for (const layer of layers) {
      if (
        !Number.isInteger(layer.year) ||
        layer.year < 1800 ||
        layer.year > 2199
      ) {
        return null;
      }
      if (!freeYears.has(layer.year)) continue;
      const id = String(layer.year);
      const segments = temporalSegmentsForRange(
        view,
        id,
        layer.segments,
        "liu_nian",
      );
      if (
        identities.has(id) ||
        !isIsoCivilDate(layer.coverage_start) ||
        !isIsoCivilDate(layer.coverage_end_exclusive) ||
        !segments ||
        segments[0].startInclusive !== layer.coverage_start ||
        segments.at(-1)?.endExclusive !== layer.coverage_end_exclusive
      ) {
        return null;
      }
      identities.add(id);
      options.push({
        id,
        label: id,
        rangeLabel: `${layer.coverage_start}—${layer.coverage_end_exclusive}`,
        segments,
        initialSegmentId: segments[0].id,
      });
      targetRecords.push(layer.liu_nian);
    }
  } else {
    const layers = view.core_facts?.monthly_layers;
    if (!layers?.length) return null;
    for (const layer of layers) {
      if (
        !Number.isInteger(layer.year) ||
        layer.year < 1800 ||
        layer.year > 2199 ||
        !Number.isInteger(layer.month) ||
        layer.month < 1 ||
        layer.month > 12 ||
        !Array.isArray(layer.segments) ||
        !layer.segments.length
      ) {
        return null;
      }
      const id = `${layer.year}-${String(layer.month).padStart(2, "0")}`;
      const segments = temporalSegmentsForRange(
        view,
        id,
        layer.segments,
        "liu_yue",
      );
      if (identities.has(id) || !segments) return null;
      identities.add(id);
      options.push({
        id,
        label: id,
        rangeLabel: `${segments[0].startInclusive}—${segments.at(-1)?.endExclusive}`,
        segments,
        initialSegmentId: segments[0].id,
      });
      targetRecords.push(layer.liu_yue);
    }
  }

  if (!options.length) return null;

  const explicitTargets = new Set<string>();
  const exactDateTargets = new Set<string>();
  for (const record of targetRecords) {
    const target = targetFromRecord(record, layerId);
    if (target.status === "invalid") return null;
    if (target.status === "valid") explicitTargets.add(target.id);
    const exactDateTarget = dateTargetFromRecord(record);
    if (exactDateTarget.status === "invalid") return null;
    if (exactDateTarget.status === "valid") {
      exactDateTargets.add(exactDateTarget.id);
    }
  }
  if (explicitTargets.size > 1 || exactDateTargets.size > 1) return null;
  const explicitTarget = [...explicitTargets][0];
  let initialId = options[0].id;
  if (explicitTarget && identities.has(explicitTarget)) {
    initialId = explicitTarget;
  } else if (
    explicitTarget &&
    !(
      layerId === "yearly" &&
      Number.isInteger(Number(explicitTarget)) &&
      !freeYears.has(Number(explicitTarget))
    )
  ) {
    return null;
  }

  const exactDateTarget = [...exactDateTargets][0];
  if (exactDateTarget) {
    const matching = options.flatMap((option) =>
      option.segments
        .filter((segment) => {
          return (
            segment.startInclusive <= exactDateTarget &&
            exactDateTarget < segment.endExclusive
          );
        })
        .map((segment) => ({ option, segment })),
    );
    if (matching.length === 1) {
      const match = matching[0];
      if (
        explicitTarget &&
        identities.has(explicitTarget) &&
        match.option.id !== explicitTarget
      ) {
        return null;
      }
      match.option.initialSegmentId = match.segment.id;
      if (!explicitTarget || !identities.has(explicitTarget)) {
        initialId = match.option.id;
      }
    } else if (!(
      layerId === "yearly" &&
      isIsoCivilDate(exactDateTarget) &&
      !freeYears.has(Number(exactDateTarget.slice(0, 4)))
    )) {
      return null;
    }
  }
  return {
    options,
    initialId,
  };
}

function temporalPalaceViewForSelection(
  selection: ZiweiTemporalSelection,
  selectedId?: string | null,
  selectedSegmentId?: string | null,
): ZiweiChartViewModel | null {
  const resolvedId =
    selectedId && selection.options.some((option) => option.id === selectedId)
      ? selectedId
      : selection.initialId;
  const option = selection.options.find((item) => item.id === resolvedId);
  if (!option) return null;
  const resolvedSegmentId =
    selectedSegmentId &&
    option.segments.some((segment) => segment.id === selectedSegmentId)
      ? selectedSegmentId
      : option.initialSegmentId;
  return (
    option.segments.find((segment) => segment.id === resolvedSegmentId)?.view ??
    null
  );
}

function resolvedTemporalSegmentId(
  option: ZiweiTemporalOption,
  selectedSegmentId?: string | null,
): string {
  return selectedSegmentId &&
    option.segments.some((segment) => segment.id === selectedSegmentId)
    ? selectedSegmentId
    : option.initialSegmentId;
}

function parseZiweiEntitlement(value: unknown): ParsedZiweiEntitlement | null {
  if (!isRecord(value) || !hasExactKeys(value, ZIWEI_ENTITLEMENT_KEYS)) {
    return null;
  }
  if (
    value.schema_version !== "time-layer-entitlement/v1" ||
    value.capability_id !== "ziwei" ||
    !ZIWEI_ENTITLEMENT_RESOLUTIONS.has(String(value.resolution)) ||
    value.free_boundary_layer_id !== "year" ||
    !Array.isArray(value.paid_layer_ids) ||
    value.paid_layer_ids.length !== 3 ||
    value.paid_layer_ids[0] !== "month" ||
    value.paid_layer_ids[1] !== "day" ||
    value.paid_layer_ids[2] !== "hour" ||
    !Array.isArray(value.free_year_set) ||
    !isRecord(value.capability) ||
    !hasExactKeys(value.capability, ZIWEI_CAPABILITY_KEYS) ||
    !Array.isArray(value.capability.time_layers) ||
    !Array.isArray(value.layers) ||
    value.layers.length !== ZIWEI_ENTITLEMENT_LAYER_TABLE.length
  ) {
    return null;
  }

  const seenYears = new Set<number>();
  for (const year of value.free_year_set) {
    if (
      typeof year !== "number" ||
      !Number.isInteger(year) ||
      year < 1800 ||
      year > 2199 ||
      seenYears.has(year)
    ) {
      return null;
    }
    seenYears.add(year);
  }

  const capability = new Map<string, ZiweiCapabilityLayer>();
  for (const item of value.capability.time_layers) {
    if (
      !isRecord(item) ||
      !hasExactKeys(item, ZIWEI_CAPABILITY_LAYER_KEYS) ||
      !isNonEmptyText(item.layer_id) ||
      !ZIWEI_CAPABILITY_LAYER_IDS.has(item.layer_id) ||
      capability.has(item.layer_id) ||
      !isNonEmptyText(item.label) ||
      typeof item.available !== "boolean" ||
      (item.unavailable_reason !== null &&
        !isNonEmptyText(item.unavailable_reason)) ||
      item.available === (item.unavailable_reason !== null)
    ) {
      return null;
    }
    capability.set(item.layer_id, item as ZiweiCapabilityLayer);
  }

  const resolution =
    value.resolution as TimeLayerEntitlementResponse["resolution"];
  const layers = new Map<string, ZiweiEntitlementLayer>();
  for (const [index, item] of value.layers.entries()) {
    if (!isRecord(item) || !hasExactKeys(item, ZIWEI_ENTITLEMENT_LAYER_KEYS)) {
      return null;
    }
    const expected = ZIWEI_ENTITLEMENT_LAYER_TABLE[index];
    const access = item.access as ZiweiEntitlementLayer["access"];
    const expectedCta =
      expected.tier === "paid" &&
      (access === "locked_paywall" || access === "fail_closed_unknown")
        ? "professional_info"
        : null;
    if (
      item.layer_id !== expected.layerId ||
      item.tier !== expected.tier ||
      !ZIWEI_ENTITLEMENT_ACCESS.has(String(item.access)) ||
      item.upgrade_cta !== expectedCta ||
      (expected.tier === "free" &&
        access !== "readable" &&
        access !== "unavailable") ||
      (expected.tier === "paid" &&
        !ZIWEI_PAID_ACCESS_BY_RESOLUTION[resolution].has(access))
    ) {
      return null;
    }
    layers.set(expected.layerId, item as ZiweiEntitlementLayer);
  }

  for (const [layerId, snapshot] of capability) {
    if (!snapshot.available && layers.get(layerId)?.access === "readable") {
      return null;
    }
  }

  return { capability, freeYears: seenYears, layers };
}

function layerHasFacts(
  view: ZiweiChartViewModel,
  layerId: WorkspaceLayerId,
  entitlement: ParsedZiweiEntitlement | null,
): boolean {
  if (layerId === "natal") return true;
  if (layerId === "decadal") {
    return activeMajorLimitPalaceView(view) !== null;
  }
  if (layerId === "yearly") {
    return (
      temporalSelectionForLayer(
        view,
        layerId,
        entitlement?.freeYears ?? EMPTY_FREE_YEAR_SET,
      ) !== null
    );
  }
  if (layerId === "monthly") {
    return temporalSelectionForLayer(view, layerId) !== null;
  }
  return false;
}

export function projectZiweiWorkspace(
  view: ZiweiChartViewModel,
  timeLayerEntitlement?: TimeLayerEntitlementResponse | null,
): ChartWorkspaceView {
  const entitlement = parseZiweiEntitlement(timeLayerEntitlement);
  const declared = new Map<
    WorkspaceLayerId,
    ZiweiChartViewModel["time_layers"][number]
  >();
  for (const layer of view.time_layers) {
    const layerId =
      WORKSPACE_LAYER_ALIASES[layer.layer_id.trim().toLowerCase()];
    if (layerId && layerId !== "natal" && !declared.has(layerId))
      declared.set(layerId, layer);
  }
  if (!declared.has("decadal") && layerHasFacts(view, "decadal", entitlement)) {
    declared.set("decadal", {
      layer_id: "major_limits",
      label: "大限",
      available: true,
      unavailable_reason: null,
    });
  }
  if (!declared.has("yearly") && layerHasFacts(view, "yearly", entitlement)) {
    declared.set("yearly", {
      layer_id: "year",
      label: "流年",
      available: true,
      unavailable_reason: null,
    });
  }
  if (!declared.has("monthly") && layerHasFacts(view, "monthly", entitlement)) {
    declared.set("monthly", {
      layer_id: "month",
      label: "流月",
      available: true,
      unavailable_reason: null,
    });
  }

  const layers: WorkspaceLayer[] = [
    {
      id: "natal",
      label: WORKSPACE_LAYER_META.natal.label,
      status: "ready",
      summary: view.palaces.length
        ? "十二宫原局"
        : "宫位字段缺失，展示诚实空盘",
    },
  ];

  for (const layerId of [
    "decadal",
    "yearly",
    "monthly",
    "daily",
    "hourly",
  ] as const) {
    const capability = declared.get(layerId);
    const hasFacts = layerHasFacts(view, layerId, entitlement);
    const meta = WORKSPACE_LAYER_META[layerId];
    const entitlementLayerId =
      layerId === "decadal"
        ? "major_limits"
        : layerId === "yearly"
          ? "year"
          : layerId === "monthly"
            ? "month"
            : layerId === "daily"
              ? "day"
              : "hour";
    const entitlementLayer = entitlement?.layers.get(entitlementLayerId);
    const entitlementCapability =
      entitlement?.capability.get(entitlementLayerId);
    let status: WorkspaceLayer["status"];
    let upgradeCta: WorkspaceLayer["upgradeCta"] = null;
    if (!capability || !capability.available) {
      status = "locked-unavailable";
    } else if (!hasFacts) {
      status = meta.tier === "paid" ? "locked-unavailable" : "empty";
    } else if (meta.tier === "paid") {
      if (!entitlement || !entitlementLayer) {
        status = "fail-closed-unknown";
      } else if (!entitlementCapability?.available) {
        status = "locked-unavailable";
      } else if (entitlementLayer.access === "readable") {
        status = "ready";
      } else if (entitlementLayer.access === "locked_paywall") {
        status = "locked-paywall";
        upgradeCta = entitlementLayer.upgrade_cta;
      } else if (entitlementLayer.access === "fail_closed_unknown") {
        status = "fail-closed-unknown";
        upgradeCta = entitlementLayer.upgrade_cta;
      } else {
        status = "locked-unavailable";
      }
    } else {
      status = "ready";
    }
    layers.push({
      id: layerId,
      label: meta.label,
      status,
      summary:
        status === "ready"
          ? `${meta.label}事实已返回`
          : capability?.unavailable_reason?.trim() ||
            entitlementCapability?.unavailable_reason?.trim() ||
            (status === "locked-unavailable" ? "暂不可用" : null),
      upgradeCta,
    });
  }

  return {
    title: "紫微斗数排盘",
    subtitle: "十二宫定位与时间层共用同一组已返回事实",
    layers,
    activeLayerId: "natal",
    cells: [],
    highlights: [],
    basis: [{ key: "schema", label: "事实合同", text: view.schema_version }],
  };
}

function palaceFocusDetail(
  view: ZiweiChartViewModel,
  branch: string | null,
): WorkspaceFocusDetail | null {
  if (!branch) return null;
  const palace = view.palaces.find((item) => item.earthly_branch === branch);
  if (!palace) return null;
  const opposite = view.palaces.find(
    (item) => item.earthly_branch === stepBranch(branch, 6),
  );
  const facts: WorkspaceFocusDetail["facts"] = [];
  if (palace.label.trim()) facts.push({ label: "宫位", text: palace.label });
  const stemBranch = ganzhiText(palace);
  if (stemBranch) facts.push({ label: "干支", text: stemBranch });
  facts.push({
    label: "主星",
    text: palace.major_stars.length ? palace.major_stars.join("、") : "无主星",
  });
  const minorStars = (palace.minor_stars ?? [])
    .map((star) => star.name?.trim())
    .filter((name): name is string => Boolean(name));
  if (minorStars.length)
    facts.push({ label: "辅星", text: minorStars.join("、") });
  const limit = decadeText(palace.decadal);
  if (limit) facts.push({ label: "大限", text: limit });
  if (!palace.major_stars.length && opposite) {
    facts.push({
      label: "对宫参考",
      text: `${opposite.label} · ${
        opposite.major_stars.length ? opposite.major_stars.join("、") : "无主星"
      }`,
    });
  }

  return {
    id: `ziwei-palace-${branch}`,
    title: `${palace.label || branch} · ${branch}`,
    facts,
    limits: [
      "只展示服务端已返回事实，不在浏览器补算星曜或追加推断。",
      ...(palace.major_stars.length
        ? []
        : ["当前宫位无主星；对宫仅作结构参考，不作推断。"]),
    ],
    sources: ["服务端紫微盘面"],
  };
}

function ZiweiTimeLayerLocator({
  activeLayerId,
  idPrefix,
  layers,
  onSelect,
  panelId,
}: Readonly<{
  activeLayerId: WorkspaceLayerId;
  idPrefix: string;
  layers: readonly WorkspaceLayer[];
  onSelect: (layerId: WorkspaceLayerId) => void;
  panelId: string;
}>) {
  const buttonRefs = useRef<
    Partial<Record<WorkspaceLayerId, HTMLButtonElement | null>>
  >({});

  function handleKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    currentLayerId: WorkspaceLayerId,
  ) {
    const interactiveLayers = layers.filter(
      (layer) => layer.status !== "locked-unavailable",
    );
    const currentIndex = interactiveLayers.findIndex(
      (layer) => layer.id === currentLayerId,
    );
    if (currentIndex < 0 || !interactiveLayers.length) return;
    let targetIndex: number | null = null;
    if (event.key === "ArrowRight") {
      targetIndex = (currentIndex + 1) % interactiveLayers.length;
    } else if (event.key === "ArrowLeft") {
      targetIndex =
        (currentIndex - 1 + interactiveLayers.length) %
        interactiveLayers.length;
    } else if (event.key === "Home") {
      targetIndex = 0;
    } else if (event.key === "End") {
      targetIndex = interactiveLayers.length - 1;
    }
    if (targetIndex === null) return;
    event.preventDefault();
    const targetLayer = interactiveLayers[targetIndex];
    buttonRefs.current[targetLayer.id]?.focus();
    onSelect(targetLayer.id);
  }

  return (
    <nav aria-label="时间层定位" className={styles.timeLayerLocator}>
      <div className={styles.timeLayerTrack}>
        {layers.map((layer) => {
          const active = layer.id === activeLayerId;
          const unavailable = layer.status === "locked-unavailable";
          const status =
            layer.status === "ready"
              ? (layer.summary ?? "可查看")
              : layer.status === "empty"
                ? "暂无结构"
                : layer.status === "locked-paywall"
                  ? "PRO · 已锁定"
                  : layer.status === "fail-closed-unknown"
                    ? "权益未确认"
                    : (layer.summary ?? "暂不可用");
          return (
            <button
              key={layer.id}
              aria-controls={panelId}
              aria-current={active ? "true" : undefined}
              aria-disabled={unavailable}
              className={styles.timeLayerButton}
              data-active={active}
              data-status={layer.status}
              disabled={unavailable}
              id={`${idPrefix}-layer-${layer.id}`}
              onClick={unavailable ? undefined : () => onSelect(layer.id)}
              onKeyDown={(event) => handleKeyDown(event, layer.id)}
              ref={(element) => {
                buttonRefs.current[layer.id] = element;
              }}
              tabIndex={!unavailable && active ? 0 : -1}
              type="button"
            >
              <span className={styles.timeLayerLabel}>{layer.label}</span>
              <span className={styles.timeLayerStatus}>{status}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

function TemporalLayerSelector({
  label,
  onSelect,
  options,
  selectedId,
}: Readonly<{
  label: string;
  onSelect: (id: string) => void;
  options: readonly { id: string; label: string }[];
  selectedId: string;
}>) {
  if (options.length < 2) return null;
  return (
    <label className={styles.temporalSelector}>
      <span>{label}</span>
      <select
        value={selectedId}
        onChange={(event) => onSelect(event.currentTarget.value)}
      >
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function ZiweiYearLayer({
  onSelectRange,
  onSelectSegment,
  selectedId,
  selectedSegmentId,
  selection,
}: Readonly<{
  onSelectRange: (id: string) => void;
  onSelectSegment: (id: string) => void;
  selectedId: string;
  selectedSegmentId: string;
  selection: ZiweiTemporalSelection;
}>) {
  const selected =
    selection.options.find((option) => option.id === selectedId) ??
    selection.options[0];
  return (
    <div className={styles.layerFacts}>
      <TemporalLayerSelector
        label="流年年份"
        onSelect={onSelectRange}
        options={selection.options}
        selectedId={selectedId}
      />
      <TemporalLayerSelector
        label="流年分段"
        onSelect={onSelectSegment}
        options={selected.segments}
        selectedId={selectedSegmentId}
      />
      <table className={styles.layerTable}>
        <caption>流年盘面事实</caption>
        <thead>
          <tr>
            <th scope="col">年份</th>
            <th scope="col">覆盖区间</th>
            <th scope="col">分段</th>
          </tr>
        </thead>
        <tbody>
          {selection.options.map((option) => (
            <tr key={option.id}>
              <td>{option.label}</td>
              <td>{option.rangeLabel}</td>
              <td>{option.segments.length}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className={styles.layerBoundary}>
        仅列出服务端已返回的年份、覆盖区间与分段数量。
      </p>
    </div>
  );
}

function ZiweiMonthLayer({
  onSelectRange,
  onSelectSegment,
  selectedId,
  selectedSegmentId,
  selection,
}: Readonly<{
  onSelectRange: (id: string) => void;
  onSelectSegment: (id: string) => void;
  selectedId: string;
  selectedSegmentId: string;
  selection: ZiweiTemporalSelection;
}>) {
  const selected =
    selection.options.find((option) => option.id === selectedId) ??
    selection.options[0];
  return (
    <div className={styles.layerFacts}>
      <TemporalLayerSelector
        label="流月月份"
        onSelect={onSelectRange}
        options={selection.options}
        selectedId={selectedId}
      />
      <TemporalLayerSelector
        label="流月分段"
        onSelect={onSelectSegment}
        options={selected.segments}
        selectedId={selectedSegmentId}
      />
      <table className={styles.layerTable}>
        <caption>流月盘面事实</caption>
        <thead>
          <tr>
            <th scope="col">月份</th>
            <th scope="col">覆盖区间</th>
            <th scope="col">分段</th>
          </tr>
        </thead>
        <tbody>
          {selection.options.map((option) => (
            <tr key={option.id}>
              <td>{option.label}</td>
              <td>{option.rangeLabel}</td>
              <td>{option.segments.length}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className={styles.layerBoundary}>
        仅列出服务端已返回的流月月份与分段数量。
      </p>
    </div>
  );
}

function ZiweiWorkspaceState({ layer }: Readonly<{ layer: WorkspaceLayer }>) {
  if (layer.status === "empty") {
    return (
      <div className={styles.workspaceState} data-state="empty">
        <h4>{layer.label}暂无结构</h4>
        <p>{layer.summary ?? "服务端尚未返回可展示结构。"}</p>
      </div>
    );
  }
  if (layer.status === "locked-unavailable") {
    return (
      <div className={styles.workspaceState} data-state="unavailable">
        <h4>{layer.label}待接入</h4>
        <p>{layer.summary ?? "当前没有可展示事实；此状态不提供购买入口。"}</p>
      </div>
    );
  }
  return (
    <div className={styles.workspaceState} data-state="locked">
      <h4>{layer.label}已锁定</h4>
      {layer.status === "fail-closed-unknown" ? (
        <p>
          <strong>权益状态未确认</strong>
          <span>当前盘面不会展示或预填任何付费事实。</span>
        </p>
      ) : (
        <p>当前盘面不会展示或预填任何锁定事实。</p>
      )}
      {layer.upgradeCta === "professional_info" ? (
        <Link className={styles.professionalInfoLink} href="/pricing">
          了解专业版
        </Link>
      ) : null}
    </div>
  );
}

function ZiweiReadingPane({
  detail,
  onClose,
}: Readonly<{
  detail: WorkspaceFocusDetail | null;
  onClose: () => void;
}>) {
  return (
    <div aria-label="连续阅读面" className={styles.readingPane}>
      <p className={styles.readingOrder}>盘面事实 / 方法边界 / 来源依据</p>
      <section aria-label="聚焦详情" className={styles.focusDetail}>
        <header className={styles.focusHeader}>
          <h4>聚焦详情</h4>
          {detail ? (
            <button aria-label="关闭聚焦详情" onClick={onClose} type="button">
              关闭
            </button>
          ) : null}
        </header>
        {detail ? (
          <div aria-live="polite" className={styles.focusBody}>
            <p className={styles.focusTitle}>{detail.title}</p>
            {detail.facts.length ? (
              <dl className={styles.focusFacts}>
                {detail.facts.map((fact) => (
                  <div key={`${fact.label}-${fact.text}`}>
                    <dt>{fact.label}</dt>
                    <dd>{fact.text}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
            {detail.limits.length ? (
              <div className={styles.focusNotes}>
                <h5>边界</h5>
                <ul>
                  {detail.limits.map((limit) => (
                    <li key={limit}>{limit}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {detail.sources.length ? (
              <div className={styles.focusNotes}>
                <h5>来源</h5>
                <ul>
                  {detail.sources.map((source) => (
                    <li key={source}>{source}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : (
          <p className={styles.focusEmpty}>
            选择一个宫位后，这里只显示已返回的宫位事实。
          </p>
        )}
      </section>
    </div>
  );
}

export function ZiweiWorkspace({
  view,
  showInterpretiveSections = true,
  timeLayerEntitlement,
}: Readonly<{
  view: ZiweiChartViewModel;
  showInterpretiveSections?: boolean;
  timeLayerEntitlement?: TimeLayerEntitlementResponse | null;
}>) {
  const layout = useResolvedLayout();
  const lifeBranch =
    view.palaces.find((palace) => palace.palace_id === view.life_palace_id)
      ?.earthly_branch ?? null;
  const [selectedBranch, setSelectedBranch] = useState<string | null>(
    lifeBranch,
  );
  const [activeBranch, setActiveBranch] = useState<string | null>(lifeBranch);
  const parsedEntitlement = useMemo(
    () => parseZiweiEntitlement(timeLayerEntitlement),
    [timeLayerEntitlement],
  );
  const workspace = useMemo(
    () => projectZiweiWorkspace(view, timeLayerEntitlement),
    [timeLayerEntitlement, view],
  );
  const temporalSelections = useMemo(
    () => ({
      yearly: temporalSelectionForLayer(
        view,
        "yearly",
        parsedEntitlement?.freeYears ?? EMPTY_FREE_YEAR_SET,
      ),
      monthly: temporalSelectionForLayer(view, "monthly"),
    }),
    [parsedEntitlement, view],
  );
  const temporalSelectionKey = [
    view.subject_ref,
    ...(["yearly", "monthly"] as const).map((layerId) => {
      const selection = temporalSelections[layerId];
      return selection
        ? `${layerId}:${selection.initialId}:${selection.options
            .map(
              (option) =>
                `${option.id}[${option.initialSegmentId}:${option.segments
                  .map((segment) => segment.id)
                  .join(",")}]`,
            )
            .join(",")}`
        : `${layerId}:none`;
    }),
  ].join("|");
  const [temporalSelectionState, setTemporalSelectionState] = useState<{
    key: string;
    ids: Partial<Record<ZiweiTemporalLayerId, string>>;
    segmentIds: Partial<Record<ZiweiTemporalLayerId, string>>;
  }>({ key: temporalSelectionKey, ids: {}, segmentIds: {} });
  const selectedTemporalIds =
    temporalSelectionState.key === temporalSelectionKey
      ? temporalSelectionState.ids
      : {};
  const selectedTemporalSegmentIds =
    temporalSelectionState.key === temporalSelectionKey
      ? temporalSelectionState.segmentIds
      : {};
  const unavailableLayerReasons = workspace.layers.flatMap((layer) => {
    const reason =
      layer.status === "locked-unavailable" ? layer.summary?.trim() : null;
    return reason ? [{ id: layer.id, label: layer.label, reason }] : [];
  });
  const [activeLayerId, setActiveLayerId] = useState<WorkspaceLayerId>(
    workspace.activeLayerId,
  );
  const locatorIdPrefix = useId();
  const workspacePanelId = `${locatorIdPrefix}-workspace-panel`;
  const activeLayer =
    workspace.layers.find((layer) => layer.id === activeLayerId) ??
    workspace.layers[0];
  const activeTemporalSelection =
    activeLayer.id === "yearly" || activeLayer.id === "monthly"
      ? temporalSelections[activeLayer.id]
      : null;
  const activeTemporalId = activeTemporalSelection
    ? (selectedTemporalIds[activeLayer.id as ZiweiTemporalLayerId] ??
      activeTemporalSelection.initialId)
    : null;
  const activeTemporalOption = activeTemporalSelection
    ? (activeTemporalSelection.options.find(
        (option) => option.id === activeTemporalId,
      ) ?? activeTemporalSelection.options[0])
    : null;
  const activeTemporalSegmentId = activeTemporalOption
    ? resolvedTemporalSegmentId(
        activeTemporalOption,
        selectedTemporalSegmentIds[activeLayer.id as ZiweiTemporalLayerId],
      )
    : null;
  const activePalaceView = useMemo(() => {
    if (activeLayer.status !== "ready") return view;
    if (activeLayer.id === "decadal") {
      return activeMajorLimitPalaceView(view) ?? view;
    }
    if (
      (activeLayer.id === "yearly" || activeLayer.id === "monthly") &&
      activeTemporalSelection
    ) {
      return (
        temporalPalaceViewForSelection(
          activeTemporalSelection,
          activeTemporalId,
          activeTemporalSegmentId,
        ) ?? view
      );
    }
    return view;
  }, [
    activeLayer.id,
    activeLayer.status,
    activeTemporalId,
    activeTemporalSegmentId,
    activeTemporalSelection,
    view,
  ]);
  const detail = useMemo(
    () => palaceFocusDetail(activePalaceView, activeBranch),
    [activeBranch, activePalaceView],
  );

  function selectBranch(branch: string | null) {
    setSelectedBranch(branch);
    setActiveBranch(branch);
  }

  function selectLayer(layerId: WorkspaceLayerId) {
    setActiveLayerId(layerId);
  }

  function selectTemporalLayer(layerId: ZiweiTemporalLayerId, id: string) {
    const selection = temporalSelections[layerId];
    if (!selection?.options.some((option) => option.id === id)) return;
    setTemporalSelectionState((current) => ({
      key: temporalSelectionKey,
      ids: {
        ...(current.key === temporalSelectionKey ? current.ids : {}),
        [layerId]: id,
      },
      segmentIds:
        current.key === temporalSelectionKey ? current.segmentIds : {},
    }));
  }

  function selectTemporalSegment(layerId: ZiweiTemporalLayerId, id: string) {
    const selection = temporalSelections[layerId];
    const selectedId = selectedTemporalIds[layerId] ?? selection?.initialId;
    const option = selection?.options.find((item) => item.id === selectedId);
    if (!option?.segments.some((segment) => segment.id === id)) return;
    setTemporalSelectionState((current) => ({
      key: temporalSelectionKey,
      ids: current.key === temporalSelectionKey ? current.ids : {},
      segmentIds: {
        ...(current.key === temporalSelectionKey ? current.segmentIds : {}),
        [layerId]: id,
      },
    }));
  }

  function renderReadyLayer(layer: WorkspaceLayer) {
    if (layer.id === "natal") return null;
    if (layer.id === "decadal") {
      return (
        <ZiweiMajorLimitTrack
          limits={view.core_facts?.major_limits ?? null}
          onSelectLimit={selectBranch}
          selectedBranch={selectedBranch}
          sequence={view.core_facts?.major_limit_sequence ?? null}
        />
      );
    }
    if (layer.id === "yearly" && temporalSelections.yearly) {
      const selectedId =
        selectedTemporalIds.yearly ?? temporalSelections.yearly.initialId;
      const selectedOption =
        temporalSelections.yearly.options.find(
          (option) => option.id === selectedId,
        ) ?? temporalSelections.yearly.options[0];
      return (
        <ZiweiYearLayer
          onSelectRange={(id) => selectTemporalLayer("yearly", id)}
          onSelectSegment={(id) => selectTemporalSegment("yearly", id)}
          selectedId={selectedId}
          selectedSegmentId={resolvedTemporalSegmentId(
            selectedOption,
            selectedTemporalSegmentIds.yearly,
          )}
          selection={temporalSelections.yearly}
        />
      );
    }
    if (layer.id === "monthly" && temporalSelections.monthly) {
      const selectedId =
        selectedTemporalIds.monthly ?? temporalSelections.monthly.initialId;
      const selectedOption =
        temporalSelections.monthly.options.find(
          (option) => option.id === selectedId,
        ) ?? temporalSelections.monthly.options[0];
      return (
        <ZiweiMonthLayer
          onSelectRange={(id) => selectTemporalLayer("monthly", id)}
          onSelectSegment={(id) => selectTemporalSegment("monthly", id)}
          selectedId={selectedId}
          selectedSegmentId={resolvedTemporalSegmentId(
            selectedOption,
            selectedTemporalSegmentIds.monthly,
          )}
          selection={temporalSelections.monthly}
        />
      );
    }
    return null;
  }

  return (
    <section
      className={styles.workspaceFrame}
      data-schema={view.schema_version}
      onKeyDown={(event) => {
        if (
          event.key !== "Escape" ||
          !activeBranch ||
          document.querySelector('[data-slot="palace-detail"]')
        ) {
          return;
        }
        event.preventDefault();
        selectBranch(null);
      }}
    >
      <ZiweiPalaceLocator
        onSelect={selectBranch}
        selectedBranch={selectedBranch}
        view={activePalaceView}
      />
      <section aria-label="排盘工作台" className={styles.workspace}>
        <header className={styles.workspaceHeader}>
          <div>
            <h3>{workspace.title}</h3>
            <p>定位与时间层 → 盘面 → 连续阅读面</p>
          </div>
          {workspace.subtitle ? <p>{workspace.subtitle}</p> : null}
        </header>
        <ZiweiTimeLayerLocator
          activeLayerId={activeLayer.id}
          idPrefix={locatorIdPrefix}
          layers={workspace.layers}
          onSelect={selectLayer}
          panelId={workspacePanelId}
        />
        {unavailableLayerReasons.length ? (
          <section
            aria-labelledby={`${locatorIdPrefix}-unavailable-layer-title`}
            className={styles.unavailableLayerNotes}
          >
            <p id={`${locatorIdPrefix}-unavailable-layer-title`}>
              不可用时间层说明
            </p>
            <ul aria-labelledby={`${locatorIdPrefix}-unavailable-layer-title`}>
              {unavailableLayerReasons.map((layer) => (
                <li key={layer.id}>
                  <strong>{layer.label}：</strong>
                  <span>{layer.reason}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        <div className={styles.workspaceBody}>
          <div
            aria-labelledby={`${locatorIdPrefix}-layer-${activeLayer.id}`}
            className={styles.workspaceBoard}
            id={workspacePanelId}
            role="region"
            tabIndex={0}
          >
            <ZiweiPalaceBoard
              layout={layout}
              onActiveBranchChange={setActiveBranch}
              onSelectedBranchChange={setSelectedBranch}
              selectedBranch={selectedBranch}
              showInterpretiveSections={showInterpretiveSections}
              showLocator={false}
              showSupportingSections={activeLayer.id === "natal"}
              view={activePalaceView}
            />
            {activeLayer.id !== "natal" ? (
              <div
                aria-live="polite"
                className={styles.layerContext}
                data-layer={activeLayer.id}
              >
                {activeLayer.status === "ready" ? (
                  renderReadyLayer(activeLayer)
                ) : (
                  <ZiweiWorkspaceState layer={activeLayer} />
                )}
              </div>
            ) : null}
          </div>
          <ZiweiReadingPane
            detail={detail}
            onClose={() => selectBranch(null)}
          />
        </div>
      </section>
    </section>
  );
}
