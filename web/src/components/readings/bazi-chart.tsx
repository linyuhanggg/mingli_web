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
  type WorkspaceCell,
  type WorkspaceLayer,
} from "@/lib/chart-workspace";

import {
  countClassicalSourcesByPillar,
  isPillarId,
  resolvePillarForFactPath,
  type PillarId,
  type PillarSourceCounts,
} from "@/lib/classical-source-markers";

import { ChartWorkspaceShell } from "./chart-workspace-shell";

import styles from "./bazi-chart.module.css";

/**
 * Focusable pillar board: roving tabindex with arrow-key movement and
 * Enter/Space activation via native button clicks.
 */
function PillarGrid({
  cells,
  selectedId,
  transientId,
  detailId,
  onSelect,
  onTransientChange,
  sourceCounts,
}: Readonly<{
  cells: WorkspaceCell[];
  selectedId: string | null;
  transientId: string | null;
  detailId: string;
  onSelect: (cellId: string | null) => void;
  onTransientChange: (cellId: string | null) => void;
  sourceCounts: PillarSourceCounts | null;
}>) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const [tabStopId, setTabStopId] = useState<string | null>(
    cells[0]?.id ?? null,
  );
  const activeTabStopId = cells.some((cell) => cell.id === tabStopId)
    ? tabStopId
    : (cells[0]?.id ?? null);

  function focusAt(index: number) {
    if (index >= 0 && index < refs.current.length) {
      setTabStopId(cells[index].id);
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
      focusAt((index + 1) % cells.length);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      focusAt((index - 1 + cells.length) % cells.length);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusAt(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusAt(cells.length - 1);
    }
  }

  const previewId = selectedId ?? transientId;
  const selectedValue = cells.find((item) => item.id === previewId)?.value;
  const selectedStem = selectedValue?.slice(0, 1);
  const selectedBranch = selectedValue?.slice(1, 2);

  return (
    <div className={styles.pillarGrid} role="group" aria-label="四柱">
      {cells.map((cell, index) => {
        const stem = cell.value?.slice(0, 1) ?? "—";
        const branch = cell.value?.slice(1, 2) ?? "";
        const sourceCount = isPillarId(cell.id) ? (sourceCounts?.[cell.id] ?? 0) : 0;
        const sourceNote = sourceCount > 0 ? `有 ${sourceCount} 条古法涉及此柱` : null;
        return (
          <button
            key={cell.id}
            type="button"
            ref={(element) => {
              refs.current[index] = element;
            }}
            className={styles.pillarCard}
            data-selected={cell.id === selectedId}
            aria-pressed={cell.id === selectedId}
            aria-controls={detailId}
            aria-expanded={cell.id === selectedId}
            tabIndex={cell.id === activeTabStopId ? 0 : -1}
            onClick={() => onSelect(cell.id)}
            onMouseEnter={() => onTransientChange(cell.id)}
            onMouseLeave={() => onTransientChange(null)}
            onFocus={() => {
              setTabStopId(cell.id);
              onTransientChange(cell.id);
            }}
            onBlur={() => onTransientChange(null)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            <span className={styles.pillarLabel}>{cell.label}</span>
            <span
              className={styles.pillarStem}
              data-fact-highlight={
                previewId && stem === selectedStem ? "true" : undefined
              }
            >
              {stem}
            </span>
            <span
              className={styles.pillarBranch}
              data-fact-highlight={
                previewId && branch && branch === selectedBranch ? "true" : undefined
              }
            >
              {branch || "—"}
            </span>
            <span className={styles.pillarFull}>{cell.value ?? "—"}</span>
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
        );
      })}
    </div>
  );
}

/**
 * Honest note for layers whose per-pillar structure the server did not return.
 * The layer may still carry a summary fact, but there is nothing to focus.
 */
function LayerNote({ layer }: Readonly<{ layer: WorkspaceLayer }>) {
  return (
    <div className={styles.layerNote}>
      <p className={styles.layerNoteTitle}>{layer.label}</p>
      {layer.summary ? (
        <p className={styles.layerNoteText}>{layer.summary}</p>
      ) : null}
      <p className={styles.layerNoteText}>
        {layer.status === "ready"
          ? "服务端已返回该时间层摘要；当前没有更多结构化事实可供展开。"
          : "服务端尚未返回该时间层的逐柱结构，此层暂无可聚焦内容。"}
      </p>
    </div>
  );
}

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

function relationCategory(relationType: string): string {
  if (/[合会]/u.test(relationType)) return "合会";
  if (/冲/u.test(relationType)) return "冲";
  if (/刑/u.test(relationType)) return "刑";
  if (/害/u.test(relationType)) return "害";
  if (/破/u.test(relationType)) return "破";
  return "其他";
}

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

function BranchRelationsPanel({
  facts,
  pillars,
  selection,
}: Readonly<{
  facts: BaziCoreFacts;
  pillars: BaziChartView["pillars"];
  selection: PillarSelection;
}>) {
  const relations = facts.branch_relations ?? [];
  if (relations.length === 0) return null;

  const pillarCells = PILLAR_POSITIONS.map((position) => {
    const value = pillars?.[position] ?? null;
    return {
      position,
      stem: value?.slice(0, 1) ?? "未返回",
      branch: value?.slice(1, 2) ?? "未返回",
    };
  });

  const relationLines = relations.flatMap((relation, relationIndex) => {
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
    <section className={styles.relationSection} aria-label="干支关系事实">
      <div className={styles.sectionHeading}>
        <h4>干支关系</h4>
        <p>天干与地支按服务端返回的柱位和关系事实展示；类别只作中性区分。</p>
      </div>
      <div className={styles.relationViewport}>
        <div className={styles.relationDiagram}>
          <div className={styles.relationRow}>
            <span className={styles.relationRowLabel}>天干</span>
            {pillarCells.map((cell) => (
              <span className={styles.relationCell} key={`stem-${cell.position}`}>
                <FactMark value={cell.stem} selection={selection} />
              </span>
            ))}
          </div>
          <svg
            className={styles.relationSvg}
            viewBox="0 0 400 80"
            preserveAspectRatio="none"
            role="img"
            aria-label="地支关系连线"
          >
            <title>地支关系连线</title>
            {relationLines.map((line) => {
              const sourceIndex = PILLAR_POSITIONS.indexOf(line.source);
              const targetIndex = PILLAR_POSITIONS.indexOf(line.target);
              return (
                <line
                  key={line.id}
                  className={styles.relationLine}
                  data-category={relationCategory(line.relationType)}
                  data-fact-highlight={line.highlighted ? "true" : undefined}
                  data-relation-type={line.relationType}
                  x1={sourceIndex * 100 + 50}
                  y1="14"
                  x2={targetIndex * 100 + 50}
                  y2="66"
                />
              );
            })}
          </svg>
          <div className={styles.relationRow}>
            <span className={styles.relationRowLabel}>地支</span>
            {pillarCells.map((cell) => (
              <span className={styles.relationCell} key={`branch-${cell.position}`}>
                <FactMark value={cell.branch} selection={selection} />
              </span>
            ))}
          </div>
        </div>
      </div>
      <div className={styles.relationTableViewport}>
        <table className={styles.relationTable}>
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
                  <td>{relation.positions.map((position) => POSITION_LABELS[position] ?? position).join("、")}</td>
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

function ElementInventoryChart({
  facts,
  selection,
}: Readonly<{
  facts: BaziCoreFacts;
  selection: PillarSelection;
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

  const maxCount = Math.max(
    1,
    ...elements.flatMap((element) => [
      inventory.visible_stem_branch_counts.find((item) => item.element === element)?.value ?? 0,
      inventory.hidden_stem_occurrence_counts.find((item) => item.element === element)?.value ?? 0,
    ]),
  );

  return (
    <section className={styles.elementSection} aria-label="五行计数事实">
      <div className={styles.sectionHeading}>
        <h4>五行计数</h4>
        <p>只展示服务端返回的可见干支计数与藏干出现次数。</p>
      </div>
      <div className={styles.elementChart}>
        {elements.map((element) => {
          const visible = inventory.visible_stem_branch_counts.find(
            (item) => item.element === element,
          )?.value;
          const hidden = inventory.hidden_stem_occurrence_counts.find(
            (item) => item.element === element,
          )?.value;
          const highlighted = Boolean(selection?.elements.includes(element));
          const count = Math.max(visible ?? 0, hidden ?? 0);
          return (
            <div
              className={styles.elementRow}
              data-fact-highlight={highlighted ? "true" : undefined}
              key={element}
            >
              <div className={styles.elementLabel}>
                <FactElementMark element={element} selection={selection} />
              </div>
              <div className={styles.elementBarTrack} aria-hidden="true">
                <span
                  className={styles.elementBar}
                  style={{ width: `${(count / maxCount) * 100}%` }}
                />
              </div>
              <span className={styles.elementCount}>
                {visible ?? "未返回"} / {hidden ?? "未返回"}
              </span>
            </div>
          );
        })}
      </div>
      <div className={styles.elementTableViewport}>
        <table className={styles.elementTable}>
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
                <td>{inventory.visible_stem_branch_counts.find((item) => item.element === element)?.value ?? "未返回"}</td>
                <td>{inventory.hidden_stem_occurrence_counts.find((item) => item.element === element)?.value ?? "未返回"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

type LuckCycles = NonNullable<BaziCoreFacts["luck_cycles"]>;

function LuckCycleSection({ facts }: Readonly<{ facts: LuckCycles }>) {
  const unavailable =
    facts.unavailable.length > 0
      ? facts.unavailable
      : facts.status === "not_calculated_missing_gender"
        ? ["缺少性别，无法计算顺逆与起运序列"]
        : [];
  const boundary = facts.boundary_term
    ? `${facts.boundary_term.name} · ${formatServerDateTime(facts.boundary_term.datetime)}`
    : "未返回";

  return (
    <section className={styles.luckSection} aria-label="大运事实">
      <div className={styles.sectionHeading}>
        <h4>大运</h4>
        <p>完整展示服务端返回的大运状态、起运口径与序列，不在浏览器补算。</p>
      </div>
      <dl className={styles.luckMeta}>
        <div>
          <dt>状态</dt>
          <dd data-status={facts.status}>
            {LUCK_STATUS_LABELS[facts.status] ?? "状态已记录"}
          </dd>
        </div>
        <div>
          <dt>顺逆</dt>
          <dd>
            {facts.direction
              ? LUCK_DIRECTION_LABELS[facts.direction] ?? "顺逆已记录"
              : "未返回"}
          </dd>
        </div>
        {facts.direction_rule ? (
          <div>
            <dt>顺逆规则</dt>
            <dd>{visiblePolicyLabel(facts.direction_rule, {})}</dd>
          </div>
        ) : null}
        {facts.start_age_rule ? (
          <div>
            <dt>起运规则</dt>
            <dd>{visiblePolicyLabel(facts.start_age_rule, {})}</dd>
          </div>
        ) : null}
        <div>
          <dt>起运岁数</dt>
          <dd>{facts.start_age_years ?? "未返回"}</dd>
        </div>
        <div>
          <dt>边界节气</dt>
          <dd>{boundary}</dd>
        </div>
        <div>
          <dt>间隔天数</dt>
          <dd>{facts.interval_days ?? "未返回"}</dd>
        </div>
        <div>
          <dt>约略起运时刻</dt>
          <dd>
            {facts.approximate_start_datetime
              ? formatServerDateTime(facts.approximate_start_datetime)
              : "未返回"}
          </dd>
        </div>
      </dl>
      <div className={styles.luckTableViewport}>
        <table className={styles.luckTable}>
          <caption>完整大运序列</caption>
          <thead>
            <tr>
              <th scope="col">序号</th>
              <th scope="col">大运</th>
              <th scope="col">起始岁数</th>
              <th scope="col">结束岁数</th>
            </tr>
          </thead>
          <tbody>
            {facts.cycles.map((cycle) => (
              <tr key={`${cycle.sequence}-${cycle.pillar}`}>
                <th scope="row">{cycle.sequence}</th>
                <td>{cycle.pillar}</td>
                <td>{cycle.start_age_years ?? "未返回"}</td>
                <td>{cycle.end_age_years ?? "未返回"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {unavailable.length > 0 ? (
        <div className={styles.unavailableFacts}>
          <h5>未能计算的项目</h5>
          <ul>
            {unavailable.map((item, index) => (
              <li key={`${item}-${index}`}>{visiblePolicyLabel(item, {})}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

const TEMPORAL_FACT_LABELS: Readonly<Record<string, string>> = {
  active_transits: "当前行运",
  structural_changes: "结构变化",
  seasonal_tiaohou_delta: "季节调候变化",
  shensha_auxiliary: "神煞辅助",
  active_luck_cycle: "当前大运",
  calendar_normalization: "历法归一化",
};

function formatRecordValue(value: unknown, depth = 0): string {
  if (value === null || value === undefined) return "未返回";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
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

function TemporalFactList({
  label,
  facts,
}: Readonly<{
  label: string;
  facts: Readonly<Record<string, unknown>> | null | undefined;
}>) {
  if (!facts) return null;
  const entries = Object.entries(facts);
  if (entries.length === 0) return null;
  return (
    <div className={styles.temporalFactBlock}>
      <h5>{label}</h5>
      <dl className={styles.temporalFactList}>
        {entries.map(([key, value]) => (
          <div key={key}>
            <dt>{TEMPORAL_FACT_LABELS[key] ?? key}</dt>
            <dd>{formatRecordValue(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function TemporalSegmentTable({
  segments,
}: Readonly<{
  segments: ReadonlyArray<Readonly<Record<string, unknown>>>;
}>) {
  if (segments.length === 0) return null;
  return (
    <div className={styles.temporalTableViewport}>
      <table className={styles.temporalTable}>
        <caption>分段事实</caption>
        <thead>
          <tr>
            <th scope="col">开始</th>
            <th scope="col">结束</th>
            <th scope="col">干支</th>
            <th scope="col">天干十神</th>
            <th scope="col">藏干十神</th>
            <th scope="col">地支关系</th>
          </tr>
        </thead>
        <tbody>
          {segments.map((segment, index) => (
            <tr key={`${String(segment.ganzhi ?? "segment")}-${index}`}>
              <td>{formatRecordValue(segment.start_inclusive)}</td>
              <td>{formatRecordValue(segment.end_exclusive)}</td>
              <td>{formatRecordValue(segment.ganzhi)}</td>
              <td>{formatRecordValue(segment.stem_ten_god)}</td>
              <td>{formatRecordValue(segment.branch_hidden_ten_gods)}</td>
              <td>{formatRecordValue(segment.branch_relations)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type BaziYearLayer = NonNullable<BaziCoreFacts["year_layers"]>[number];

function YearLayerBoard({
  layers,
  selection,
}: Readonly<{
  layers: ReadonlyArray<BaziYearLayer>;
  selection: PillarSelection;
}>) {
  if (layers.length === 0) return null;
  return (
    <section className={styles.temporalSection} aria-label="流年事实">
      <div className={styles.sectionHeading}>
        <h4>流年事实</h4>
        <p>逐年展示服务端已返回的干支、十神、关系与分段事实。</p>
      </div>
      <div className={styles.temporalTableViewport}>
        <table className={styles.temporalTable}>
          <caption>完整流年事实</caption>
          <thead>
            <tr>
              <th scope="col">年份</th>
              <th scope="col">干支</th>
              <th scope="col">天干十神</th>
              <th scope="col">藏干十神</th>
              <th scope="col">地支关系</th>
              <th scope="col">结构状态</th>
              <th scope="col">分段</th>
            </tr>
          </thead>
          <tbody>
            {layers.map((layer) => (
              <tr key={layer.year}>
                <th scope="row">{layer.year}</th>
                <td>
                  <FactMark value={layer.ganzhi.slice(0, 1)} selection={selection} />
                  <FactMark value={layer.ganzhi.slice(1, 2)} selection={selection} />
                </td>
                <td>
                  <FactMark
                    value={layer.stem_ten_god}
                    highlightValue={layer.ganzhi.slice(0, 1)}
                    selection={selection}
                  />
                </td>
                <td>
                  {layer.branch_hidden_ten_gods.map((item, index) => (
                    <span key={`${item.stem}-${index}`}>
                      {index > 0 ? "；" : null}
                      <FactMark value={item.stem} selection={selection} /> ·{" "}
                      <FactMark
                        value={item.ten_god}
                        highlightValue={item.stem}
                        selection={selection}
                      />
                    </span>
                  ))}
                </td>
                <td>
                  {layer.branch_relations.length > 0
                    ? layer.branch_relations
                        .map((item) => `${item.relation_type}（${item.natal_branch}·${item.transit_branch}）`)
                        .join("；")
                    : "未返回"}
                </td>
                <td>{layer.structural_changes.status}</td>
                <td>{layer.ganzhi_segments.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {layers.map((layer) => (
        <details className={styles.temporalDetail} key={`detail-${layer.year}`} open>
          <summary>{layer.year} {layer.ganzhi} · 分段事实</summary>
          <TemporalSegmentTable segments={layer.ganzhi_segments} />
          <div className={styles.temporalFactGrid}>
            <TemporalFactList label="当前大运" facts={layer.active_luck_cycle} />
            <TemporalFactList label="季节作用" facts={layer.seasonal_effect} />
            <TemporalFactList label="调候作用" facts={layer.tiaohou_effect} />
            <TemporalFactList label="季节调候变化" facts={layer.seasonal_tiaohou_delta} />
            <TemporalFactList label="历法归一化" facts={layer.calendar_normalization} />
          </div>
        </details>
      ))}
    </section>
  );
}

function TemporalLayerBoard({
  label,
  layers,
}: Readonly<{
  label: string;
  layers: ReadonlyArray<BaziTemporalLayer>;
}>) {
  if (layers.length === 0) return null;
  return (
    <section className={styles.temporalSection} aria-label={`${label}事实`}>
      <div className={styles.sectionHeading}>
        <h4>{label}事实</h4>
        <p>逐期展示服务端已返回的时间、分段、结构和规则轨迹事实。</p>
      </div>
      <div className={styles.temporalTableViewport}>
        <table className={styles.temporalTable}>
          <caption>{label}总览</caption>
          <thead>
            <tr>
              <th scope="col">周期</th>
              <th scope="col">年份</th>
              <th scope="col">月份</th>
              <th scope="col">日期</th>
              <th scope="col">代表时刻</th>
              <th scope="col">分段</th>
            </tr>
          </thead>
          <tbody>
            {layers.map((layer) => (
              <tr key={layer.period}>
                <th scope="row">{layer.period}</th>
                <td>{layer.year}</td>
                <td>{layer.month ?? "未返回"}</td>
                <td>{layer.date ?? "未返回"}</td>
                <td>{layer.representative_instant ?? "未返回"}</td>
                <td>{layer.ganzhi_segments.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {layers.map((layer) => (
        <details className={styles.temporalDetail} key={`detail-${layer.period}`} open>
          <summary>{layer.period} · 分段与时间层事实</summary>
          <TemporalSegmentTable segments={layer.ganzhi_segments} />
          <div className={styles.temporalFactGrid}>
            <TemporalFactList label="当前行运" facts={layer.active_transits} />
            <TemporalFactList label="结构变化" facts={layer.structural_changes} />
            <TemporalFactList label="季节调候变化" facts={layer.seasonal_tiaohou_delta} />
            <TemporalFactList label="神煞辅助" facts={layer.shensha_auxiliary} />
            <TemporalFactList label="当前大运" facts={layer.active_luck_cycle} />
            <TemporalFactList label="历法归一化" facts={layer.calendar_normalization} />
          </div>
          {layer.rule_trace.length > 0 ? (
            <div className={styles.temporalFactBlock}>
              <h5>规则轨迹</h5>
              <ul className={styles.ruleTraceList}>
                {layer.rule_trace.map((item, index) => (
                  <li key={`${String(item.rule_id ?? "rule")}-${index}`}>
                    {formatRecordValue(item)}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </details>
      ))}
    </section>
  );
}

const PREDICATE_AUDIT_LABELS: Readonly<Record<string, string>> = {
  "/day_master/stem:eq:甲": "日主天干为甲",
  "/day_master/stem:eq:丙": "日主天干为丙",
  "/day_master/stem:nonempty:()": "日主天干已返回",
  "/four_pillars/year:eq:庚辰": "年柱为庚辰",
  "/four_pillars/month:eq:丙午": "月柱为丙午",
  "/calendar_normalization/ganzhi/year:nonempty": "年柱干支已返回",
};

const TRUE_SOLAR_STATUS_LABELS: Readonly<Record<string, string>> = {
  apparent_solar_applied: "真太阳时已应用",
  longitude_mean_solar_applied: "经度平太阳时已应用",
  not_applied: "未应用真太阳时",
};

const CHANGED_PILLAR_LABELS: Readonly<Record<"year" | "month" | "day" | "hour", string>> = {
  year: "年柱",
  month: "月柱",
  day: "日柱",
  hour: "时柱",
};

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

function formatSeconds(value: number | null): string | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return `${value > 0 ? "+" : ""}${Math.round(value)} 秒`;
}

function TimeBasisFacts({
  calendar,
}: Readonly<{ calendar: BaziCalendarNormalization | null | undefined }>) {
  if (!calendar) return null;

  const rows: Array<{ label: string; value: string }> = [];
  const boundary = calendar.time_basis.boundary;

  rows.push({
    label: "采用时间",
    value: visiblePolicyLabel(calendar.time_basis.policy, TIME_BASIS_POLICY_LABELS),
  });
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
    rows.push({ label: "排盘采用时刻", value: formatServerDateTime(calendar.effective_datetime) });
  }
  rows.push({
    label: "真太阳时",
    value:
      TRUE_SOLAR_STATUS_LABELS[calendar.true_solar_time.status] ??
      "状态已记录",
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
          ? `该修正改变了${calendar.changed_pillars.map((pillar) => CHANGED_PILLAR_LABELS[pillar]).join("、")}`
          : "该修正未改变四柱",
    });
  }
  if (typeof boundary.distance_seconds === "number") {
    rows.push({ label: "边界距离", value: `${Math.round(boundary.distance_seconds)} 秒` });
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

  return (
    <section className={styles.timeBasis} aria-labelledby="bazi-time-basis-title">
      <div className={styles.sectionHeading}>
        <h4 id="bazi-time-basis-title">时间口径</h4>
        <p>只显示服务端排盘采用的时刻、修正与边界。</p>
      </div>
      <dl className={styles.timeBasisList}>
        {rows.map((row, index) => (
          <div key={`${row.label}-${index}`}>
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function BaziCandidateSection({
  candidates,
}: Readonly<{ candidates: BaziInterpretiveCandidates | null | undefined }>) {
  if (!candidates) return null;

  const strength = candidates.strength;
  const elementCounts = strength.all_element_occurrences.map(
    (item) => `${ELEMENT_LABELS[item.element] ?? item.element}${item.value}`,
  );
  const stemCandidates = candidates.following_and_transformation.stem_combination_candidates;
  const branchCandidates = candidates.following_and_transformation.branch_formation_candidates;

  return (
    <section className={styles.candidateSection} aria-labelledby="bazi-candidate-title">
      <div className={styles.sectionHeading}>
        <h4 id="bazi-candidate-title">候选事实</h4>
        <p>状态：仅呈现证据。这里列出证据与边界，不合成结论。</p>
      </div>
      <div className={styles.candidateGroups}>
        <div>
          <h5>支持性事实</h5>
          <p className={styles.candidateFactLabel}>全局强弱证据（未裁定）</p>
          <ul>
            <li>同类 {strength.same_element_occurrences} 项；生扶 {ELEMENT_LABELS[strength.resource_element] ?? strength.resource_element} {strength.resource_occurrences} 项</li>
          </ul>
        </div>
        <div>
          <h5>中性盘面事实</h5>
          <p className={styles.candidateFactLabel}>月令状态裁定</p>
          <ul>
            <li>月令状态 {strength.seasonal_state}</li>
            {elementCounts.length > 0 ? <li>元素计数：{elementCounts.join("、")}</li> : null}
          </ul>
        </div>
        <div>
          <h5>候选与待裁定</h5>
          <ul>
            <li>
              结构候选：月令主气 {candidates.structure.month_main_qi} · {candidates.structure.month_main_qi_ten_god}；主气可见：{candidates.structure.main_qi_visible ? "是" : "否"}；可见位置：{candidates.structure.visible_positions.map((position) => POSITION_LABELS[position] ?? position).join("、") || "无"}；{candidates.structure.boundary}；候选，待裁定
            </li>
            <li>
              合化 / 从格候选：天干 {stemCandidates.length} 项，地支成局 {branchCandidates.length} 项；{candidates.following_and_transformation.boundary}；候选，待裁定
            </li>
          </ul>
        </div>
      </div>
      <dl className={styles.candidateBoundary}>
        <div>
          <dt>证据边界</dt>
          <dd>{strength.boundary}</dd>
        </div>
      </dl>
    </section>
  );
}

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

function pickFirstVerifiedExactCitation(
  evidence: ReadonlyArray<ReadingEvidence>,
): { source_title: string; locator: string } | null {
  for (const item of evidence) {
    const matched = item.verbatim_citations?.find(
      (citation) =>
        citation.verification_status === "verified_exact" &&
        isNonEmptyText(citation.source_title) &&
        isNonEmptyText(citation.locator),
    );
    if (matched) {
      return {
        source_title: matched.source_title,
        locator: matched.locator,
      };
    }
    if (
      item.verification_status === "verified_exact" &&
      isNonEmptyText(item.source_title) &&
      isNonEmptyText(item.locator)
    ) {
      return {
        source_title: item.source_title,
        locator: item.locator,
      };
    }
  }
  return null;
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
 * 连线是量测后绘制的三次贝塞尔，纯装饰（aria-hidden，无动效、无发光、无渐变，
 * 符合 §3/§15/§21.6）；节点内容全部是真实可选中文本；
 * `fact_paths` 按 §19.1 只进 title，不进正文。
 * 窄屏堆叠时不绘线，节点纵向排列。
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

function BaziEvidenceDrawer({
  patterns,
  evidence,
  open,
  onOpenChange,
  focusPillar,
}: Readonly<{
  patterns: ReadonlyArray<BaziSourcePattern>;
  evidence: ReadonlyArray<ReadingEvidence>;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  focusPillar: PillarId | null;
}>) {
  const resolved = resolveBaziEvidence(patterns, evidence);
  const drawerRef = useRef<HTMLDetailsElement | null>(null);

  useLayoutEffect(() => {
    if (!open || !focusPillar) return;
    const node = drawerRef.current;
    if (typeof node?.scrollIntoView === "function") {
      node.scrollIntoView({ block: "nearest" });
    }
  }, [open, focusPillar]);

  if (resolved.length === 0) return null;

  return (
    <details
      ref={drawerRef}
      className={styles.evidenceDrawer}
      open={open}
      onToggle={(event) => {
        const next = event.currentTarget.open;
        if (next !== open) onOpenChange(next);
      }}
    >
      <summary>命中古法 {resolved.length} 条 · 可核验</summary>
      <div className={styles.evidenceList}>
        {resolved.map(({ pattern, citations }) => (
          <article
            className={styles.evidenceItem}
            data-focused={patternTouchesPillar(pattern, focusPillar) ? "true" : undefined}
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

function BaziCoreFactSummary({
  facts,
  pillars,
  selection,
  evidence,
  showInterpretiveSections,
  evidenceDrawerOpen,
  onEvidenceDrawerOpenChange,
  evidenceFocusPillar,
}: Readonly<{
  facts: BaziCoreFacts | null | undefined;
  pillars: BaziChartView["pillars"];
  selection: PillarSelection;
  evidence: ReadonlyArray<ReadingEvidence>;
  showInterpretiveSections: boolean;
  evidenceDrawerOpen: boolean;
  onEvidenceDrawerOpenChange: (open: boolean) => void;
  evidenceFocusPillar: PillarId | null;
}>) {
  if (!facts) return null;
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
  if (facts.hidden_stems) {
    rows.push({
      label: "藏干",
      content: facts.hidden_stems.map((item, index) => (
        <span key={`${item.position}-${item.branch}-${index}`}>
          {index > 0 ? "；" : null}
          {POSITION_LABELS[item.position] ?? item.position} <FactMark value={item.branch} selection={selection} />：
          <FactMarks values={item.stems} selection={selection} />
        </span>
      )),
    });
  }
  if (facts.ten_gods) {
    const tenGods = [
      ...facts.ten_gods.heavenly_stems,
      ...(facts.ten_gods.hidden_stems ?? []),
    ];
    rows.push({
      label: "十神",
      content: tenGods.map((item, index) => (
        <span key={`${item.layer}-${item.position}-${item.stem}-${index}`}>
          {index > 0 ? "；" : null}
          {item.layer === "hidden_stem" ? "藏干" : "天干"} · {POSITION_LABELS[item.position] ?? item.position}{" "}
          <FactMark value={item.stem} selection={selection} /> ·{" "}
          <FactMark
            value={item.ten_god}
            highlightValue={item.stem}
            selection={selection}
          />
        </span>
      )),
    });
  }
  if (facts.nayin) {
    rows.push({
      label: "纳音",
      content: facts.nayin.map((item, index) => (
        <span key={`${item.position}-${item.name}-${index}`}>
          {index > 0 ? "；" : null}
          {POSITION_LABELS[item.position] ?? item.position} {item.name}
        </span>
      )),
    });
  }
  if (facts.twelve_growth_stages?.length) {
    rows.push({
      label: "十二长生",
      content: (
        <>
          {facts.twelve_growth_stages
            .map((item) => {
              const place = item.position === "day"
                ? "日柱（自坐地势）"
                : (POSITION_LABELS[item.position] ?? item.position);
              return `${place} ${item.stem}${item.branch}：${item.stage}`;
            })
            .join("；")}
          <span className={styles.termDef}>该柱天干在本柱地支上的生旺状态位</span>
        </>
      ),
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
  if (facts.san_yuan) {
    rows.push({
      label: "三垣",
      content: `胎元 ${facts.san_yuan.tai_yuan} · 命宫 ${facts.san_yuan.ming_gong} · 身宫 ${facts.san_yuan.shen_gong}`,
    });
  }
  if (facts.month_command) {
    rows.push({
      label: "月令",
      content: (
        <>
          {facts.month_command.label} · 主气 <FactMark value={facts.month_command.main_qi} selection={selection} />
          （{ELEMENT_LABELS[facts.month_command.main_qi_element] ?? "五行已记录"}）
        </>
      ),
    });
  }
  if (facts.seasonal_profile) {
    rows.push({
      label: "季节",
      content: `${facts.seasonal_profile.season} · ${facts.seasonal_profile.month_qi} · ${facts.seasonal_profile.temperature} · ${facts.seasonal_profile.moisture}`,
    });
  }
  if (facts.tiaohou_markers) {
    rows.push({
      label: "调候标记",
      content: `${facts.tiaohou_markers.markers.join("、")} · ${visiblePolicyLabel(facts.tiaohou_markers.scope, TIAOHOU_SCOPE_LABELS)}`,
    });
  }
  if (facts.shensha_auxiliary) {
    rows.push({
      label: "神煞辅助",
      content: facts.shensha_auxiliary.calculated_items.length
        ? facts.shensha_auxiliary.calculated_items.map((item, index) => (
            <span key={`${item.item_id}-${index}`}>
              {index > 0 ? "；" : null}
              {item.name}（{item.matched_positions.join("、")}）
            </span>
          ))
        : "本命未命中已声明的辅助项",
    });
  }
  const sourcePatterns = facts.source_conditioned_patterns ?? [];
  const hasEvidence = resolveBaziEvidence(sourcePatterns, evidence).length > 0;
  const hasStructuredFacts = Boolean(
    facts.element_inventory || facts.branch_relations?.length || facts.luck_cycles ||
      facts.year_layers?.length || facts.month_layers?.length || facts.day_layers?.length,
  );
  if (
    !rows.length &&
    !facts.calendar_normalization &&
    !facts.interpretive_candidates &&
    !hasEvidence &&
    !hasStructuredFacts
  ) return null;
  return (
    <>
      <TimeBasisFacts calendar={facts.calendar_normalization} />
      {rows.length > 0 ? (
        <details className={styles.coreFacts} open>
          <summary>服务端已计算事实</summary>
          <dl className={styles.coreFactsList}>
            {rows.map((row) => (
              <div key={row.label}>
                <dt>{row.label}</dt>
                <dd>{row.content}</dd>
              </div>
            ))}
          </dl>
          <p className={styles.coreFactsNote}>
            这里只展示服务端已返回的计算事实、证据与候选；页面不在浏览器重新排盘，也不把候选或辅助标记升级成结论。
          </p>
        </details>
      ) : null}
      <ElementInventoryChart facts={facts} selection={selection} />
      <BranchRelationsPanel facts={facts} pillars={pillars} selection={selection} />
      {showInterpretiveSections ? (
        <BaziCandidateSection candidates={facts.interpretive_candidates} />
      ) : null}
      {showInterpretiveSections ? (
        <BaziEvidenceDrawer
          patterns={sourcePatterns}
          evidence={evidence}
          open={evidenceDrawerOpen}
          onOpenChange={onEvidenceDrawerOpenChange}
          focusPillar={evidenceFocusPillar}
        />
      ) : null}
    </>
  );
}

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

/**
 * Bazi board rendered inside the shared chart workspace shell. The board maps
 * only server-provided public facts; it never calculates pillars, stars, or
 * patterns, and missing structures render as unavailable.
 */
export function BaziChart({
  chart,
  title = "八字命盘",
  evidence = [],
  showInterpretiveSections = true,
}: Readonly<{
  chart: BaziChartView;
  title?: string;
  evidence?: ReadonlyArray<ReadingEvidence>;
  showInterpretiveSections?: boolean;
}>) {
  const detailId = `bazi-focus-${useId()}`;
  const view = useMemo(
    () => buildBaziWorkspaceView(baziWorkspaceFactsFromChart(chart)),
    [chart],
  );
  const workspaceView = useMemo(
    () => ({ ...view, title }),
    [view, title],
  );
  const [selectedCellId, setSelectedCellId] = useState<string | null>(null);
  const [transientCellId, setTransientCellId] = useState<string | null>(null);
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState(false);
  const [evidenceFocusPillar, setEvidenceFocusPillar] = useState<PillarId | null>(null);
  const firstScreenCitation = useMemo(
    () => pickFirstVerifiedExactCitation(evidence),
    [evidence],
  );
  const firstScreenPublicSource = firstScreenCitation
    ? formatPublicEvidenceSource(
        firstScreenCitation.source_title,
        firstScreenCitation.locator,
      )
    : null;

  // §21.3 第 1/2 级：只统计抽屉真正会展示的、已核验的条目，标记数与抽屉计数同源。
  const pillarSourceCounts = useMemo<PillarSourceCounts | null>(() => {
    if (!showInterpretiveSections) return null;
    const patterns = chart.coreFacts?.source_conditioned_patterns ?? [];
    const resolved = resolveBaziEvidence(patterns, evidence);
    if (resolved.length === 0) return null;
    return countClassicalSourcesByPillar(resolved.map((item) => item.pattern));
  }, [chart.coreFacts, evidence, showInterpretiveSections]);

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
  const selectedValue = workspaceView.cells.find(
    (cell) => cell.id === activeSelectionId,
  )?.value;
  const selectedPosition = PILLAR_POSITIONS.find(
    (position) => position === activeSelectionId,
  );
  const selection: PillarSelection = selectedValue && selectedPosition
    ? {
      position: selectedPosition,
      stem: selectedValue.slice(0, 1),
      branch: selectedValue.slice(1, 2),
      elements: pillarElements(
        selectedValue,
        selectedPosition,
        chart.coreFacts?.hidden_stems,
      ),
    }
    : null;

  function renderBoard(layer: WorkspaceLayer) {
    if (layer.id === "decadal") {
      return chart.coreFacts?.luck_cycles ? (
        <LuckCycleSection facts={chart.coreFacts.luck_cycles} />
      ) : (
        <LayerNote layer={layer} />
      );
    }
    if (layer.id === "yearly") {
      return chart.coreFacts?.year_layers?.length ? (
        <YearLayerBoard layers={chart.coreFacts.year_layers} selection={selection} />
      ) : (
        <LayerNote layer={layer} />
      );
    }
    if (layer.id === "monthly") {
      return chart.coreFacts?.month_layers?.length ? (
        <TemporalLayerBoard label="流月" layers={chart.coreFacts.month_layers} />
      ) : (
        <LayerNote layer={layer} />
      );
    }
    if (layer.id === "daily") {
      return chart.coreFacts?.day_layers?.length ? (
        <TemporalLayerBoard label="流日" layers={chart.coreFacts.day_layers} />
      ) : (
        <LayerNote layer={layer} />
      );
    }
    return (
      <div className={styles.board}>
        <div className={styles.brandBlock}>
          <p className={styles.brand}>八字命盘</p>
          <p className={styles.brandSub}>
            {chart.dayMaster ? `日主 ${chart.dayMaster}` : "八字本命"}
          </p>
          {chart.monthCommand ? (
            <p className={styles.brandMeta}>月令 {chart.monthCommand}</p>
          ) : null}
        </div>

        <PillarGrid
          cells={workspaceView.cells}
          selectedId={selectedCellId}
          transientId={transientCellId}
          detailId={detailId}
          onTransientChange={setTransientCellId}
          onSelect={(cellId) => {
            setSelectedCellId((current) => (current === cellId ? null : cellId));
            if (
              cellId &&
              isPillarId(cellId) &&
              (pillarSourceCounts?.[cellId] ?? 0) > 0
            ) {
              setEvidenceDrawerOpen(true);
              setEvidenceFocusPillar(cellId);
            }
          }}
          sourceCounts={pillarSourceCounts}
        />

        {firstScreenPublicSource ? (
          <figure
            className={styles.firstScreenCitation}
            data-verification-status="verified_exact"
          >
            <figcaption>
              {firstScreenPublicSource.title}
              <span>
                {firstScreenPublicSource.isLineLocator ? " · " : " "}
                {firstScreenPublicSource.locator}
              </span>
            </figcaption>
          </figure>
        ) : null}

        {workspaceView.highlights.length > 0 ? (
          <div className={styles.highlights}>
            <h4>盘面要点</h4>
            <ul>
              {workspaceView.highlights.map((highlight) => (
                <li key={highlight.id} data-tone={highlight.tone}>
                  <strong>{highlight.title}</strong>
                  <span>{highlight.body}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <BaziCoreFactSummary
          facts={chart.coreFacts}
          pillars={chart.pillars}
          selection={selection}
          evidence={evidence}
          showInterpretiveSections={showInterpretiveSections}
          evidenceDrawerOpen={evidenceDrawerOpen}
          onEvidenceDrawerOpenChange={setEvidenceDrawerOpen}
          evidenceFocusPillar={evidenceFocusPillar}
        />
      </div>
    );
  }

  return (
    <ChartWorkspaceShell
      view={workspaceView}
      renderBoard={renderBoard}
      detail={detail}
      detailId={detailId}
      onCloseDetail={() => setSelectedCellId(null)}
      boardLabel="八字盘面"
    />
  );
}
