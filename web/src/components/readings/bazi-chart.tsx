"use client";

import {
  Fragment,
  useId,
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
} from "@/view-models/registry";
import {
  baziWorkspaceFactsFromChart,
  buildBaziWorkspaceView,
  resolveBaziFocusDetail,
  type WorkspaceCell,
  type WorkspaceLayer,
} from "@/lib/chart-workspace";

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
}: Readonly<{
  cells: WorkspaceCell[];
  selectedId: string | null;
  transientId: string | null;
  detailId: string;
  onSelect: (cellId: string | null) => void;
  onTransientChange: (cellId: string | null) => void;
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
          ? "Runtime 已返回该时间层事实；当前页面先展示年度汇总，未在浏览器重新排盘。"
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

const LUCK_STATUS_LABELS: Readonly<Record<string, string>> = {
  calculated: "已计算",
  sequence_only: "仅返回序列",
  not_calculated_missing_gender: "因性别缺失未计算",
};

const LUCK_DIRECTION_LABELS: Readonly<Record<string, string>> = {
  forward: "顺行",
  reverse: "逆行",
};

const PREDICATE_AUDIT_LABELS: Readonly<Record<string, string>> = {
  "/day_master/stem:eq:甲": "日主天干为甲",
  "/day_master/stem:eq:丙": "日主天干为丙",
  "/day_master/stem:nonempty:()": "日主天干已返回",
  "/four_pillars/year:eq:庚辰": "年柱为庚辰",
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
  stem: string;
  branch: string;
}> | null;

function FactMark({
  value,
  selection,
}: Readonly<{ value: string; selection: PillarSelection }>) {
  const highlighted = Boolean(
    selection && (value === selection.stem || value === selection.branch),
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

function formatSeconds(value: number | null): string | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return `${value > 0 ? "+" : ""}${Math.round(value)} 秒`;
}

function TimeBasisFacts({
  calendar,
}: Readonly<{ calendar: BaziCalendarNormalization | null | undefined }>) {
  if (!calendar) return null;

  const rows: Array<{ label: string; value: string }> = [];
  const algorithm = calendar.time_basis.algorithm;
  const boundary = calendar.time_basis.boundary;

  rows.push({ label: "策略 / policy", value: calendar.time_basis.policy });
  if (algorithm.id) {
    rows.push({
      label: "算法 ID",
      value: algorithm.version ? `${algorithm.id} v${algorithm.version}` : algorithm.id,
    });
  }
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
    rows.push({ label: "有效时刻", value: calendar.effective_datetime });
  }
  rows.push({
    label: "真太阳时",
    value:
      TRUE_SOLAR_STATUS_LABELS[calendar.true_solar_time.status] ??
      calendar.true_solar_time.status,
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
      label: "子时换日",
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
    rows.push({ label: "晚子时", value: calendar.calendar_convention.zi_hour_policy });
  }
  const solarTerms = calendar.solar_terms;
  if (solarTerms?.previous) {
    rows.push({
      label: "前一节气",
      value: `${solarTerms.previous.name} · ${solarTerms.previous.datetime}${solarTerms.previous.is_month_boundary_jie ? " · 月界节" : ""}`,
    });
  }
  if (solarTerms?.next) {
    rows.push({
      label: "后一节气",
      value: `${solarTerms.next.name} · ${solarTerms.next.datetime}${solarTerms.next.is_month_boundary_jie ? " · 月界节" : ""}`,
    });
  }
  if (solarTerms?.month_switch_policy) {
    rows.push({ label: "换月口径", value: solarTerms.month_switch_policy });
  }

  return (
    <section className={styles.timeBasis} aria-labelledby="bazi-time-basis-title">
      <div className={styles.sectionHeading}>
        <h4 id="bazi-time-basis-title">时间口径</h4>
        <p>只显示 Runtime 返回的有效时刻、修正与边界。</p>
      </div>
      <dl className={styles.timeBasisList}>
        {rows.map((row) => (
          <div key={row.label}>
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

function BaziEvidenceDrawer({
  patterns,
  evidence,
}: Readonly<{
  patterns: ReadonlyArray<BaziSourcePattern>;
  evidence: ReadonlyArray<ReadingEvidence>;
}>) {
  const resolved = resolveBaziEvidence(patterns, evidence);

  if (resolved.length === 0) return null;

  return (
    <details className={styles.evidenceDrawer}>
      <summary>命中古法 {resolved.length} 条 · 可核验</summary>
      <div className={styles.evidenceList}>
        {resolved.map(({ pattern, citations }) => (
          <article className={styles.evidenceItem} key={pattern.evidence_ref}>
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
            <dl>
              <div>
                <dt>为什么适用于这张盘</dt>
                <dd>
                  {pattern.predicate_audit.map((audit, index) => (
                    <Fragment key={`${audit}-${index}`}>
                      {index > 0 ? "；" : null}
                      <span>{readablePredicateAudit(audit)}</span>
                    </Fragment>
                  ))}
                </dd>
              </div>
              <div>
                <dt>可回溯出处</dt>
                <dd>
                  <ul className={styles.evidenceSources}>
                    {citations.map((citation, index) => (
                      <li key={`${citation.source_title}-${citation.locator}-${index}`}>
                        <span>{citation.source_title}</span>
                        {" · "}
                        <span>{citation.locator}</span>
                      </li>
                    ))}
                  </ul>
                </dd>
              </div>
            </dl>
            <p>只呈现条件命中，不作断语。</p>
          </article>
        ))}
      </div>
    </details>
  );
}

function BaziCoreFactSummary({
  facts,
  selection,
  evidence,
}: Readonly<{
  facts: BaziCoreFacts | null | undefined;
  selection: PillarSelection;
  evidence: ReadonlyArray<ReadingEvidence>;
}>) {
  if (!facts) return null;
  const rows: Array<{ label: string; content: ReactNode }> = [];
  if (facts.day_master) {
    rows.push({
      label: "日主",
      content: (
        <>
          <FactMark value={facts.day_master.stem} selection={selection} />
          {` · ${ELEMENT_LABELS[facts.day_master.element] ?? facts.day_master.element} · ${facts.day_master.polarity}`}
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
          {item.layer === "hidden_stem" ? "藏干" : "天干"} · {POSITION_LABELS[item.position] ?? item.position} <FactMark value={item.stem} selection={selection} /> · {item.ten_god}
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
      content: facts.twelve_growth_stages
        .map(
          (item) =>
            `${POSITION_LABELS[item.position] ?? item.position} ${item.stem}${item.branch}：${item.stage}`,
        )
        .join("；"),
    });
  }
  if (facts.xunkong) {
    rows.push({
      label: "旬空",
      content: `${facts.xunkong.day_pillar} 属 ${facts.xunkong.xun} 旬：${facts.xunkong.branches.join("、")}`,
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
          （{ELEMENT_LABELS[facts.month_command.main_qi_element] ?? facts.month_command.main_qi_element}）
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
      content: `${facts.tiaohou_markers.markers.join("、")} · ${facts.tiaohou_markers.scope}`,
    });
  }
  if (facts.element_inventory) {
    rows.push({
      label: "五行计数",
      content: facts.element_inventory.visible_stem_branch_counts
        .map((item) => `${ELEMENT_LABELS[item.element] ?? item.element}${item.value}`)
        .join("、"),
    });
  }
  if (facts.branch_relations?.length) {
    rows.push({
      label: "地支关系",
      content: facts.branch_relations.map((item, index) => (
        <span key={`${item.relation_type}-${index}`}>
          {index > 0 ? "；" : null}
          {item.relation_type}（<FactMarks values={item.branches} selection={selection} />）
        </span>
      )),
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
  if (facts.luck_cycles) {
    const cycles = facts.luck_cycles.cycles.slice(0, 3).map((item) => item.pillar).join("、");
    const status = LUCK_STATUS_LABELS[facts.luck_cycles.status] ?? facts.luck_cycles.status;
    const direction = facts.luck_cycles.direction
      ? LUCK_DIRECTION_LABELS[facts.luck_cycles.direction] ?? facts.luck_cycles.direction
      : null;
    rows.push({
      label: "大运",
      content: [status, direction, cycles ? `序列 ${cycles}` : null]
        .filter((value): value is string => Boolean(value))
        .join(" · "),
    });
  }
  if (facts.year_layers?.length) {
    rows.push({
      label: "流年",
      content: facts.year_layers.map((item, index) => (
        <span key={`${item.year}-${item.ganzhi}-${index}`}>
          {index > 0 ? "；" : null}
          {item.year} {item.ganzhi} · {item.stem_ten_god} · 立春分段 {item.ganzhi_segments.length} 段 · 大运 {typeof item.active_luck_cycle.status === "string" ? LUCK_STATUS_LABELS[item.active_luck_cycle.status] ?? item.active_luck_cycle.status : "已返回"}
        </span>
      )),
    });
  }
  if (facts.month_layers?.length) {
    rows.push({
      label: "流月",
      content: facts.month_layers.map((item, index) => {
        const ganzhi = item.ganzhi_segments
          .map((segment) => (typeof segment.ganzhi === "string" ? segment.ganzhi : null))
          .filter((value): value is string => Boolean(value))
          .join("、");
        return <span key={`${item.period}-${index}`}>{index > 0 ? "；" : null}{item.period} · {ganzhi || "分段事实"} · {item.ganzhi_segments.length} 段</span>;
      }),
    });
  }
  if (facts.day_layers?.length) {
    rows.push({
      label: "流日",
      content: facts.day_layers.map((item, index) => {
        const ganzhi = item.ganzhi_segments
          .map((segment) => (typeof segment.ganzhi === "string" ? segment.ganzhi : null))
          .filter((value): value is string => Boolean(value))
          .join("、");
        return <span key={`${item.period}-${index}`}>{index > 0 ? "；" : null}{item.period} · {ganzhi || "分段事实"} · {item.ganzhi_segments.length} 段</span>;
      }),
    });
  }
  const sourcePatterns = facts.source_conditioned_patterns ?? [];
  const hasEvidence = resolveBaziEvidence(sourcePatterns, evidence).length > 0;
  if (!rows.length && !facts.calendar_normalization && !facts.interpretive_candidates && !hasEvidence) return null;
  return (
    <>
      <TimeBasisFacts calendar={facts.calendar_normalization} />
      {rows.length > 0 ? (
        <details className={styles.coreFacts} open>
          <summary>Runtime 已计算事实</summary>
          <dl className={styles.coreFactsList}>
            {rows.map((row) => (
              <div key={row.label}>
                <dt>{row.label}</dt>
                <dd>{row.content}</dd>
              </div>
            ))}
          </dl>
          <p className={styles.coreFactsNote}>
            这里只展示 Runtime 已返回的计算事实、证据与候选；页面不在浏览器重新排盘，也不把候选或辅助标记升级成结论。
          </p>
        </details>
      ) : null}
      <BaziCandidateSection candidates={facts.interpretive_candidates} />
      <BaziEvidenceDrawer
        patterns={sourcePatterns}
        evidence={evidence}
      />
    </>
  );
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
}: Readonly<{
  chart: BaziChartView;
  title?: string;
  evidence?: ReadonlyArray<ReadingEvidence>;
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

  const detail = useMemo(
    () =>
      selectedCellId
        ? resolveBaziFocusDetail(workspaceView, selectedCellId)
        : null,
    [workspaceView, selectedCellId],
  );
  const activeSelectionId = selectedCellId ?? transientCellId;
  const selectedValue = workspaceView.cells.find(
    (cell) => cell.id === activeSelectionId,
  )?.value;
  const selection: PillarSelection = selectedValue
    ? { stem: selectedValue.slice(0, 1), branch: selectedValue.slice(1, 2) }
    : null;

  function renderBoard(layer: WorkspaceLayer) {
    if (layer.id !== "natal") {
      return <LayerNote layer={layer} />;
    }
    return (
      <div className={styles.board}>
        <div className={styles.brandBlock}>
          <p className={styles.brand}>命理工具</p>
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
          onSelect={(cellId) =>
            setSelectedCellId((current) => (current === cellId ? null : cellId))
          }
        />

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
          selection={selection}
          evidence={evidence}
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
