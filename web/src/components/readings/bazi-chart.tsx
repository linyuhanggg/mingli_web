"use client";

import {
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import {
  type BaziChartView,
} from "@/lib/reading-display";
import type {
  ReadingEvidence,
  VerifiedExactCitation,
} from "@/lib/api/contracts";
import type {
  BaziCalendarNormalization,
  BaziCoreFacts,
  BaziInterpretiveCandidates,
  BaziSourcePattern,
  BaziTemporalLayer,
} from "@/view-models/registry";
import {
  baziWorkspaceFactsFromChart,
  buildBaziWorkspaceView,
  resolveBaziFocusDetail,
} from "@/lib/chart-workspace";

import {
  countClassicalSourcesByPillar,
  isPillarId,
  resolvePillarForFactPath,
  type PillarId,
  type PillarSourceCounts,
} from "@/lib/classical-source-markers";

import { FocusDetailDrawer } from "./focus-detail-drawer";
import { BaziDeepEntry, type BaziS4Offer, type BaziS4Phase } from "./bazi-deep-entry";
import {
  natalFindingCards,
  type NatalFindingCard,
} from "./bazi-chart-findings";

import styles from "./bazi-chart.module.css";

function ChapterIndex({ index }: { index: string }) {
  return (
    <p aria-hidden="true" className={styles.chapterIndex}>
      {index}
    </p>
  );
}

function NatalFindingCards({
  cards,
  anchorId,
}: Readonly<{
  cards: ReadonlyArray<NatalFindingCard>;
  anchorId: string;
}>) {
  return (
    <section className={styles.findingList} id={anchorId} aria-label="盘面说明">
      {cards.map((card) => (
        <article key={`${card.title}-${card.body}`} className={styles.findingCard}>
          <h4>{card.title}</h4>
          <p>{card.body}</p>
        </article>
      ))}
    </section>
  );
}

/**
 * S3 盘面态（docs/redesign/2026-08-21-bazi-flow-spec.md）。
 * 本组件只投影服务端已返回的公开事实：不排盘、不推格局、不合成评分；
 * 缺失字段整块不渲染（DESIGN §19.2），时间层由 ViewModel time_layers 声明。
 */

const ELEMENT_LABELS: Record<string, string> = {
  wood: "木",
  fire: "火",
  earth: "土",
  metal: "金",
  water: "水",
};

const POSITION_LABELS: Record<string, string> = {
  year: "年柱",
  month: "月柱",
  day: "日柱",
  hour: "时柱",
};

type PillarPosition = "year" | "month" | "day" | "hour";

const PILLAR_POSITIONS: ReadonlyArray<PillarPosition> = [
  "year",
  "month",
  "day",
  "hour",
];

/** 干支→五行为固定字典；只允许用于染色，不用于生成事实文本（flow-spec S3-M2）。 */
const STEM_ELEMENTS: Readonly<Record<string, string>> = {
  甲: "wood",
  乙: "wood",
  丙: "fire",
  丁: "fire",
  戊: "earth",
  己: "earth",
  庚: "metal",
  辛: "metal",
  壬: "water",
  癸: "water",
};

const BRANCH_ELEMENTS: Readonly<Record<string, string>> = {
  子: "water",
  丑: "earth",
  寅: "wood",
  卯: "wood",
  辰: "earth",
  巳: "fire",
  午: "fire",
  未: "earth",
  申: "metal",
  酉: "metal",
  戌: "earth",
  亥: "water",
};

const LUCK_STATUS_LABELS: Readonly<Record<string, string>> = {
  calculated: "已计算",
  sequence_only: "仅返回序列",
  not_calculated_missing_gender: "因性别缺失未计算",
};

const LUCK_DIRECTION_LABELS: Readonly<Record<string, string>> = {
  forward: "顺行",
  reverse: "逆行",
};

const TIME_BASIS_POLICY_LABELS: Readonly<Record<string, string>> = {
  civil: "民用钟表时间",
  solar: "真太阳时",
  "local_apparent_solar-v1": "当地真太阳时",
  "longitude_mean_solar-v1": "当地平太阳时",
};

const ZI_HOUR_POLICY_LABELS: Readonly<Record<string, string>> = {
  midnight: "按午夜换日",
  substitute: "按晚子时口径换日",
  solar: "按太阳时判断子时",
};

const MONTH_SWITCH_POLICY_LABELS: Readonly<Record<string, string>> = {
  "exact Jie instant": "按节气交接时刻换月",
  "month-switch-at-jie-v1": "按节气交接时刻换月",
};

const TIAOHOU_SCOPE_LABELS: Readonly<Record<string, string>> = {
  "month-level climate anchors only": "仅作月令气候参照，不作调候结论",
  "month-level climate anchors only; not a 调候用神 conclusion":
    "仅作月令气候参照，不等于调候用神结论",
};

const TRUE_SOLAR_STATUS_LABELS: Readonly<Record<string, string>> = {
  apparent_solar_applied: "真太阳时已应用",
  longitude_mean_solar_applied: "经度平太阳时已应用",
  not_applied: "未应用真太阳时",
};

const CHANGED_PILLAR_LABELS: Readonly<Record<PillarPosition, string>> = {
  year: "年柱",
  month: "月柱",
  day: "日柱",
  hour: "时柱",
};

const PREDICATE_AUDIT_LABELS: Readonly<Record<string, string>> = {
  "/day_master/stem:eq:甲": "日主天干为甲",
  "/day_master/stem:eq:丙": "日主天干为丙",
  "/day_master/stem:nonempty:()": "日主天干已返回",
  "/four_pillars/year:eq:庚辰": "年柱为庚辰",
  "/four_pillars/month:eq:丙午": "月柱为丙午",
  "/calendar_normalization/ganzhi/year:nonempty": "年柱干支已返回",
};

function visiblePolicyLabel(
  value: string,
  labels: Readonly<Record<string, string>>,
): string {
  if (labels[value]) return labels[value];
  return /[\u3400-\u9fff]/u.test(value) ? value : "服务端已记录";
}

function formatServerDateTime(value: string): string {
  const match = value.match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/u,
  );
  if (!match) return value;
  const [, year, month, day, hour, minute, second] = match;
  const seconds = second && second !== "00" ? `:${second}` : "";
  return `${year}年${Number(month)}月${Number(day)}日 ${hour}:${minute}${seconds}`;
}

function formatSeconds(value: number | null): string | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return `${value > 0 ? "+" : ""}${Math.round(value)} 秒`;
}

function relationCategory(relationType: string): string {
  if (/[合会]/u.test(relationType)) return "合会";
  if (/冲/u.test(relationType)) return "冲";
  if (/刑/u.test(relationType)) return "刑";
  if (/害/u.test(relationType)) return "害";
  if (/破/u.test(relationType)) return "破";
  return "其他";
}

/* ---------- 联动高亮（DESIGN §21.1） ---------- */

type PillarSelection = Readonly<{
  position: PillarPosition;
  stem: string;
  branch: string;
  elements: ReadonlyArray<string>;
}> | null;

function FactMark({
  value,
  selection,
  highlightValue = value,
}: Readonly<{
  value: string;
  selection: PillarSelection;
  highlightValue?: string;
}>) {
  const highlighted = Boolean(
    selection &&
      (highlightValue === selection.stem || highlightValue === selection.branch),
  );
  return (
    <span
      className={highlighted ? styles.factHighlight : undefined}
      data-fact-highlight={highlighted ? "true" : undefined}
    >
      {value}
    </span>
  );
}

function FactMarks({
  values,
  selection,
  separator = "、",
}: Readonly<{
  values: ReadonlyArray<string>;
  selection: PillarSelection;
  separator?: string;
}>) {
  return values.map((value, index) => (
    <span key={`${value}-${index}`}>
      {index > 0 ? separator : null}
      <FactMark value={value} selection={selection} />
    </span>
  ));
}

function FactElementMark({
  element,
  selection,
}: Readonly<{ element: string; selection: PillarSelection }>) {
  const highlighted = Boolean(selection?.elements.includes(element));
  return (
    <span
      className={highlighted ? styles.factHighlight : undefined}
      data-fact-highlight={highlighted ? "true" : undefined}
    >
      {ELEMENT_LABELS[element] ?? "五行已记录"}
    </span>
  );
}

function pillarElements(
  value: string | null | undefined,
  position: PillarPosition,
  hiddenStems: BaziCoreFacts["hidden_stems"] | undefined,
): ReadonlyArray<string> {
  if (!value) return [];
  const hiddenStemValues =
    hiddenStems?.find((item) => item.position === position)?.stems ?? [];
  return Array.from(
    new Set(
      [
        STEM_ELEMENTS[value.slice(0, 1)],
        BRANCH_ELEMENTS[value.slice(1, 2)],
        ...hiddenStemValues.map((stem) => STEM_ELEMENTS[stem]),
      ]
        .filter((element): element is string => Boolean(element)),
    ),
  );
}

/** 域字（宋体系）大字。data-element 只染色，不生成事实文本。 */
function Glyph({
  char,
  size,
  dayMaster = false,
  selection,
}: Readonly<{
  char: string;
  size: "display" | "cell";
  dayMaster?: boolean;
  selection: PillarSelection;
}>) {
  const element = STEM_ELEMENTS[char] ?? BRANCH_ELEMENTS[char];
  const highlighted = Boolean(
    selection && (char === selection.stem || char === selection.branch),
  );
  return (
    <span
      className={size === "display" ? styles.glyphDisplay : styles.glyphCell}
      data-element={element}
      data-day-master={dayMaster ? "true" : undefined}
      data-fact-highlight={highlighted ? "true" : undefined}
    >
      {char}
    </span>
  );
}

/* ---------- 时间层 chips（工作条；由 ViewModel time_layers 声明） ---------- */

type LayerChip = Readonly<{
  id: string;
  label: string;
  enabled: boolean;
  reason: string | null;
}>;

const TRANSIT_LAYER_IDS = new Set(["year", "month", "day"]);
const NATAL_LAYER_IDS = new Set(["natal", "life"]);

export type SingleLayerPreviewTarget = {
  target_year?: number;
  target_month?: string;
  target_date?: string;
};

export function singleLayerPreviewTarget(
  layerId: string,
  now: Date = new Date(),
): SingleLayerPreviewTarget {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  if (layerId === "year") return { target_year: year };
  if (layerId === "month") return { target_month: `${year}-${month}` };
  if (layerId === "day") return { target_date: `${year}-${month}-${day}` };
  return {};
}

export function countPreviewTargets(target: SingleLayerPreviewTarget): number {
  return [target.target_year, target.target_month, target.target_date].filter(
    (value) => value != null && value !== "",
  ).length;
}

export function previewQueryForTimeLayer(layerId: string): string {
  if (layerId === "year") return "请预览我的八字流年盘面。";
  if (layerId === "month") return "请预览我的八字流月盘面。";
  if (layerId === "day") return "请预览我的八字流日盘面。";
  return "请预览我的八字命盘。";
}

function TimeLayerChips({
  chips,
  activeId,
  pendingId,
  onSelect,
}: Readonly<{
  chips: ReadonlyArray<LayerChip>;
  activeId: string;
  pendingId?: string | null;
  onSelect: (id: string) => void;
}>) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const requestInFlight = Boolean(pendingId);

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, id: string) {
    if (requestInFlight) return;
    const enabled = chips.filter((chip) => chip.enabled);
    const index = enabled.findIndex((chip) => chip.id === id);
    if (index < 0) return;
    let target: number | null = null;
    if (event.key === "ArrowRight") target = (index + 1) % enabled.length;
    else if (event.key === "ArrowLeft") {
      target = (index - 1 + enabled.length) % enabled.length;
    } else if (event.key === "Home") target = 0;
    else if (event.key === "End") target = enabled.length - 1;
    if (target === null) return;
    event.preventDefault();
    const chip = enabled[target];
    refs.current[chip.id]?.focus();
    onSelect(chip.id);
  }

  return (
    <div className={styles.chipsRow} role="group" aria-label="时间层">
      {chips.map((chip) => {
        const active = chip.id === activeId;
        const pending = chip.id === pendingId;
        return (
          <button
            key={chip.id}
            type="button"
            ref={(element) => {
              refs.current[chip.id] = element;
            }}
            className={styles.chip}
            data-active={active ? "true" : undefined}
            data-pending={pending ? "true" : undefined}
            aria-pressed={active}
            aria-busy={pending || undefined}
            disabled={!chip.enabled || requestInFlight}
            title={chip.reason ?? undefined}
            onClick={() => onSelect(chip.id)}
            onKeyDown={(event) => handleKeyDown(event, chip.id)}
          >
            <span className={styles.chipLabel}>{chip.label}</span>
            {chip.reason ? (
              <span className={styles.chipReason}>{chip.reason}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

/* ---------- M1 时间口径条（G3） ---------- */

function timeBasisRows(
  calendar: BaziCalendarNormalization,
): Array<{ label: string; value: string }> {
  const rows: Array<{ label: string; value: string }> = [];
  const boundary = calendar.time_basis.boundary;

  if (typeof calendar.time_basis.standard_meridian_degrees === "number") {
    rows.push({
      label: "标准经线",
      value: `${calendar.time_basis.standard_meridian_degrees}°`,
    });
  }
  const longitude = formatSeconds(calendar.time_basis.longitude_correction_seconds);
  if (longitude) rows.push({ label: "经度修正", value: longitude });
  const equation = formatSeconds(calendar.time_basis.equation_of_time_seconds);
  if (equation) rows.push({ label: "均时差", value: equation });
  const total = formatSeconds(calendar.time_basis.total_correction_seconds);
  if (total) rows.push({ label: "总修正", value: total });
  if (calendar.effective_datetime) {
    rows.push({
      label: "排盘采用时刻",
      value: formatServerDateTime(calendar.effective_datetime),
    });
  }
  rows.push({
    label: "真太阳时",
    value:
      TRUE_SOLAR_STATUS_LABELS[calendar.true_solar_time.status] ?? "状态已记录",
  });
  if (typeof boundary.correction_changes_hour_branch === "boolean") {
    rows.push({
      label: "时辰边界",
      value: boundary.correction_changes_hour_branch
        ? "跨时辰边界"
        : "未跨时辰边界",
    });
  }
  if (calendar.day_boundary) {
    rows.push({
      label: "日界状态",
      value: calendar.day_boundary.correction_crossed_date
        ? "修正跨越日界"
        : "修正未跨日界",
    });
    rows.push({
      label: "换日结果",
      value: calendar.day_boundary.zi_policy_advanced_day_pillar
        ? "晚子时策略推进日柱"
        : "晚子时策略未推进日柱",
    });
  }
  if (calendar.changed_pillars) {
    rows.push({
      label: "变柱",
      value:
        calendar.changed_pillars.length > 0
          ? `该修正改变了${calendar.changed_pillars
              .map((pillar) => CHANGED_PILLAR_LABELS[pillar])
              .join("、")}`
          : "该修正未改变四柱",
    });
  }
  if (typeof boundary.distance_seconds === "number") {
    rows.push({
      label: "边界距离",
      value: `${Math.round(boundary.distance_seconds)} 秒`,
    });
  }
  if (typeof boundary.within_uncertainty === "boolean") {
    rows.push({
      label: "不确定区间",
      value: boundary.within_uncertainty ? "位于不确定区间" : "不在不确定区间",
    });
  }
  if (calendar.calendar_convention.zi_hour_policy) {
    rows.push({
      label: "子时口径",
      value: visiblePolicyLabel(
        calendar.calendar_convention.zi_hour_policy,
        ZI_HOUR_POLICY_LABELS,
      ),
    });
  }
  const solarTerms = calendar.solar_terms;
  if (solarTerms?.previous) {
    rows.push({
      label: "前一节气",
      value: `${solarTerms.previous.name} · ${formatServerDateTime(solarTerms.previous.datetime)}${solarTerms.previous.is_month_boundary_jie ? " · 月界节" : ""}`,
    });
  }
  if (solarTerms?.next) {
    rows.push({
      label: "后一节气",
      value: `${solarTerms.next.name} · ${formatServerDateTime(solarTerms.next.datetime)}${solarTerms.next.is_month_boundary_jie ? " · 月界节" : ""}`,
    });
  }
  if (solarTerms?.month_switch_policy) {
    rows.push({
      label: "换月口径",
      value: visiblePolicyLabel(
        solarTerms.month_switch_policy,
        MONTH_SWITCH_POLICY_LABELS,
      ),
    });
  }
  return rows;
}

/**
 * 口径跨界（改变了柱、跨时辰或跨日界）时详情默认展开并给通栏标注；
 * 未跨界时是一行平静的信息 +「详情」折叠（flow-spec S3-M1 默认态纪律）。
 */
function TimeBasisBar({
  calendar,
}: Readonly<{ calendar: BaziCalendarNormalization | null | undefined }>) {
  const changedPillars = calendar?.changed_pillars ?? [];
  const crossed = Boolean(
    calendar &&
      (changedPillars.length > 0 ||
        calendar.time_basis.boundary.correction_changes_hour_branch ||
        calendar.day_boundary?.correction_crossed_date),
  );
  const [open, setOpen] = useState(crossed);
  if (!calendar) return null;

  const policyLabel = visiblePolicyLabel(
    calendar.time_basis.policy,
    TIME_BASIS_POLICY_LABELS,
  );
  const rows = timeBasisRows(calendar);

  return (
    <section className={styles.basisBar} aria-label="时间口径">
      <ChapterIndex index="01" />
      {changedPillars.length > 0 ? (
        <p className={styles.basisBanner}>
          口径修正改变了
          <strong>
            {changedPillars
              .map((pillar) => CHANGED_PILLAR_LABELS[pillar])
              .join("、")}
          </strong>
          ，对应矩阵列头已标注。
        </p>
      ) : null}
      <details
        className={styles.basisDetails}
        open={open}
        onToggle={(event) => {
          const next = event.currentTarget.open;
          if (next !== open) setOpen(next);
        }}
      >
        <summary className={styles.basisCalm}>
          <span className={styles.basisPolicy}>{policyLabel}</span>
          <span className={styles.basisState}>
            {crossed ? "口径修正跨越边界" : "口径修正未跨越时辰与日界"}
          </span>
          <span className={styles.basisToggle}>详情</span>
        </summary>
        <dl className={styles.timeBasisList}>
          {rows.map((row, index) => (
            <div key={`${row.label}-${index}`}>
              <dt>{row.label}</dt>
              <dd>{row.value}</dd>
            </div>
          ))}
        </dl>
      </details>
    </section>
  );
}

/* ---------- M2 四柱矩阵 ---------- */

type YearLayer = NonNullable<BaziCoreFacts["year_layers"]>[number];

function stemGodFor(
  facts: BaziCoreFacts | null | undefined,
  position: PillarPosition,
): string | null {
  return (
    facts?.ten_gods?.heavenly_stems.find((item) => item.position === position)
      ?.ten_god ?? null
  );
}

function PillarMatrix({
  chart,
  selection,
  selectedId,
  detailId,
  onSelect,
  onTransientChange,
  sourceCounts,
  transitLayers,
}: Readonly<{
  chart: BaziChartView;
  selection: PillarSelection;
  selectedId: string | null;
  detailId: string;
  onSelect: (cellId: string | null) => void;
  onTransientChange: (cellId: string | null) => void;
  sourceCounts: PillarSourceCounts | null;
  transitLayers: ReadonlyArray<YearLayer>;
}>) {
  const facts = chart.coreFacts ?? null;
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const [tabStopId, setTabStopId] = useState<string>(PILLAR_POSITIONS[0]);
  if (!chart.pillars) return null;

  const voidBranches = new Set(facts?.xunkong?.branches ?? []);
  const changedPillars = new Set(
    facts?.calendar_normalization?.changed_pillars ?? [],
  );

  function focusAt(index: number) {
    if (index >= 0 && index < PILLAR_POSITIONS.length) {
      setTabStopId(PILLAR_POSITIONS[index]);
      refs.current[index]?.focus();
    }
  }

  function handleKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    if (event.key === "Escape") {
      event.preventDefault();
      onSelect(null);
    } else if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      focusAt((index + 1) % PILLAR_POSITIONS.length);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      focusAt((index - 1 + PILLAR_POSITIONS.length) % PILLAR_POSITIONS.length);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusAt(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusAt(PILLAR_POSITIONS.length - 1);
    }
  }

  const hiddenRow = facts?.hidden_stems?.length ? facts.hidden_stems : null;
  const hiddenGodRow = facts?.ten_gods?.hidden_stems?.length
    ? facts.ten_gods.hidden_stems
    : null;
  const nayinRow = facts?.nayin?.length ? facts.nayin : null;
  const stageRow = facts?.twelve_growth_stages?.length
    ? facts.twelve_growth_stages
    : null;
  const shenshaItems =
    facts?.shensha_auxiliary?.calculated_items.filter(
      (item) => item.matched_positions.length > 0,
    ) ?? [];
  const shenshaRow = shenshaItems.length > 0 ? shenshaItems : null;
  const hasFactRows = Boolean(
    hiddenRow || hiddenGodRow || nayinRow || stageRow || shenshaRow,
  );
  const transitActive = transitLayers.length > 0;

  return (
    <div className={styles.folio}>
      <p className={styles.folioMeta}>
        <span className={styles.folioSeal}>八字</span>
        <span aria-hidden="true" className={styles.chapterIndex}>
          02
        </span>
      </p>
    <div className={styles.matrixGroup} role="group" aria-label="四柱">
      <div className={styles.matrixViewport}>
        <table
          className={styles.matrix}
          aria-label="四柱矩阵"
          data-transit={transitActive ? "true" : undefined}
        >
          <thead>
            <tr>
              <td className={styles.cornerCell}>
                <span className="sr-only">事实类别</span>
              </td>
              {PILLAR_POSITIONS.map((position, index) => {
                const value = chart.pillars?.[position] || null;
                const stem = value?.slice(0, 1) ?? null;
                const branch = value?.slice(1, 2) ?? null;
                const stemGod = stemGodFor(facts, position);
                const sourceCount = sourceCounts?.[position] ?? 0;
                const sourceNote =
                  sourceCount > 0 ? `有 ${sourceCount} 条古法涉及此柱` : null;
                const changed = changedPillars.has(position);
                return (
                  <th key={position} scope="col" className={styles.pillarHead}>
                    <button
                      type="button"
                      ref={(element) => {
                        refs.current[index] = element;
                      }}
                      className={styles.pillarCard}
                      data-selected={position === selectedId}
                      aria-pressed={position === selectedId}
                      aria-controls={detailId}
                      aria-expanded={position === selectedId}
                      tabIndex={position === tabStopId ? 0 : -1}
                      onClick={() => onSelect(position)}
                      onMouseEnter={() => onTransientChange(position)}
                      onMouseLeave={() => onTransientChange(null)}
                      onFocus={() => {
                        setTabStopId(position);
                        onTransientChange(position);
                      }}
                      onBlur={() => onTransientChange(null)}
                      onKeyDown={(event) => handleKeyDown(event, index)}
                    >
                      <span className={styles.pillarLabel}>
                        {POSITION_LABELS[position]}
                        {changed ? (
                          <span
                            className={styles.changedMark}
                            aria-label="该柱受时间口径修正影响"
                          >
                            变
                          </span>
                        ) : null}
                      </span>
                      {stem ? (
                        <Glyph
                          char={stem}
                          size="display"
                          dayMaster={position === "day"}
                          selection={selection}
                        />
                      ) : (
                        <span className={styles.glyphEmpty}>—</span>
                      )}
                      {stemGod ? (
                        <span className={styles.stemGod}>
                          <FactMark
                            value={stemGod}
                            highlightValue={stem ?? stemGod}
                            selection={selection}
                          />
                        </span>
                      ) : null}
                      {branch ? (
                        <span className={styles.branchWrap}>
                          <Glyph char={branch} size="display" selection={selection} />
                          {voidBranches.has(branch) ? (
                            <span
                              className={styles.voidMark}
                              title="旬空：日柱所属那一旬中缺位的两个地支"
                            >
                              空
                            </span>
                          ) : null}
                        </span>
                      ) : (
                        <span className={styles.glyphEmpty}>—</span>
                      )}
                      {!value && position === "hour" ? (
                        <span className={styles.stemGod}>时辰未知</span>
                      ) : null}
                      {sourceNote ? (
                        <span
                          className={styles.pillarSourceMark}
                          data-source-count={sourceCount}
                        >
                          <span aria-hidden="true">典 {sourceCount}</span>
                          <span className={styles.pillarSourceHint}>{sourceNote}</span>
                        </span>
                      ) : null}
                    </button>
                  </th>
                );
              })}
              {transitLayers.map((layer) => (
                <th
                  key={`transit-${layer.year}`}
                  scope="col"
                  className={styles.transitHead}
                  data-active="true"
                >
                  <span className={styles.pillarLabel}>流年柱 · {layer.year}</span>
                  <Glyph
                    char={layer.ganzhi.slice(0, 1)}
                    size="display"
                    selection={selection}
                  />
                  <span className={styles.stemGod}>
                    <FactMark
                      value={layer.stem_ten_god}
                      highlightValue={layer.ganzhi.slice(0, 1)}
                      selection={selection}
                    />
                  </span>
                  <Glyph
                    char={layer.ganzhi.slice(1, 2)}
                    size="display"
                    selection={selection}
                  />
                </th>
              ))}
            </tr>
          </thead>
          {hasFactRows ? (
            <tbody>
              {hiddenRow ? (
                <tr>
                  <th scope="row">藏干</th>
                  {PILLAR_POSITIONS.map((position) => {
                    const entry = hiddenRow.find(
                      (item) => item.position === position,
                    );
                    return (
                      <td key={position} data-active-col={position === selectedId ? "true" : undefined}>
                        {entry ? (
                          <span className={styles.hiddenStack}>
                            {entry.stems.map((stem, index) => (
                              <span
                                key={`${stem}-${index}`}
                                className={styles.hiddenStem}
                                data-rank={index === 0 ? "main" : "rest"}
                                data-element={STEM_ELEMENTS[stem]}
                              >
                                <FactMark value={stem} selection={selection} />
                              </span>
                            ))}
                          </span>
                        ) : null}
                      </td>
                    );
                  })}
                  {transitLayers.map((layer) => (
                    <td key={`transit-${layer.year}`} data-active="true" />
                  ))}
                </tr>
              ) : null}
              {hiddenGodRow ? (
                <tr>
                  <th scope="row">藏干十神</th>
                  {PILLAR_POSITIONS.map((position) => {
                    const entries = hiddenGodRow.filter(
                      (item) => item.position === position,
                    );
                    return (
                      <td key={position} data-active-col={position === selectedId ? "true" : undefined}>
                        {entries.length > 0 ? (
                          <span className={styles.hiddenStack}>
                            {entries.map((item, index) => (
                              <span key={`${item.stem}-${index}`} className={styles.hiddenGod}>
                                <FactMark value={item.stem} selection={selection} />
                                {" · "}
                                <FactMark
                                  value={item.ten_god}
                                  highlightValue={item.stem}
                                  selection={selection}
                                />
                              </span>
                            ))}
                          </span>
                        ) : null}
                      </td>
                    );
                  })}
                  {transitLayers.map((layer) => (
                    <td key={`transit-${layer.year}`} data-active="true">
                      <span className={styles.hiddenStack}>
                        {layer.branch_hidden_ten_gods.map((item, index) => (
                          <span key={`${item.stem}-${index}`} className={styles.hiddenGod}>
                            <FactMark value={item.stem} selection={selection} />
                            {" · "}
                            <FactMark
                              value={item.ten_god}
                              highlightValue={item.stem}
                              selection={selection}
                            />
                          </span>
                        ))}
                      </span>
                    </td>
                  ))}
                </tr>
              ) : null}
              {nayinRow ? (
                <tr>
                  <th scope="row">纳音</th>
                  {PILLAR_POSITIONS.map((position) => (
                    <td key={position} data-active-col={position === selectedId ? "true" : undefined}>
                      {nayinRow.find((item) => item.position === position)?.name ?? null}
                    </td>
                  ))}
                  {transitLayers.map((layer) => (
                    <td key={`transit-${layer.year}`} data-active="true" />
                  ))}
                </tr>
              ) : null}
              {stageRow ? (
                <tr>
                  <th scope="row">十二长生</th>
                  {PILLAR_POSITIONS.map((position) => {
                    const entry = stageRow.find(
                      (item) => item.position === position,
                    );
                    return (
                      <td key={position} data-active-col={position === selectedId ? "true" : undefined}>
                        {entry ? entry.stage : null}
                      </td>
                    );
                  })}
                  {transitLayers.map((layer) => (
                    <td key={`transit-${layer.year}`} data-active="true" />
                  ))}
                </tr>
              ) : null}
              {shenshaRow ? (
                <tr>
                  <th scope="row">神煞</th>
                  {PILLAR_POSITIONS.map((position) => {
                    const names = shenshaRow
                      .filter((item) => item.matched_positions.includes(position))
                      .map((item) => item.name);
                    return (
                      <td key={position} data-active-col={position === selectedId ? "true" : undefined}>
                        {names.length > 0 ? (
                          <span className={styles.hiddenStack}>
                            {names.map((name, index) => (
                              <span key={`${name}-${index}`} className={styles.shenshaChip}>
                                {name}
                              </span>
                            ))}
                          </span>
                        ) : null}
                      </td>
                    );
                  })}
                  {transitLayers.map((layer) => (
                    <td key={`transit-${layer.year}`} data-active="true" />
                  ))}
                </tr>
              ) : null}
            </tbody>
          ) : null}
        </table>
      </div>
    </div>
    </div>
  );
}

/* ---------- M2 关系连线（矩阵下缘弧线 + 语义表格） ---------- */

function relationHighlightsSelection(
  relation: Readonly<{ positions: ReadonlyArray<string>; branches: ReadonlyArray<string> }>,
  selection: PillarSelection,
): boolean {
  return Boolean(
    selection &&
      (relation.positions.includes(selection.position) ||
        relation.branches.includes(selection.branch)),
  );
}

function RelationArcs({
  facts,
  selection,
  anchorId,
}: Readonly<{
  facts: BaziCoreFacts;
  selection: PillarSelection;
  anchorId?: string;
}>) {
  const relations = facts.branch_relations ?? [];
  if (relations.length === 0) return null;

  const arcs = relations.flatMap((relation, relationIndex) => {
    const positions = relation.positions.filter(
      (position): position is PillarPosition =>
        PILLAR_POSITIONS.includes(position as PillarPosition),
    );
    if (positions.length < 2) return [];
    const highlighted = relationHighlightsSelection(relation, selection);
    return positions.slice(1).map((target, pairIndex) => ({
      id: `${relationIndex}-${pairIndex}`,
      relationType: relation.relation_type,
      source: positions[0],
      target,
      highlighted,
    }));
  });

  return (
    <section className={styles.relationSection} aria-label="干支关系事实" id={anchorId}>
      <div className={styles.sectionHeading}>
        <h4>干支关系</h4>
        <p>按服务端返回的柱位与关系事实展示；类别只作中性区分。</p>
      </div>
      {arcs.length > 0 ? (
        <svg
          className={styles.relationSvg}
          viewBox="0 0 400 56"
          preserveAspectRatio="none"
          role="img"
          aria-label="地支关系连线"
        >
          <title>地支关系连线</title>
          {arcs.map((arc) => {
            const sourceX = PILLAR_POSITIONS.indexOf(arc.source) * 100 + 50;
            const targetX = PILLAR_POSITIONS.indexOf(arc.target) * 100 + 50;
            const midX = (sourceX + targetX) / 2;
            return (
              <path
                key={arc.id}
                className={styles.relationArc}
                data-category={relationCategory(arc.relationType)}
                data-relation-type={arc.relationType}
                data-fact-highlight={arc.highlighted ? "true" : undefined}
                d={`M ${sourceX} 8 Q ${midX} 56, ${targetX} 8`}
              />
            );
          })}
        </svg>
      ) : null}
      <ul className={styles.relationChips}>
        {relations.map((relation, index) => (
          <li key={`${relation.relation_type}-${index}`}>
            <span
              className={styles.relationTag}
              data-category={relationCategory(relation.relation_type)}
              data-fact-highlight={
                relationHighlightsSelection(relation, selection) ? "true" : undefined
              }
            >
              {relation.relation_type}
            </span>
            <span className={styles.relationMeta}>
              {relation.positions
                .map((position) => POSITION_LABELS[position] ?? position)
                .join("·")}
              {" "}
              <FactMarks values={relation.branches} selection={selection} />
            </span>
          </li>
        ))}
      </ul>
      <div className={styles.tableViewport}>
        <table className={styles.factTable}>
          <caption>地支关系事实</caption>
          <thead>
            <tr>
              <th scope="col">关系类型</th>
              <th scope="col">柱位</th>
              <th scope="col">地支</th>
              <th scope="col">类别</th>
            </tr>
          </thead>
          <tbody>
            {relations.map((relation, index) => {
              const highlighted = relationHighlightsSelection(relation, selection);
              return (
                <tr key={`${relation.relation_type}-${index}`}>
                  <th scope="row">
                    <span
                      className={styles.relationTag}
                      data-category={relationCategory(relation.relation_type)}
                      data-fact-highlight={highlighted ? "true" : undefined}
                    >
                      {relation.relation_type}
                    </span>
                  </th>
                  <td>
                    {relation.positions
                      .map((position) => POSITION_LABELS[position] ?? position)
                      .join("、")}
                  </td>
                  <td>
                    <FactMarks values={relation.branches} selection={selection} />
                  </td>
                  <td>{relationCategory(relation.relation_type)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* ---------- M8 大运轨 ---------- */

type LuckCycles = NonNullable<BaziCoreFacts["luck_cycles"]>;

function LuckCycleTrack({
  facts,
  activePillar,
  anchorId,
  selection,
}: Readonly<{
  facts: LuckCycles;
  activePillar: string | null;
  anchorId?: string;
  selection: PillarSelection;
}>) {
  if (facts.status === "not_calculated_missing_gender") {
    return (
      <section className={styles.luckSection} aria-label="大运" id={anchorId}>
        <div className={styles.sectionHeading}>
          <ChapterIndex index="04" />
          <h4>大运</h4>
        </div>
        <p
          className={styles.luckMissing}
          data-status="not_calculated_missing_gender"
        >
          未提供性别，无法确定大运顺逆。
        </p>
      </section>
    );
  }

  const showAges = facts.status === "calculated";
  const boundary = facts.boundary_term
    ? `${facts.boundary_term.name} · ${formatServerDateTime(facts.boundary_term.datetime)}`
    : null;
  const basisRows: Array<{ label: string; value: string }> = [];
  if (facts.direction) {
    basisRows.push({
      label: "顺逆",
      value: LUCK_DIRECTION_LABELS[facts.direction] ?? "顺逆已记录",
    });
  }
  if (facts.direction_rule) {
    basisRows.push({
      label: "顺逆规则",
      value: visiblePolicyLabel(facts.direction_rule, {}),
    });
  }
  if (facts.start_age_rule) {
    basisRows.push({
      label: "起运规则",
      value: visiblePolicyLabel(facts.start_age_rule, {}),
    });
  }
  if (facts.start_age_years != null) {
    basisRows.push({ label: "起运岁数", value: `${facts.start_age_years} 岁` });
  }
  if (boundary) basisRows.push({ label: "边界节气", value: boundary });
  if (facts.interval_days != null) {
    basisRows.push({ label: "间隔天数", value: `${facts.interval_days} 天` });
  }
  if (facts.approximate_start_datetime) {
    basisRows.push({
      label: "约略起运时刻",
      value: formatServerDateTime(facts.approximate_start_datetime),
    });
  }

  return (
    <section className={styles.luckSection} aria-label="大运" id={anchorId}>
      <div className={styles.sectionHeading}>
        <ChapterIndex index="04" />
        <h4>
          大运
          <span
            className={styles.luckStatus}
            data-status={facts.status}
          >
            {LUCK_STATUS_LABELS[facts.status] ?? "状态已记录"}
          </span>
        </h4>
      </div>
      {facts.cycles.length > 0 ? (
        <div className={styles.luckTrackViewport}>
          <ol className={styles.luckTrack} aria-label="大运序列">
            {facts.cycles.map((cycle) => (
              <li
                key={`${cycle.sequence}-${cycle.pillar}`}
                className={styles.luckStep}
                data-active={cycle.pillar === activePillar ? "true" : undefined}
              >
                <span className={styles.luckSeq}>第 {cycle.sequence} 运</span>
                <span className={styles.luckGanzhi}>
                  {cycle.pillar.split("").map((char, index) => (
                    <Glyph
                      key={`${char}-${index}`}
                      char={char}
                      size="cell"
                      selection={selection}
                    />
                  ))}
                </span>
                {showAges && cycle.start_age_years != null ? (
                  <span className={styles.luckAges}>
                    {cycle.start_age_years}–{cycle.end_age_years ?? "…"} 岁
                  </span>
                ) : null}
                {cycle.pillar === activePillar ? (
                  <span className={styles.luckActiveMark}>当年所在</span>
                ) : null}
              </li>
            ))}
          </ol>
        </div>
      ) : null}
      <details className={styles.foldBlock}>
        <summary>起运依据</summary>
        <dl className={styles.metaList}>
          {basisRows.map((row) => (
            <div key={row.label}>
              <dt>{row.label}</dt>
              <dd>{row.value}</dd>
            </div>
          ))}
        </dl>
      </details>
      {facts.unavailable.length > 0 ? (
        <div className={styles.unavailableFacts}>
          <h5>未能计算的项目</h5>
          <ul>
            {facts.unavailable.map((item, index) => (
              <li key={`${item}-${index}`}>{visiblePolicyLabel(item, {})}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

/* ---------- M3 日主与月令 ---------- */

function DayMasterPanel({
  facts,
  selection,
  anchorId,
}: Readonly<{
  facts: BaziCoreFacts;
  selection: PillarSelection;
  anchorId?: string;
}>) {
  const rows: Array<{ label: string; content: ReactNode }> = [];
  if (facts.day_master) {
    rows.push({
      label: "日主",
      content: (
        <>
          <FactMark value={facts.day_master.stem} selection={selection} />
          {` · ${ELEMENT_LABELS[facts.day_master.element] ?? "五行已记录"} · ${facts.day_master.polarity}`}
        </>
      ),
    });
  }
  if (facts.month_command) {
    rows.push({
      label: "月令",
      content: (
        <>
          {facts.month_command.label} · 主气{" "}
          <FactMark value={facts.month_command.main_qi} selection={selection} />
          （{ELEMENT_LABELS[facts.month_command.main_qi_element] ?? "五行已记录"}）
        </>
      ),
    });
  }
  if (facts.seasonal_profile) {
    rows.push({
      label: "季节剖面",
      content: `${facts.seasonal_profile.season} · ${facts.seasonal_profile.month_qi} · ${facts.seasonal_profile.temperature} · ${facts.seasonal_profile.moisture}`,
    });
  }
  if (facts.tiaohou_markers) {
    rows.push({
      label: "调候标记",
      content: (
        <>
          {facts.tiaohou_markers.markers.join("、")}
          <span className={styles.termDef}>
            {visiblePolicyLabel(facts.tiaohou_markers.scope, TIAOHOU_SCOPE_LABELS)}
          </span>
        </>
      ),
    });
  }
  if (facts.san_yuan) {
    rows.push({
      label: "三垣",
      content: `胎元 ${facts.san_yuan.tai_yuan} · 命宫 ${facts.san_yuan.ming_gong} · 身宫 ${facts.san_yuan.shen_gong}`,
    });
  }
  if (facts.xunkong) {
    rows.push({
      label: "旬空",
      content: (
        <>
          {`${facts.xunkong.day_pillar} 属 ${facts.xunkong.xun} 旬：${facts.xunkong.branches.join("、")}`}
          <span className={styles.termDef}>日柱所属那一旬中缺位的两个地支</span>
        </>
      ),
    });
  }
  if (rows.length === 0) return null;
  return (
    <section className={styles.panel} aria-label="日主与月令" id={anchorId}>
      <div className={styles.sectionHeading}>
        <h4>日主与月令</h4>
      </div>
      <dl className={styles.metaList}>
        {rows.map((row) => (
          <div key={row.label}>
            <dt>{row.label}</dt>
            <dd>{row.content}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/* ---------- M4 五行盘点 ---------- */

function ElementDots({
  value,
  element,
}: Readonly<{ value: number; element: string }>) {
  const dots = Math.max(0, Math.min(value, 8));
  return (
    <span className={styles.dotGroup} aria-hidden="true">
      {Array.from({ length: dots }, (_, index) => (
        <span key={index} className={styles.dot} data-element={element} />
      ))}
    </span>
  );
}

function ElementPanel({
  facts,
  balanceTexts,
  selection,
  anchorId,
}: Readonly<{
  facts: BaziCoreFacts;
  balanceTexts: ReadonlyMap<string, string>;
  selection: PillarSelection;
  anchorId?: string;
}>) {
  const inventory = facts.element_inventory;
  if (!inventory) return null;

  const elements = Array.from(
    new Set([
      ...inventory.visible_stem_branch_counts.map((item) => item.element),
      ...inventory.hidden_stem_occurrence_counts.map((item) => item.element),
    ]),
  );
  if (elements.length === 0) return null;

  return (
    <section className={styles.panel} aria-label="五行盘点" id={anchorId}>
      <div className={styles.sectionHeading}>
        <h4>五行盘点</h4>
        <p>只展示服务端返回的可见干支计数与藏干出现次数，不做主气结论。</p>
      </div>
      <ul className={styles.elementRows}>
        {elements.map((element) => {
          const visible = inventory.visible_stem_branch_counts.find(
            (item) => item.element === element,
          )?.value;
          const hidden = inventory.hidden_stem_occurrence_counts.find(
            (item) => item.element === element,
          )?.value;
          const highlighted = Boolean(selection?.elements.includes(element));
          const balanceText = balanceTexts.get(element);
          return (
            <li
              key={element}
              className={styles.elementRow}
              data-fact-highlight={highlighted ? "true" : undefined}
            >
              <span className={styles.elementName} data-element={element}>
                <FactElementMark element={element} selection={selection} />
              </span>
              {balanceText ? (
                <span className={styles.elementText}>{balanceText}</span>
              ) : null}
              <span className={styles.elementCounts}>
                <span className={styles.elementCount}>
                  明 {visible ?? "未返回"}
                  {typeof visible === "number" ? (
                    <ElementDots value={visible} element={element} />
                  ) : null}
                </span>
                <span className={styles.elementCount}>
                  藏 {hidden ?? "未返回"}
                  {typeof hidden === "number" ? (
                    <ElementDots value={hidden} element={element} />
                  ) : null}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
      <p className={styles.footnote}>{inventory.scope}</p>
      <div className={styles.tableViewport}>
        <table className={styles.factTable}>
          <caption>五行计数</caption>
          <thead>
            <tr>
              <th scope="col">五行</th>
              <th scope="col">可见干支计数</th>
              <th scope="col">藏干出现次数</th>
            </tr>
          </thead>
          <tbody>
            {elements.map((element) => (
              <tr key={`count-${element}`}>
                <th scope="row">
                  <FactElementMark element={element} selection={selection} />
                </th>
                <td>
                  {inventory.visible_stem_branch_counts.find(
                    (item) => item.element === element,
                  )?.value ?? "未返回"}
                </td>
                <td>
                  {inventory.hidden_stem_occurrence_counts.find(
                    (item) => item.element === element,
                  )?.value ?? "未返回"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* ---------- M5–M7 候选与证据（evidence_only / candidate_only，零断语） ---------- */

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatRecordValue(value: unknown, depth = 0): string {
  if (value === null || value === undefined) return "未返回";
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.length > 0
      ? value.map((item) => formatRecordValue(item, depth + 1)).join("；")
      : "0 项";
  }
  if (depth >= 2) return "已返回结构";
  return Object.entries(value)
    .map(([key, item]) => `${key}：${formatRecordValue(item, depth + 1)}`)
    .join("；");
}

function StrengthPanel({
  strength,
  evidenceBadge,
  anchorId,
}: Readonly<{
  strength: BaziInterpretiveCandidates["strength"];
  evidenceBadge: ReactNode;
  anchorId?: string;
}>) {
  const counts = strength.all_element_occurrences
    .map((item) => `${ELEMENT_LABELS[item.element] ?? item.element} ${item.value}`)
    .join("、");
  const unresolved = strength.month_order_adjudication.unresolved_checks;
  return (
    <section className={styles.panel} aria-label="旺衰证据" id={anchorId}>
      <div className={styles.sectionHeading}>
        <h4>旺衰证据</h4>
        <p>只列证据与出处，不合成评分、不给强弱档位。</p>
      </div>
      <p className={styles.seasonalLine}>
        月令状态：<strong>{strength.seasonal_state}</strong>
        {evidenceBadge}
      </p>
      <ul className={styles.evidenceCountList}>
        <li>同类 {strength.same_element_occurrences} 见</li>
        <li>
          生扶（{ELEMENT_LABELS[strength.resource_element] ?? strength.resource_element}）
          {strength.resource_occurrences} 见
        </li>
      </ul>
      {counts ? <p className={styles.footnote}>盘面五行出现：{counts}</p> : null}
      <dl className={styles.metaList}>
        <div>
          <dt>未裁定边界</dt>
          <dd>
            {strength.boundary}
            {unresolved.length > 0 ? (
              <span className={styles.termDef}>
                待裁定：{unresolved.join("、")}
              </span>
            ) : null}
          </dd>
        </div>
      </dl>
    </section>
  );
}

function StructurePanel({
  structure,
  anchorId,
}: Readonly<{
  structure: BaziInterpretiveCandidates["structure"];
  anchorId?: string;
}>) {
  return (
    <section className={styles.panel} aria-label="格局候选" id={anchorId}>
      <div className={styles.sectionHeading}>
        <h4>格局候选</h4>
        <p>候选，待裁定；不渲染成已确定的格局名。</p>
      </div>
      <ul className={styles.plainList}>
        <li>
          月令主气 {structure.month_main_qi} · {structure.month_main_qi_ten_god}
        </li>
        <li>{structure.main_qi_visible ? "主气已透干" : "主气未透干"}</li>
        <li>
          可见位置：
          {structure.visible_positions
            .map((position) => POSITION_LABELS[position] ?? position)
            .join("、") || "无"}
        </li>
      </ul>
      <p className={styles.footnote}>{structure.boundary}</p>
    </section>
  );
}

function CombinationPanel({
  candidates,
}: Readonly<{
  candidates: BaziInterpretiveCandidates;
}>) {
  const fat = candidates.following_and_transformation;
  const tools = candidates.reasoning_tools ?? null;
  const toolEntries = tools ? Object.entries(tools) : [];
  const hasMechanical = candidates.salience_signals.length > 0 || toolEntries.length > 0;

  return (
    <section className={styles.panel} aria-label="合化候选">
      <div className={styles.sectionHeading}>
        <h4>合化候选</h4>
        <p>每条待古法裁定；不升级为合化或从格结论。</p>
      </div>
      <ul className={styles.plainList}>
        <li>
          天干合化候选 {fat.stem_combination_candidates.length} 项 · 地支成局候选{" "}
          {fat.branch_formation_candidates.length} 项
        </li>
        {fat.stem_combination_candidates.map((item, index) => (
          <li key={`stem-${index}`}>
            与{POSITION_LABELS[item.with_position] ?? item.with_position}
            {item.stems.join("")}：候选化
            {ELEMENT_LABELS[item.candidate_element] ?? item.candidate_element}
            （待古法裁定）
          </li>
        ))}
        {fat.branch_formation_candidates.map((item, index) => (
          <li key={`branch-${index}`}>
            {item.relation_type}：{item.branches.join("、")}（
            {item.positions
              .map((position) => POSITION_LABELS[position] ?? position)
              .join("、")}
            ；待古法裁定）
          </li>
        ))}
      </ul>
      <p className={styles.footnote}>{fat.boundary}</p>
      {hasMechanical ? (
        <details className={styles.foldBlock}>
          <summary>更多机械候选</summary>
          <div className={styles.mechanicalBody}>
            {candidates.salience_signals.map((signal) => (
              <div key={signal.signal_id} className={styles.mechanicalItem}>
                <p className={styles.mechanicalTitle}>
                  {signal.signal_id} · 机械候选（未裁定）
                </p>
                {isPlainRecord(signal.basis) && Object.keys(signal.basis).length > 0 ? (
                  <p className={styles.mechanicalRaw}>{formatRecordValue(signal.basis)}</p>
                ) : null}
                <p className={styles.footnote}>{signal.boundary}</p>
              </div>
            ))}
            {toolEntries.map(([key, tool]) => (
              <div key={key} className={styles.mechanicalItem}>
                <p className={styles.mechanicalTitle}>{key} · 机械投影（原值）</p>
                <p className={styles.mechanicalRaw}>{formatRecordValue(tool.output)}</p>
                {tool.caveats?.length ? (
                  <ul className={styles.plainList}>
                    {tool.caveats.map((caveat, index) => (
                      <li key={`${key}-caveat-${index}`}>{caveat}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ))}
          </div>
        </details>
      ) : null}
    </section>
  );
}

/* ---------- M10 神煞明细 ---------- */

function ShenshaPanel({
  aux,
  anchorId,
}: Readonly<{
  aux: NonNullable<BaziCoreFacts["shensha_auxiliary"]>;
  anchorId?: string;
}>) {
  if (aux.calculated_items.length === 0 && aux.evaluated_rules.length === 0) {
    return null;
  }
  return (
    <section className={styles.panel} aria-label="神煞明细" id={anchorId}>
      <div className={styles.sectionHeading}>
        <h4>神煞</h4>
        <p>辅助事实，只作中性标注；不覆盖主规则。</p>
      </div>
      {aux.calculated_items.length > 0 ? (
        <ul className={styles.plainList}>
          {aux.calculated_items.map((item) => (
            <li key={item.item_id}>
              <span className={styles.shenshaChip}>{item.name}</span>
              {" 目标支 "}
              {item.target_branch}
              {item.anchor_positions.length > 0
                ? ` · 依${item.anchor_positions
                    .map((position) => POSITION_LABELS[position] ?? position)
                    .join("、")}（${item.anchor_branches.join("、")}）起`
                : null}
              {" · "}
              {item.matched_positions.length > 0
                ? `落${item.matched_positions
                    .map((position) => POSITION_LABELS[position] ?? position)
                    .join("、")}`
                : "本命未命中"}
            </li>
          ))}
        </ul>
      ) : null}
      {aux.evaluated_rules.length > 0 ? (
        <details className={styles.foldBlock}>
          <summary>判定过程</summary>
          <ul className={styles.plainList}>
            {aux.evaluated_rules.map((rule, index) => (
              <li key={`${rule.rule_id}-${index}`}>
                {rule.name}：依
                {POSITION_LABELS[rule.anchor_position] ?? rule.anchor_position}（
                {rule.anchor_branch}）对照 {rule.target_branch}，
                {rule.matched ? "命中" : "未命中"}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      <p className={styles.footnote}>
        {aux.boundary}
        {aux.cannot_override.length > 0
          ? `；不可覆盖：${aux.cannot_override.join("、")}`
          : null}
      </p>
    </section>
  );
}

/* ---------- M11 免费基础摘要（机械投影，只引用本页已渲染字段） ---------- */

function FreeSummary({
  facts,
  includeSeasonalState,
}: Readonly<{ facts: BaziCoreFacts; includeSeasonalState: boolean }>) {
  const clauses: string[] = [];
  if (facts.day_master) {
    clauses.push(
      `日主${facts.day_master.stem}${ELEMENT_LABELS[facts.day_master.element] ?? ""}（${facts.day_master.polarity}）`,
    );
  }
  if (facts.month_command) {
    clauses.push(
      `生于${facts.month_command.label}，主气${facts.month_command.main_qi}`,
    );
  }
  // M11 只允许引用本页已渲染字段：B 档不渲染旺衰证据块时，摘要同步去掉该子句。
  const seasonal = includeSeasonalState
    ? facts.interpretive_candidates?.strength.seasonal_state
    : null;
  if (seasonal) clauses.push(`月令状态${seasonal}（有据）`);
  if (facts.element_inventory) clauses.push("五行分布见上");
  const cycleCount = facts.luck_cycles?.cycles.length ?? 0;
  if (cycleCount > 0) clauses.push(`大运 ${cycleCount} 步已列`);
  if (clauses.length === 0) return null;
  return (
    <section className={styles.panel} aria-label="基础摘要">
      <div className={styles.sectionHeading}>
        <h4>基础摘要</h4>
      </div>
      <p className={styles.freeSummary}>{clauses.join("；")}。</p>
    </section>
  );
}

function deepReadQuotes(facts: BaziCoreFacts | null): readonly string[] {
  if (!facts) return [];
  const quotes: string[] = [];
  if (facts.day_master) {
    quotes.push(
      `日主${facts.day_master.stem}${ELEMENT_LABELS[facts.day_master.element] ?? ""}（${facts.day_master.polarity}）`,
    );
  }
  if (facts.month_command?.label) quotes.push(facts.month_command.label);
  const cycleCount = facts.luck_cycles?.cycles.length ?? 0;
  if (cycleCount > 0) quotes.push(`大运 ${cycleCount} 步已列`);
  return quotes;
}

/* ---------- M12 古籍命中抽屉（§19.1 / §21.3） ---------- */

function readablePredicateAudit(value: string): string {
  return PREDICATE_AUDIT_LABELS[value] ?? value;
}

type ResolvedBaziEvidence = Readonly<{
  pattern: BaziSourcePattern;
  item: ReadingEvidence;
  citations: ReadonlyArray<VerifiedExactCitation>;
}>;

function isNonEmptyText(value: string | null | undefined): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function formatPublicEvidenceSource(
  sourceTitle: string,
  locator: string,
): { title: string; locator: string; isLineLocator: boolean } {
  const lineMatch = locator.match(
    /(?:^|\/)fulltext\.md#L(\d+)(?:-L?(\d+))?$/i,
  );
  if (!lineMatch) {
    return { title: sourceTitle, locator, isLineLocator: false };
  }

  const title = /^《.*》$/.test(sourceTitle)
    ? sourceTitle
    : `《${sourceTitle}》`;
  const lineLabel = lineMatch[2]
    ? `第 ${lineMatch[1]}–${lineMatch[2]} 行`
    : `第 ${lineMatch[1]} 行`;
  return { title, locator: lineLabel, isLineLocator: true };
}

function verifiedExactCitations(
  pattern: BaziSourcePattern,
  item: ReadingEvidence,
): ReadonlyArray<VerifiedExactCitation> | null {
  if (
    !pattern.evidence_ref ||
    item.ref !== pattern.evidence_ref ||
    item.evidence_ref !== pattern.evidence_ref ||
    item.rule_id !== pattern.rule_id ||
    item.verification_status !== "verified_exact" ||
    !isNonEmptyText(item.source_title) ||
    !isNonEmptyText(item.locator) ||
    !isNonEmptyText(item.verbatim_excerpt) ||
    !item.verbatim_citations?.length
  ) {
    return null;
  }

  const citations = item.verbatim_citations;
  if (
    !citations.every(
      (citation) =>
        citation.verification_status === "verified_exact" &&
        isNonEmptyText(citation.source_title) &&
        isNonEmptyText(citation.locator) &&
        isNonEmptyText(citation.verbatim_excerpt),
    )
  ) {
    return null;
  }

  const firstCitation = citations[0];
  if (
    firstCitation.source_title !== item.source_title ||
    firstCitation.locator !== item.locator ||
    firstCitation.verbatim_excerpt !== item.verbatim_excerpt
  ) {
    return null;
  }

  return citations;
}

function resolveBaziEvidence(
  patterns: ReadonlyArray<BaziSourcePattern>,
  evidence: ReadonlyArray<ReadingEvidence>,
): ReadonlyArray<ResolvedBaziEvidence> {
  return patterns
    .map((pattern) => {
      if (!pattern.evidence_ref) return null;
      const item = evidence.find((candidate) => candidate.ref === pattern.evidence_ref);
      if (!item) return null;
      const citations = verifiedExactCitations(pattern, item);
      return citations ? { pattern, item, citations } : null;
    })
    .filter((item): item is ResolvedBaziEvidence => item !== null);
}

type EvidenceEdge = Readonly<{
  key: string;
  d: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}>;

/**
 * §21.3 第三级：把每条命中条件与可回溯出处画成一条链路。
 * 连线是量测后绘制的三次贝塞尔，纯装饰（aria-hidden，无动效、无发光、无渐变）；
 * 节点内容全部是真实可选中文本；`fact_paths` 按 §19.1 只进 title，不进正文。
 */
function BaziEvidenceGraph({
  citations,
  pattern,
}: Readonly<{
  citations: ReadonlyArray<VerifiedExactCitation>;
  pattern: BaziSourcePattern;
}>) {
  const groupId = useId();
  const factsLabelId = `${groupId}-facts`;
  const sourceLabelId = `${groupId}-source`;

  const canvasRef = useRef<HTMLDivElement | null>(null);
  const factRefs = useRef<Array<HTMLLIElement | null>>([]);
  const sourceRef = useRef<HTMLDivElement | null>(null);
  const [edges, setEdges] = useState<ReadonlyArray<EvidenceEdge>>([]);
  const [canvasSize, setCanvasSize] = useState<Readonly<{ w: number; h: number }>>({
    w: 0,
    h: 0,
  });

  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    const source = sourceRef.current;
    if (!canvas || !source) return;

    const measure = () => {
      const canvasBox = canvas.getBoundingClientRect();
      const sourceBox = source.getBoundingClientRect();
      if (canvasBox.width === 0 || canvasBox.height === 0) {
        setEdges([]);
        return;
      }

      const targetX = sourceBox.left - canvasBox.left;
      const targetY = sourceBox.top - canvasBox.top + sourceBox.height / 2;

      const next: EvidenceEdge[] = [];
      factRefs.current.forEach((node, index) => {
        if (!node) return;
        const box = node.getBoundingClientRect();
        const x1 = box.right - canvasBox.left;
        const y1 = box.top - canvasBox.top + box.height / 2;
        // 节点与出处仍在同一列（窄屏堆叠）时不画线
        if (targetX - x1 < 16) return;
        const bend = (targetX - x1) * 0.55;
        next.push({
          key: `${index}`,
          d: `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${targetX - bend} ${targetY}, ${targetX} ${targetY}`,
          x1,
          y1,
          x2: targetX,
          y2: targetY,
        });
      });

      setCanvasSize({ w: canvasBox.width, h: canvasBox.height });
      setEdges(next);
    };

    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [citations, pattern]);

  return (
    <div
      aria-label={`${pattern.title}命中链路`}
      className={styles.evidenceGraph}
      role="group"
    >
      <div className={styles.evidenceGraphCanvas} ref={canvasRef}>
        {edges.length > 0 ? (
          <svg
            aria-hidden="true"
            className={styles.evidenceGraphEdges}
            focusable="false"
            viewBox={`0 0 ${canvasSize.w} ${canvasSize.h}`}
          >
            {edges.map((edge) => (
              <g key={edge.key}>
                <path className={styles.evidenceGraphEdge} d={edge.d} />
                <circle className={styles.evidenceGraphDot} cx={edge.x1} cy={edge.y1} r="2.5" />
              </g>
            ))}
            <circle
              className={styles.evidenceGraphDotTarget}
              cx={edges[0].x2}
              cy={edges[0].y2}
              r="3"
            />
          </svg>
        ) : null}

        <dl className={styles.evidenceGraphColumns}>
          <div className={styles.evidenceGraphFacts}>
            <dt id={factsLabelId}>为什么适用于这张盘</dt>
            <dd>
              <ul aria-labelledby={factsLabelId} className={styles.evidenceGraphNodes}>
                {pattern.predicate_audit.map((audit, index) => (
                  <li
                    aria-label={`适用条件 ${index + 1}`}
                    className={styles.evidenceGraphNode}
                    key={`${audit}-${index}`}
                    ref={(node) => {
                      factRefs.current[index] = node;
                    }}
                    title={pattern.fact_paths[index] ?? undefined}
                  >
                    {readablePredicateAudit(audit)}
                  </li>
                ))}
              </ul>
            </dd>
          </div>
          <div className={styles.evidenceGraphSource}>
            <dt id={sourceLabelId}>可回溯出处</dt>
            <dd>
              <div
                aria-labelledby={sourceLabelId}
                className={styles.evidenceGraphSourceNode}
                ref={sourceRef}
                role="group"
              >
                <ul className={styles.evidenceSources}>
                  {citations.map((citation, index) => {
                    const publicSource = formatPublicEvidenceSource(
                      citation.source_title,
                      citation.locator,
                    );
                    return (
                      <li key={`${citation.source_title}-${citation.locator}-${index}`}>
                        <span>{publicSource.title}</span>
                        {" · "}
                        <span>{publicSource.locator}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}

function patternTouchesPillar(
  pattern: BaziSourcePattern,
  pillar: PillarId | null,
): boolean {
  if (!pillar) return false;
  return (pattern.fact_paths ?? []).some(
    (path) => resolvePillarForFactPath(path) === pillar,
  );
}

function patternMatchesRuleId(
  pattern: BaziSourcePattern,
  ruleId: string | null,
): boolean {
  if (!ruleId) return false;
  return pattern.rule_id === ruleId || ruleId.endsWith(`#${pattern.rule_id}`);
}

function BaziEvidenceDrawer({
  patterns,
  evidence,
  open,
  onOpenChange,
  focusPillar,
  focusRuleId,
  anchorId,
}: Readonly<{
  patterns: ReadonlyArray<BaziSourcePattern>;
  evidence: ReadonlyArray<ReadingEvidence>;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  focusPillar: PillarId | null;
  focusRuleId: string | null;
  anchorId?: string;
}>) {
  const resolved = resolveBaziEvidence(patterns, evidence);
  const drawerRef = useRef<HTMLDetailsElement | null>(null);

  useLayoutEffect(() => {
    if (!open || (!focusPillar && !focusRuleId)) return;
    const node = drawerRef.current;
    if (typeof node?.scrollIntoView === "function") {
      node.scrollIntoView({ block: "nearest" });
    }
  }, [open, focusPillar, focusRuleId]);

  if (resolved.length === 0) return null;

  return (
    <details
      ref={drawerRef}
      className={styles.evidenceDrawer}
      id={anchorId}
      open={open}
      onToggle={(event) => {
        const next = event.currentTarget.open;
        if (next !== open) onOpenChange(next);
      }}
    >
      <ChapterIndex index="06" />
      <summary className={styles.evidenceSummary}>
        命中古法 {resolved.length} 条 · 可核验
      </summary>
      <div className={styles.evidenceList}>
        {resolved.map(({ pattern, citations }) => (
          <article
            className={styles.evidenceItem}
            data-focused={
              patternTouchesPillar(pattern, focusPillar) ||
              patternMatchesRuleId(pattern, focusRuleId)
                ? "true"
                : undefined
            }
            key={pattern.evidence_ref}
          >
            <h5>{pattern.title}</h5>
            <section className={styles.evidenceQuotes} aria-label={`${pattern.title}原文`}>
              <h6>原文</h6>
              {citations.map((citation, index) => (
                <blockquote
                  className={styles.evidenceQuote}
                  key={`${citation.source_title}-${citation.locator}-${index}`}
                >
                  {citation.verbatim_excerpt}
                </blockquote>
              ))}
            </section>
            <BaziEvidenceGraph
              citations={citations}
              pattern={pattern}
            />
            <p>只呈现条件命中，不作断语。</p>
          </article>
        ))}
      </div>
    </details>
  );
}

/* ---------- M9 时间层模块（GAP-BZ-01 数据到位后的合同） ---------- */

function transitRelationLine(
  relation: Readonly<{
    relation_type: string;
    natal_position: string;
    natal_branch: string;
    transit_branch: string;
  }>,
): string {
  return `${relation.relation_type}（本命${POSITION_LABELS[relation.natal_position] ?? relation.natal_position}${relation.natal_branch} · 行运${relation.transit_branch}）`;
}

function SegmentTable({
  segments,
  selection,
}: Readonly<{
  segments: ReadonlyArray<Readonly<Record<string, unknown>>>;
  selection: PillarSelection;
}>) {
  if (segments.length === 0) return null;
  return (
    <div className={styles.tableViewport}>
      <table className={styles.factTable}>
        <caption>分段事实</caption>
        <thead>
          <tr>
            <th scope="col">开始</th>
            <th scope="col">结束</th>
            <th scope="col">干支</th>
            <th scope="col">天干十神</th>
            <th scope="col">藏干十神</th>
            <th scope="col">与本命关系</th>
          </tr>
        </thead>
        <tbody>
          {segments.map((segment, index) => {
            const ganzhi = typeof segment.ganzhi === "string" ? segment.ganzhi : null;
            const stemGod =
              typeof segment.stem_ten_god === "string" ? segment.stem_ten_god : null;
            const hiddenGods = Array.isArray(segment.branch_hidden_ten_gods)
              ? segment.branch_hidden_ten_gods.filter(
                  (item): item is { stem: string; ten_god: string } =>
                    isPlainRecord(item) &&
                    typeof item.stem === "string" &&
                    typeof item.ten_god === "string",
                )
              : [];
            const relations = Array.isArray(segment.branch_relations)
              ? segment.branch_relations.filter(
                  (item): item is {
                    relation_type: string;
                    natal_position: string;
                    natal_branch: string;
                    transit_branch: string;
                  } =>
                    isPlainRecord(item) &&
                    typeof item.relation_type === "string" &&
                    typeof item.natal_position === "string" &&
                    typeof item.natal_branch === "string" &&
                    typeof item.transit_branch === "string",
                )
              : [];
            const start =
              typeof segment.start_inclusive === "string"
                ? formatServerDateTime(segment.start_inclusive)
                : "未返回";
            const end =
              typeof segment.end_exclusive === "string"
                ? formatServerDateTime(segment.end_exclusive)
                : "未返回";
            return (
              <tr key={`${ganzhi ?? "segment"}-${index}`}>
                <td>{start}</td>
                <td>{end}</td>
                <td>
                  {ganzhi ? (
                    <>
                      <FactMark value={ganzhi.slice(0, 1)} selection={selection} />
                      <FactMark value={ganzhi.slice(1, 2)} selection={selection} />
                    </>
                  ) : (
                    "未返回"
                  )}
                </td>
                <td>{stemGod ?? "未返回"}</td>
                <td>
                  {hiddenGods.length > 0
                    ? hiddenGods.map((item, godIndex) => (
                        <span key={`${item.stem}-${godIndex}`}>
                          {godIndex > 0 ? "；" : null}
                          <FactMark value={item.stem} selection={selection} />
                          {` · ${item.ten_god}`}
                        </span>
                      ))
                    : "无"}
                </td>
                <td>
                  {relations.length > 0
                    ? relations.map((item) => transitRelationLine(item)).join("；")
                    : "无"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function activeLuckPillar(record: Readonly<Record<string, unknown>> | null | undefined): string | null {
  return record && typeof record.pillar === "string" ? record.pillar : null;
}

function YearLayerModule({
  layer,
  selection,
}: Readonly<{
  layer: YearLayer;
  selection: PillarSelection;
}>) {
  const luckPillar = activeLuckPillar(layer.active_luck_cycle);
  return (
    <section className={styles.panel} aria-label={`流年 ${layer.year}`} data-layer-module="year">
      <div className={styles.sectionHeading}>
        <h4>
          流年 {layer.year} ·{" "}
          <FactMark value={layer.ganzhi.slice(0, 1)} selection={selection} />
          <FactMark value={layer.ganzhi.slice(1, 2)} selection={selection} />
        </h4>
        <p>流年天干十神：{layer.stem_ten_god}</p>
      </div>
      {layer.branch_relations.length > 0 ? (
        <ul className={styles.plainList}>
          {layer.branch_relations.map((relation, index) => (
            <li key={`${relation.relation_type}-${index}`}>
              {transitRelationLine(relation)}
            </li>
          ))}
        </ul>
      ) : null}
      <p className={styles.footnote}>
        本年机械候选（未裁定）：行运柱 {layer.structural_changes.transit_pillar} ·
        天干十神 {layer.structural_changes.stem_ten_god}；只列关系事实，不作断语。
      </p>
      {luckPillar ? (
        <p className={styles.footnote}>当年所在大运：{luckPillar}（大运轨已标注）</p>
      ) : null}
      {layer.ganzhi_segments.length > 0 ? (
        <details className={styles.foldBlock}>
          <summary>年内分段（{layer.ganzhi_segments.length}）</summary>
          <SegmentTable segments={layer.ganzhi_segments} selection={selection} />
        </details>
      ) : null}
    </section>
  );
}

function TemporalLayerModule({
  layer,
  selection,
}: Readonly<{
  layer: BaziTemporalLayer;
  selection: PillarSelection;
}>) {
  const granularityLabel = layer.granularity === "month" ? "流月" : "流日";
  const transits = layer.active_transits;
  const transitPillar =
    transits && typeof transits.pillar === "string" ? transits.pillar : null;
  const luckPillar = activeLuckPillar(layer.active_luck_cycle);
  return (
    <section
      className={styles.panel}
      aria-label={`${granularityLabel} ${layer.period}`}
      data-layer-module={layer.granularity}
    >
      <div className={styles.sectionHeading}>
        <h4>
          {granularityLabel} {layer.period}
        </h4>
        {layer.representative_instant ? (
          <p>代表时刻：{formatServerDateTime(layer.representative_instant)}</p>
        ) : null}
      </div>
      {transitPillar ? (
        <p className={styles.footnote}>当前行运柱：{transitPillar}</p>
      ) : null}
      {luckPillar ? (
        <p className={styles.footnote}>所在大运：{luckPillar}（大运轨已标注）</p>
      ) : null}
      <p className={styles.footnote}>
        结构变化为机械候选（未裁定），只列分段事实，不作断语。
      </p>
      <SegmentTable segments={layer.ganzhi_segments} selection={selection} />
    </section>
  );
}

/* ---------- 聚焦详情的补充事实（保持服务端事实来源） ---------- */

function collectBaziFocusExtras(
  chart: BaziChartView,
  evidenceItems: ReadonlyArray<ReadingEvidence>,
  pillar: PillarId,
): { facts: Array<{ label: string; text: string }>; sources: string[] } {
  const facts: Array<{ label: string; text: string }> = [];
  const core = chart.coreFacts;
  if (core) {
    const hidden = core.hidden_stems?.find((item) => item.position === pillar);
    if (hidden?.stems.length) {
      facts.push({ label: "藏干", text: hidden.stems.join("、") });
    }
    const stemGods =
      core.ten_gods?.heavenly_stems.filter((item) => item.position === pillar) ?? [];
    if (stemGods.length) {
      facts.push({
        label: "十神",
        text: stemGods.map((item) => `${item.stem} · ${item.ten_god}`).join("；"),
      });
    }
    const hiddenGods =
      core.ten_gods?.hidden_stems.filter((item) => item.position === pillar) ?? [];
    if (hiddenGods.length) {
      facts.push({
        label: "藏干十神",
        text: hiddenGods.map((item) => `${item.stem} · ${item.ten_god}`).join("；"),
      });
    }
    const nayin = core.nayin?.find((item) => item.position === pillar);
    if (nayin?.name) {
      facts.push({ label: "纳音", text: nayin.name });
    }
    const stage = core.twelve_growth_stages?.find((item) => item.position === pillar);
    if (stage?.stage) {
      facts.push({
        label: pillar === "day" ? "自坐地势" : "十二长生",
        text: `${stage.stem}${stage.branch}：${stage.stage}`,
      });
    }
    if (pillar === "day" && core.xunkong?.branches.length) {
      facts.push({
        label: "旬空",
        text: `${core.xunkong.xun}：${core.xunkong.branches.join("、")}`,
      });
    }
  }

  const sources: string[] = [];
  const patterns = core?.source_conditioned_patterns ?? [];
  for (const { pattern, citations } of resolveBaziEvidence(patterns, evidenceItems)) {
    if (!patternTouchesPillar(pattern, pillar)) continue;
    for (const citation of citations) {
      const publicSource = formatPublicEvidenceSource(
        citation.source_title,
        citation.locator,
      );
      const sourceSeparator = publicSource.isLineLocator ? " · " : " ";
      sources.push(
        `${pattern.title} · ${publicSource.title}${sourceSeparator}${publicSource.locator}`,
      );
    }
  }
  return { facts, sources };
}

/* ---------- 章节导航（<1024 单列时的粘性锚点，flow-spec S3 布局） ---------- */

type NavItem = Readonly<{ id: string; label: string }>;

function SectionNav({ items }: Readonly<{ items: ReadonlyArray<NavItem> }>) {
  if (items.length < 2) return null;
  return (
    <nav className={styles.sectionNav} aria-label="盘面章节">
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <a href={`#${item.id}`}>{item.label}</a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/* ---------- 组件主体 ---------- */

/**
 * Bazi S3 chart surface. The board maps only server-provided public facts;
 * it never calculates pillars, stars, or patterns, and missing structures
 * render as absent blocks (no placeholders).
 */
export function BaziChart({
  chart,
  title = "八字命盘",
  evidence = [],
  findings,
  showInterpretiveSections = true,
  onRequestLayer,
  pendingLayerId = null,
  layerError = null,
  initialLayerId = "natal",
  offer = null,
  s4Phase = "entry",
}: Readonly<{
  chart: BaziChartView;
  title?: string;
  evidence?: ReadonlyArray<ReadingEvidence>;
  findings?: unknown;
  showInterpretiveSections?: boolean;
  onRequestLayer?: (layerId: string) => void;
  pendingLayerId?: string | null;
  layerError?: string | null;
  initialLayerId?: string;
  offer?: BaziS4Offer | null;
  s4Phase?: BaziS4Phase;
}>) {
  const detailId = `bazi-focus-${useId()}`;
  const anchorBase = useId().replace(/[^a-zA-Z0-9-]/g, "");
  const facts = chart.coreFacts ?? null;

  const workspaceView = useMemo(
    () => ({
      ...buildBaziWorkspaceView(baziWorkspaceFactsFromChart(chart)),
      title,
    }),
    [chart, title],
  );

  const [selectedCellId, setSelectedCellId] = useState<string | null>(null);
  const [transientCellId, setTransientCellId] = useState<string | null>(null);
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState(false);
  const [evidenceFocusPillar, setEvidenceFocusPillar] = useState<PillarId | null>(null);
  const [evidenceFocusRuleId, setEvidenceFocusRuleId] = useState<string | null>(null);
  const [activeLayerId, setActiveLayerId] = useState<string>(initialLayerId);

  // §21.3 第 1/2 级：只统计抽屉真正会展示的、已核验的条目，标记数与抽屉计数同源。
  const pillarSourceCounts = useMemo<PillarSourceCounts | null>(() => {
    if (!showInterpretiveSections) return null;
    const patterns = facts?.source_conditioned_patterns ?? [];
    const resolved = resolveBaziEvidence(patterns, evidence);
    if (resolved.length === 0) return null;
    return countClassicalSourcesByPillar(resolved.map((item) => item.pattern));
  }, [facts, evidence, showInterpretiveSections]);

  const detail = useMemo(() => {
    if (!selectedCellId) return null;
    const extras =
      isPillarId(selectedCellId) && showInterpretiveSections
        ? collectBaziFocusExtras(chart, evidence, selectedCellId)
        : isPillarId(selectedCellId)
          ? collectBaziFocusExtras(chart, [], selectedCellId)
          : undefined;
    return resolveBaziFocusDetail(workspaceView, selectedCellId, extras);
  }, [workspaceView, selectedCellId, chart, evidence, showInterpretiveSections]);

  const activeSelectionId = selectedCellId ?? transientCellId;
  const selectedPosition = PILLAR_POSITIONS.find(
    (position) => position === activeSelectionId,
  );
  const selectedValue = selectedPosition
    ? chart.pillars?.[selectedPosition] || null
    : null;
  const selection: PillarSelection = selectedValue && selectedPosition
    ? {
      position: selectedPosition,
      stem: selectedValue.slice(0, 1),
      branch: selectedValue.slice(1, 2),
      elements: pillarElements(
        selectedValue,
        selectedPosition,
        facts?.hidden_stems,
      ),
    }
    : null;

  /* 时间层 chips 由 ViewModel time_layers 声明。
     无重新请求回调时：缺数据仍禁用并写明服务端原因。
     有回调时：流年/流月/流日可点，一次只请求一层，不在本地造盘。 */
  const layerDataAvailable: Record<string, boolean> = {
    year: Boolean(facts?.year_layers?.length),
    month: Boolean(facts?.month_layers?.length),
    day: Boolean(facts?.day_layers?.length),
  };
  const vmLayers = chart.timeLayers ?? [];
  const nativeNatal = vmLayers.some((layer) => NATAL_LAYER_IDS.has(layer.layer_id));
  const canRequestTransit = Boolean(onRequestLayer);
  const chips: LayerChip[] = vmLayers.length
    ? [
        ...(nativeNatal
          ? []
          : [{ id: "natal", label: "本命", enabled: true, reason: null }]),
        ...vmLayers.map((layer) => {
          const natal = NATAL_LAYER_IDS.has(layer.layer_id);
          const hasData = Boolean(layerDataAvailable[layer.layer_id]);
          const requestable =
            canRequestTransit && TRANSIT_LAYER_IDS.has(layer.layer_id);
          const pending = pendingLayerId === layer.layer_id;
          return {
            id: layer.layer_id,
            label: layer.label,
            enabled: natal || hasData || requestable,
            reason: pending
              ? "正在取该层盘面"
              : natal || hasData || requestable
                ? null
                : !layer.available
                  ? layer.unavailable_reason ?? "该时间层暂不可用"
                  : "该时间层数据尚未产出",
          };
        }),
      ]
    : [];
  const resolvedLayerId = chips.some(
    (chip) => chip.id === activeLayerId && chip.enabled,
  )
    ? activeLayerId
    : nativeNatal
      ? (vmLayers.find((layer) => NATAL_LAYER_IDS.has(layer.layer_id))?.layer_id ?? "natal")
      : "natal";

  function handleLayerSelect(id: string) {
    if (pendingLayerId) return;
    if (NATAL_LAYER_IDS.has(id) || layerDataAvailable[id]) {
      setActiveLayerId(id);
      return;
    }
    onRequestLayer?.(id);
  }

  const yearLayers =
    resolvedLayerId === "year" && facts?.year_layers?.length
      ? facts.year_layers
      : [];
  const monthLayers =
    resolvedLayerId === "month" && facts?.month_layers?.length
      ? facts.month_layers
      : [];
  const dayLayers =
    resolvedLayerId === "day" && facts?.day_layers?.length
      ? facts.day_layers
      : [];
  const activeLuck =
    yearLayers.length > 0
      ? activeLuckPillar(yearLayers[0].active_luck_cycle)
      : monthLayers.length > 0
        ? activeLuckPillar(monthLayers[0].active_luck_cycle)
        : dayLayers.length > 0
          ? activeLuckPillar(dayLayers[0].active_luck_cycle)
          : null;

  const strength = facts?.interpretive_candidates?.strength ?? null;
  const sourcePatterns = facts?.source_conditioned_patterns ?? [];
  const resolvedEvidence = resolveBaziEvidence(sourcePatterns, evidence);
  const seasonalPattern = strength
    ? resolvedEvidence.find(({ pattern }) =>
        patternMatchesRuleId(pattern, strength.seasonal_state_source_rule_id),
      ) ?? null
    : null;

  const balanceTexts = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of chart.secondary) {
      const match = item.key.match(/^view-model:element-balance:(\w+)$/);
      if (match) map.set(match[1], item.text);
    }
    return map;
  }, [chart.secondary]);

  const anchors: NavItem[] = [];
  const anchorId = (suffix: string) => `${anchorBase}-${suffix}`;
  if (chart.pillars) anchors.push({ id: anchorId("matrix"), label: "盘面" });
  if (facts?.day_master || facts?.month_command) {
    anchors.push({ id: anchorId("daymaster"), label: "日主月令" });
  }
  if (facts?.element_inventory) anchors.push({ id: anchorId("elements"), label: "五行" });
  if (showInterpretiveSections && strength) {
    anchors.push({ id: anchorId("strength"), label: "旺衰证据" });
    anchors.push({ id: anchorId("structure"), label: "格局候选" });
  }
  if (facts?.luck_cycles) anchors.push({ id: anchorId("luck"), label: "大运" });
  if (
    facts?.shensha_auxiliary &&
    (facts.shensha_auxiliary.calculated_items.length > 0 ||
      facts.shensha_auxiliary.evaluated_rules.length > 0)
  ) {
    anchors.push({ id: anchorId("shensha"), label: "神煞" });
  }
  if (facts?.branch_relations?.length) {
    anchors.push({ id: anchorId("relations"), label: "关系" });
  }
  const findingCards = natalFindingCards(findings);
  if (findingCards.length > 0) {
    anchors.push({ id: anchorId("findings"), label: "盘面说明" });
  }
  if (showInterpretiveSections && resolvedEvidence.length > 0) {
    anchors.push({ id: anchorId("evidence"), label: "古法命中" });
  }

  function handlePillarSelect(cellId: string | null) {
    setSelectedCellId((current) => (current === cellId ? null : cellId));
    if (
      cellId &&
      isPillarId(cellId) &&
      (pillarSourceCounts?.[cellId] ?? 0) > 0
    ) {
      setEvidenceDrawerOpen(true);
      setEvidenceFocusPillar(cellId);
      setEvidenceFocusRuleId(null);
    }
  }

  return (
    <section className={styles.workspace} aria-label="排盘工作台">
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>确定性盘面</p>
          <h3 className={styles.title}>{title}</h3>
        </div>
        {(chart.dayMaster || chart.monthCommand) ? (
          <p className={styles.headerMeta}>
            {chart.dayMaster ? `日主 ${chart.dayMaster}` : null}
            {chart.dayMaster && chart.monthCommand ? " · " : null}
            {chart.monthCommand ? `月令 ${chart.monthCommand}` : null}
          </p>
        ) : null}
      </header>

      {chips.length > 0 ? (
        <div className={styles.chipBlock}>
          <ChapterIndex index="05" />
          <TimeLayerChips
            chips={chips}
            activeId={resolvedLayerId}
            pendingId={pendingLayerId}
            onSelect={handleLayerSelect}
          />
          {layerError ? (
            <p className={styles.chipError} role="alert">
              {layerError}
            </p>
          ) : null}
        </div>
      ) : null}

      <TimeBasisBar calendar={facts?.calendar_normalization} />

      <div className={styles.stage}>
        <div className={styles.board} id={anchorId("matrix")}>
          <PillarMatrix
            chart={chart}
            selection={selection}
            selectedId={selectedCellId}
            detailId={detailId}
            onSelect={handlePillarSelect}
            onTransientChange={setTransientCellId}
            sourceCounts={pillarSourceCounts}
            transitLayers={yearLayers}
          />
          <SectionNav items={anchors} />
          {facts ? (
            <RelationArcs
              facts={facts}
              selection={selection}
              anchorId={anchorId("relations")}
            />
          ) : null}
          <FocusDetailDrawer
            id={detailId}
            detail={detail}
            onClose={() => setSelectedCellId(null)}
          />
          {facts?.luck_cycles ? (
            <LuckCycleTrack
              facts={facts.luck_cycles}
              activePillar={activeLuck}
              anchorId={anchorId("luck")}
              selection={selection}
            />
          ) : null}
        </div>

        <div className={styles.reading}>
          {yearLayers.map((layer) => (
            <YearLayerModule key={layer.year} layer={layer} selection={selection} />
          ))}
          {monthLayers.map((layer) => (
            <TemporalLayerModule key={layer.period} layer={layer} selection={selection} />
          ))}
          {dayLayers.map((layer) => (
            <TemporalLayerModule key={layer.period} layer={layer} selection={selection} />
          ))}

          <div className={styles.readingChapter}>
            <ChapterIndex index="03" />
          {facts ? (
            <DayMasterPanel
              facts={facts}
              selection={selection}
              anchorId={anchorId("daymaster")}
            />
          ) : null}
          {facts ? (
            <ElementPanel
              facts={facts}
              balanceTexts={balanceTexts}
              selection={selection}
              anchorId={anchorId("elements")}
            />
          ) : null}
          {showInterpretiveSections && strength ? (
            <StrengthPanel
              strength={strength}
              anchorId={anchorId("strength")}
              evidenceBadge={
                seasonalPattern ? (
                  <button
                    type="button"
                    className={styles.evidenceBadge}
                    onClick={() => {
                      setEvidenceDrawerOpen(true);
                      setEvidenceFocusRuleId(
                        strength.seasonal_state_source_rule_id,
                      );
                      setEvidenceFocusPillar(null);
                    }}
                  >
                    有据 · 可核验
                  </button>
                ) : (
                  <span className={styles.evidencePlain}>（有据）</span>
                )
              }
            />
          ) : null}
          </div>
          {showInterpretiveSections && facts?.interpretive_candidates ? (
            <StructurePanel
              structure={facts.interpretive_candidates.structure}
              anchorId={anchorId("structure")}
            />
          ) : null}
          {showInterpretiveSections && facts?.interpretive_candidates ? (
            <CombinationPanel candidates={facts.interpretive_candidates} />
          ) : null}
          {facts?.shensha_auxiliary ? (
            <ShenshaPanel
              aux={facts.shensha_auxiliary}
              anchorId={anchorId("shensha")}
            />
          ) : null}
          {facts ? (
            <FreeSummary
              facts={facts}
              includeSeasonalState={showInterpretiveSections}
            />
          ) : null}

          {chart.highlights.length > 0 ? (
            <section className={styles.panel} aria-label="盘面要点">
              <div className={styles.sectionHeading}>
                <h4>盘面要点</h4>
              </div>
              <ul className={styles.highlights}>
                {chart.highlights.map((highlight) => (
                  <li key={highlight.key}>
                    <strong>{highlight.label}</strong>
                    <span>{highlight.text}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {findingCards.length > 0 ? (
            <NatalFindingCards
              cards={findingCards}
              anchorId={anchorId("findings")}
            />
          ) : null}

          {showInterpretiveSections ? (
            <BaziEvidenceDrawer
              patterns={sourcePatterns}
              evidence={evidence}
              open={evidenceDrawerOpen}
              onOpenChange={setEvidenceDrawerOpen}
              focusPillar={evidenceFocusPillar}
              focusRuleId={evidenceFocusRuleId}
              anchorId={anchorId("evidence")}
            />
          ) : null}

          <BaziDeepEntry
            offer={offer}
            quotes={deepReadQuotes(facts)}
            s4Phase={s4Phase}
          />
        </div>
      </div>
    </section>
  );
}

export function BaziEmptySilhouette() {
  return (
    <div className={styles.matrixGroup} aria-hidden="true">
      <div className={styles.matrixViewport}>
        <table className={styles.matrix}>
          <thead>
            <tr>
              <td className={styles.cornerCell} />
              {PILLAR_POSITIONS.map((position) => (
                <th key={position} className={styles.pillarHead} scope="col">
                  <div className={styles.pillarCard} data-empty="true">
                    <span className={styles.pillarLabel}>{POSITION_LABELS[position]}</span>
                    <span className={styles.glyphEmpty} />
                    <span className={styles.glyphEmpty} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
        </table>
      </div>
    </div>
  );
}
