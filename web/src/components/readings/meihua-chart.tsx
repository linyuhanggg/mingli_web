"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Drawer } from "@/components/ui/drawer";
import { Status } from "@/components/ui/status";
import type { MeihuaChartViewModel, MeihuaInterpretiveCandidates } from "@/view-models/registry";

import {
  HexagramFigure,
  HexagramHeader,
  TrigramGlyph,
  hexagramLinesFromTrigrams,
} from "./hexagram-glyphs";
import {
  meihuaS5ClaimRefs,
  resolveMeihuaS5Anchors,
  type MeihuaS5Anchor,
  type MeihuaS5Claim,
  type MeihuaSlotId,
  type MeihuaUnitId,
} from "./meihua-s5-anchors";
import {
  MEIHUA_BODY_USE_STATUS,
  MEIHUA_FACTS_ONLY_CAPTION,
  MEIHUA_INTERPRETATION_STATUS,
  MEIHUA_POLARITY,
  MEIHUA_POLARITY_FOOTER,
  MEIHUA_SEASONAL_CAPTION,
  displayBoundary,
  mappedOrNull,
  seasonLabel,
  strengthStateLabel,
} from "./meihua-copy";
import { Reveal } from "@/components/motion-primitives";

import styles from "./meihua-chart.module.css";

export type { MeihuaS5Claim };

const CASTING_LABELS: Record<MeihuaChartViewModel["casting_method"], string> = {
  time: "按时间起卦",
  supplied_number: "按数字起卦",
  sound_count: "按声数起卦",
  observation: "按观察起卦",
  supplied_hexagram: "提供完整卦象",
};

const LINE_NAMES = ["", "初", "二", "三", "四", "五", "上"] as const;


const ELEMENT_TOKEN: Record<string, string> = {
  木: "wood",
  火: "fire",
  土: "earth",
  金: "metal",
  水: "water",
};

type SlotId = MeihuaSlotId;
type UnitId = MeihuaUnitId;

const SLOT_LABEL: Record<SlotId, string> = {
  primary: "本卦",
  mutual: "互卦",
  changed: "变卦",
};

const QUESTION_FOLD = 48;
const SKU_COPY = "一事一问：只深读当前这件已起之卦的体用关系与极性证据，不另起他事，也不把极性翻译成成败。";

export type MeihuaS4Offer = {
  name: string;
  coverage: string;
  priceText: string;
  refundBoundary: string;
};

export type MeihuaS4Phase = "entry" | "confirming";

function elementToken(element: string): string | undefined {
  return ELEMENT_TOKEN[element];
}

function positionLabel(position: "upper" | "lower"): string {
  return position === "upper" ? "上卦" : "下卦";
}

function plateLabel(plate: string): SlotId {
  if (plate.includes("mutual")) return "mutual";
  if (plate.includes("changed") || plate.includes("change")) return "changed";
  return "primary";
}

function plateName(plate: string): string {
  return SLOT_LABEL[plateLabel(plate)];
}

function bodyUseStatusLabel(status: string): string | null {
  return mappedOrNull(MEIHUA_BODY_USE_STATUS, status);
}

function interpretationStatusLabel(status: string): string | null {
  return mappedOrNull(MEIHUA_INTERPRETATION_STATUS, status);
}

function movingLineText(lines: ReadonlyArray<number>): string {
  return `动爻：${lines.map((line) => `${LINE_NAMES[line] ?? line}爻`).join("、")}`;
}

function isStructuredObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

const CASTING_INPUT_ORDER = [
  "year_branch_number",
  "lunar_year",
  "lunar_month",
  "lunar_day",
  "lunar_leap_month",
  "hour_branch_number",
  "number",
  "count",
  "upper_trigram",
  "lower_trigram",
  "moving_line",
] as const;

const CASTING_INPUT_LABELS: Record<(typeof CASTING_INPUT_ORDER)[number], string> = {
  year_branch_number: "年支数",
  lunar_year: "农历年",
  lunar_month: "农历月",
  lunar_day: "农历日",
  lunar_leap_month: "闰月",
  hour_branch_number: "时支数",
  number: "起卦数字",
  count: "声数",
  upper_trigram: "上卦",
  lower_trigram: "下卦",
  moving_line: "动爻",
};

type PromiseRow = {
  readonly label: string;
  readonly value: string;
};

function formatCastingInput(key: (typeof CASTING_INPUT_ORDER)[number], value: unknown): string | null {
  if (key === "lunar_leap_month") {
    return value === true ? "是" : null;
  }
  if (key === "moving_line") {
    const line = asNumber(value);
    if (line === null) return null;
    return `${LINE_NAMES[line] ?? line}爻`;
  }
  if (key === "upper_trigram" || key === "lower_trigram") return asText(value);
  const numeric = asNumber(value);
  if (numeric !== null) return String(numeric);
  return asText(value);
}

function readCastingPromise(facts: MeihuaChartViewModel["core_facts"]): ReadonlyArray<PromiseRow> | null {
  if (!facts) return null;
  const extra = facts as typeof facts & { casting?: unknown; calendar?: unknown; totals?: unknown };
  const casting = isStructuredObject(extra.casting) ? extra.casting : null;
  const calendar = isStructuredObject(extra.calendar) ? extra.calendar : null;
  const totals = isStructuredObject(extra.totals) ? extra.totals : null;
  if (!casting && !calendar && !totals) return null;

  const rows: PromiseRow[] = [];
  const inputs = isStructuredObject(casting?.inputs) ? casting.inputs : null;
  if (inputs) {
    for (const key of CASTING_INPUT_ORDER) {
      const formatted = formatCastingInput(key, inputs[key]);
      if (!formatted) continue;
      rows.push({ label: CASTING_INPUT_LABELS[key], value: formatted });
    }
  }
  if (calendar) {
    const monthGanzhi = asText(calendar.month_ganzhi);
    const monthBranch = asText(calendar.month_branch);
    const hourGanzhi = asText(calendar.hour_ganzhi);
    if (monthGanzhi) rows.push({ label: "月干支", value: monthGanzhi });
    if (monthBranch) rows.push({ label: "月支", value: monthBranch });
    if (hourGanzhi) rows.push({ label: "时干支", value: hourGanzhi });
  }
  if (totals) {
    const upper = asNumber(totals.upper);
    const lower = asNumber(totals.lower);
    const moving = asNumber(totals.moving);
    if (upper !== null) rows.push({ label: "上卦原始和", value: String(upper) });
    if (lower !== null) rows.push({ label: "下卦原始和", value: String(lower) });
    if (moving !== null) rows.push({ label: "动爻原始和", value: String(moving) });
  }
  return rows.length ? rows : null;
}

function polaritySentence(
  item: MeihuaInterpretiveCandidates["relation_candidates"][number],
): string {
  return `${plateName(item.source_plate)}${positionLabel(item.position)} ${item.actor.trigram}（${item.actor.element}）→ 体 ${item.body.trigram}（${item.body.element}）：${item.actor.element}${item.relation}${item.body.element}`;
}

function seasonalClauses(view: MeihuaChartViewModel): string[] {
  const strength = view.core_facts?.seasonal_strength;
  if (!strength) return [];
  return Object.entries(strength).flatMap(([name, value]) => {
    if (!isStructuredObject(value)) return [];
    const trigram = asText(value.trigram) ?? name;
    const state = asText(value.state);
    return state ? [`${trigram}${state}`] : [];
  });
}

function freeSummaryText(view: MeihuaChartViewModel, includeSeason: boolean): string | null {
  const parts: string[] = [`本卦${view.primary_hexagram.name}`];
  if (view.mutual_hexagram) parts.push(`互卦${view.mutual_hexagram.name}`);
  if (view.changed_hexagram) parts.push(`变卦${view.changed_hexagram.name}`);
  if (view.moving_lines.length) parts.push(movingLineText(view.moving_lines));
  if (view.body_use.relation) {
    parts.push(
      `体${view.body_use.body.trigram}${view.body_use.body.element}、用${view.body_use.use.trigram}${view.body_use.use.element}，${view.body_use.relation}`,
    );
  }
  if (includeSeason) {
    const seasons = seasonalClauses(view);
    if (seasons.length) parts.push(seasons.join("、"));
  }
  return parts.length ? `${parts.join("；")}。` : null;
}

type HexagramPayload = {
  readonly name: string;
  readonly upper_trigram: string;
  readonly lower_trigram: string;
};

function MeihuaTriad({
  view,
  highlight,
  expanded,
  onHighlight,
  onExpand,
}: Readonly<{
  view: MeihuaChartViewModel;
  highlight: UnitId | null;
  expanded: SlotId;
  onHighlight: (unit: UnitId) => void;
  onExpand: (slot: SlotId) => void;
}>) {
  const slots = useMemo(() => {
    const items: Array<{
      id: SlotId;
      hex: HexagramPayload;
      moving: ReadonlyArray<number>;
    }> = [
      { id: "primary", hex: view.primary_hexagram, moving: view.moving_lines },
    ];
    if (view.mutual_hexagram) {
      items.push({ id: "mutual", hex: view.mutual_hexagram, moving: [] });
    }
    if (view.changed_hexagram) {
      items.push({ id: "changed", hex: view.changed_hexagram, moving: [] });
    }
    return items;
  }, [view]);

  const units = slots.flatMap((slot) => [`${slot.id}-upper`, `${slot.id}-lower`] as UnitId[]);

  function focusUnit(unit: UnitId, offset: number) {
    const index = units.indexOf(unit);
    if (index < 0) return;
    const next = units[(index + offset + units.length) % units.length];
    onHighlight(next);
    document.getElementById(`meihua-unit-${next}`)?.focus();
  }

  return (
    <section className={styles.triadSection} id="meihua-s3-board" aria-labelledby="meihua-s3-board-title">
      <p aria-hidden="true" className={styles.chapterIndex}>
        01
      </p>
      <h2 id="meihua-s3-board-title" className={styles.sectionTitle}>
        盘面
      </h2>
      <div className={styles.folio}>
        <p className={styles.folioMeta}>
          <span className={styles.folioSeal}>梅花</span>
          <span>三卦</span>
        </p>
      <Reveal y={16}>
      <div
        className={styles.triad}
        data-count={slots.length}
        data-expanded={expanded}
      >
        {slots.map((slot, index) => {
          const compact = slot.id !== expanded;
          const isBodyUpper = slot.id === "primary" && view.body_use.body.position === "upper";
          const isBodyLower = slot.id === "primary" && view.body_use.body.position === "lower";
          const upperUnit: UnitId = `${slot.id}-upper`;
          const lowerUnit: UnitId = `${slot.id}-lower`;
          return (
            <article
              className={styles.slot}
              data-slot={slot.id}
              data-compact={compact ? "true" : "false"}
              key={slot.id}
            >
              <p className={styles.slotLabel}>
                {SLOT_LABEL[slot.id]}
                {slot.id === "primary" && !view.changed_hexagram ? (
                  <span className={styles.quietFact}>静卦</span>
                ) : null}
              </p>
              <HexagramHeader
                name={slot.hex.name}
                upper_trigram={slot.hex.upper_trigram}
                lower_trigram={slot.hex.lower_trigram}
              />
              <div className={styles.figureWrap}>
                <button
                  className={styles.unit}
                  data-unit={upperUnit}
                  data-active={highlight === upperUnit ? "true" : "false"}
                  data-body={isBodyUpper ? "true" : "false"}
                  id={`meihua-unit-${upperUnit}`}
                  type="button"
                  aria-label={`${SLOT_LABEL[slot.id]}${positionLabel("upper")} ${slot.hex.upper_trigram}${
                    slot.id === "primary" ? (isBodyUpper ? "，体" : "，用") : ""
                  }`}
                  onClick={() => {
                    onHighlight(upperUnit);
                    onExpand(slot.id);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
                      event.preventDefault();
                      focusUnit(upperUnit, 1);
                    }
                    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
                      event.preventDefault();
                      focusUnit(upperUnit, -1);
                    }
                  }}
                >
                  {slot.id === "primary" ? (
                    <span className={styles.seal} data-kind={isBodyUpper ? "body" : "use"}>
                      {isBodyUpper ? "体" : "用"}
                    </span>
                  ) : null}
                  <TrigramGlyph name={slot.hex.upper_trigram} size={compact ? "s" : "m"} />
                  {slot.id === "primary" ? (
                    <span
                      className={styles.element}
                      data-element={elementToken(
                        isBodyUpper ? view.body_use.body.element : view.body_use.use.element,
                      )}
                    >
                      {isBodyUpper ? view.body_use.body.element : view.body_use.use.element}
                    </span>
                  ) : (
                    <span className={styles.quietFact}>{positionLabel("upper")}</span>
                  )}
                </button>
                <HexagramFigure
                  lines={hexagramLinesFromTrigrams(
                    slot.hex.upper_trigram,
                    slot.hex.lower_trigram,
                    slot.moving,
                  )}
                  size={compact ? "s" : "m"}
                />
                <button
                  className={styles.unit}
                  data-unit={lowerUnit}
                  data-active={highlight === lowerUnit ? "true" : "false"}
                  data-body={isBodyLower ? "true" : "false"}
                  id={`meihua-unit-${lowerUnit}`}
                  type="button"
                  aria-label={`${SLOT_LABEL[slot.id]}${positionLabel("lower")} ${slot.hex.lower_trigram}${
                    slot.id === "primary" ? (isBodyLower ? "，体" : "，用") : ""
                  }`}
                  onClick={() => {
                    onHighlight(lowerUnit);
                    onExpand(slot.id);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
                      event.preventDefault();
                      focusUnit(lowerUnit, 1);
                    }
                    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
                      event.preventDefault();
                      focusUnit(lowerUnit, -1);
                    }
                  }}
                >
                  {slot.id === "primary" ? (
                    <span className={styles.seal} data-kind={isBodyLower ? "body" : "use"}>
                      {isBodyLower ? "体" : "用"}
                    </span>
                  ) : null}
                  <TrigramGlyph name={slot.hex.lower_trigram} size={compact ? "s" : "m"} />
                  {slot.id === "primary" ? (
                    <span
                      className={styles.element}
                      data-element={elementToken(
                        isBodyLower ? view.body_use.body.element : view.body_use.use.element,
                      )}
                    >
                      {isBodyLower ? view.body_use.body.element : view.body_use.use.element}
                    </span>
                  ) : (
                    <span className={styles.quietFact}>{positionLabel("lower")}</span>
                  )}
                </button>
              </div>
              {index < slots.length - 1 ? (
                <span className={styles.arrow} aria-hidden="true">
                  →
                </span>
              ) : null}
            </article>
          );
        })}
      </div>
      </Reveal>
      <table className={styles.semantic}>
        <caption>三卦语义表</caption>
        <thead>
          <tr>
            <th>卦位</th>
            <th>上卦</th>
            <th>下卦</th>
            <th>五行</th>
            <th>动爻</th>
          </tr>
        </thead>
        <tbody>
          {slots.map((slot) => (
            <tr key={`row-${slot.id}`}>
              <th scope="row">{SLOT_LABEL[slot.id]}</th>
              <td>{slot.hex.upper_trigram}</td>
              <td>{slot.hex.lower_trigram}</td>
              <td>
                {slot.id === "primary"
                  ? `体${view.body_use.body.element} / 用${view.body_use.use.element}`
                  : "—"}
              </td>
              <td>
                {slot.id === "primary" && view.moving_lines.length
                  ? movingLineText(view.moving_lines)
                  : "无"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </section>
  );
}

function VerifiableCasting({ view }: Readonly<{ view: MeihuaChartViewModel }>) {
  const rows = readCastingPromise(view.core_facts);
  if (!rows) return null;
  return (
    <div className={styles.promise}>
      <p aria-hidden="true" className={styles.chapterIndex}>
        02
      </p>
      <h3 className={styles.promiseTitle}>可核验起卦</h3>
      <dl className={styles.promiseList}>
        {rows.map((row) => (
          <div className={styles.promiseRow} key={row.label}>
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function BasisBar({ view }: Readonly<{ view: MeihuaChartViewModel }>) {
  const folded = view.question.length > QUESTION_FOLD;
  return (
    <section className={styles.basis} aria-label="起卦依据">
      {folded ? (
        <details>
          <summary>问题</summary>
          <p>{view.question}</p>
        </details>
      ) : (
        <p>
          <span className={styles.kicker}>问题</span>
          <span>{view.question}</span>
        </p>
      )}
      <p>
        <span className={styles.kicker}>起法</span>
        <span>{CASTING_LABELS[view.casting_method]}</span>
      </p>
      {view.moving_lines.length ? <p>{movingLineText(view.moving_lines)}</p> : null}
      <VerifiableCasting view={view} />
    </section>
  );
}

function BodyUseCard({ view }: Readonly<{ view: MeihuaChartViewModel }>) {
  const statusLine = bodyUseStatusLabel(view.body_use.status);
  return (
    <section className={styles.card} id="meihua-s3-body" aria-labelledby="meihua-s3-body-title">
      <p aria-hidden="true" className={styles.chapterIndex}>
        03
      </p>
      <h2 id="meihua-s3-body-title" className={styles.sectionTitle}>
        体用
      </h2>
      <div className={styles.bodyRow}>
        <p>
          体：{view.body_use.body.trigram}（{positionLabel(view.body_use.body.position)}）·{" "}
          <span data-element={elementToken(view.body_use.body.element)}>
            {view.body_use.body.element}
          </span>
          <TrigramGlyph name={view.body_use.body.trigram} />
        </p>
        <p>
          用：{view.body_use.use.trigram}（{positionLabel(view.body_use.use.position)}）·{" "}
          <span data-element={elementToken(view.body_use.use.element)}>
            {view.body_use.use.element}
          </span>
          <TrigramGlyph name={view.body_use.use.trigram} />
        </p>
      </div>
      <p className={styles.relation}>{view.body_use.relation}</p>
      {statusLine ? <p className={styles.statusLine}>{statusLine}</p> : null}
    </section>
  );
}

function SeasonalFacts({
  view,
  highlight,
}: Readonly<{
  view: MeihuaChartViewModel;
  highlight: UnitId | null;
}>) {
  const strength = view.core_facts?.seasonal_strength;
  if (!strength) return null;
  const seen = new Set<string>();
  const rows = Object.entries(strength).flatMap(([name, value]) => {
    if (!isStructuredObject(value)) return [];
    const trigram = asText(value.trigram) ?? name;
    const role =
      trigram === view.body_use.body.trigram
        ? "体"
        : trigram === view.body_use.use.trigram
          ? "用"
          : null;
    const month = asText(value.month_branch);
    const season = seasonLabel(asText(value.season));
    const state = strengthStateLabel(asText(value.state));
    const key = `${trigram}|${role ?? ""}|${month ?? ""}|${state ?? ""}`;
    if (seen.has(key)) return [];
    seen.add(key);
    return [{ trigram, role, month, season, state }];
  });
  if (!rows.length) return null;
  return (
    <section className={styles.card} id="meihua-s3-season" aria-labelledby="meihua-s3-season-title">
      <p aria-hidden="true" className={styles.chapterIndex}>
        04
      </p>
      <h2 id="meihua-s3-season-title" className={styles.sectionTitle}>
        旺衰
      </h2>
      <p className={styles.note}>{MEIHUA_SEASONAL_CAPTION}</p>
      <table className={styles.facts}>
        <caption className={styles.srOnly}>月令旺衰事实</caption>
        <thead>
          <tr>
            <th>卦</th>
            <th>月令</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const matched =
              highlight &&
              ((row.trigram === view.primary_hexagram.upper_trigram &&
                highlight.endsWith("upper") &&
                highlight.startsWith("primary")) ||
                (row.trigram === view.primary_hexagram.lower_trigram &&
                  highlight.endsWith("lower") &&
                  highlight.startsWith("primary")) ||
                (view.mutual_hexagram &&
                  ((row.trigram === view.mutual_hexagram.upper_trigram &&
                    highlight === "mutual-upper") ||
                    (row.trigram === view.mutual_hexagram.lower_trigram &&
                      highlight === "mutual-lower"))) ||
                (view.changed_hexagram &&
                  ((row.trigram === view.changed_hexagram.upper_trigram &&
                    highlight === "changed-upper") ||
                    (row.trigram === view.changed_hexagram.lower_trigram &&
                      highlight === "changed-lower"))));
            return (
              <tr data-active={matched ? "true" : "false"} key={`${row.trigram}-${row.role}-${row.month}-${row.state}`}>
                <td>
                  {row.trigram}
                  {row.role ? `（${row.role}）` : ""}
                </td>
                <td>
                  {[row.month ? `${row.month}月` : null, row.season].filter(Boolean).join(" · ") || "—"}
                </td>
                <td className={styles.stateCell}>{row.state ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function EvidenceBadge({
  pack,
  ruleId,
  sourceAnchor,
}: Readonly<{
  pack: string;
  ruleId: string;
  sourceAnchor: string;
}>) {
  const [open, setOpen] = useState(false);
  return (
    <Drawer
      open={open}
      onOpenChange={setOpen}
      title={`${ruleId} 出处`}
      description={pack}
      trigger={
        <button className={styles.evidenceBadge} type="button">
          {ruleId}
        </button>
      }
    >
      <p>{sourceAnchor}</p>
    </Drawer>
  );
}

function PolarityEvidence({
  candidates,
  interpretationStatus,
  highlight,
  polarityId,
  onHighlight,
}: Readonly<{
  candidates: MeihuaInterpretiveCandidates;
  interpretationStatus: string | null;
  highlight: UnitId | null;
  polarityId: string | null;
  onHighlight: (unit: UnitId) => void;
}>) {
  const factsOnly = interpretationStatus === "facts_only";
  const interpretationLine = factsOnly
    ? MEIHUA_FACTS_ONLY_CAPTION
    : interpretationStatusLabel(interpretationStatus ?? "");
  const extraBoundary = displayBoundary(candidates.boundary, MEIHUA_POLARITY_FOOTER);
  return (
    <section className={styles.card} id="meihua-s3-polarity" aria-labelledby="meihua-s3-polarity-title">
      <p aria-hidden="true" className={styles.chapterIndex}>
        05
      </p>
      <h2 id="meihua-s3-polarity-title" className={styles.sectionTitle}>
        古籍极性
      </h2>
      {interpretationLine ? (
        <p className={factsOnly ? styles.note : styles.statusLine}>{interpretationLine}</p>
      ) : null}
      <ul className={styles.polarityList}>
        {candidates.relation_candidates.map((item) => {
          const unit: UnitId = `${plateLabel(item.source_plate)}-${item.position}`;
          const sentence = polaritySentence(item);
          const ref = item.relation_adjudication.source_refs[0];
          const polarity = mappedOrNull(MEIHUA_POLARITY, item.relation_adjudication.source_polarity);
          const seasonalState = strengthStateLabel(item.seasonal_state);
          return (
            <li
              className={styles.polarityRow}
              data-active={highlight === unit || polarityId === item.candidate_id ? "true" : "false"}
              data-candidate={item.candidate_id}
              id={`meihua-polarity-${item.candidate_id}`}
              key={item.candidate_id}
            >
              <button
                className={styles.polarityFact}
                type="button"
                onClick={() => onHighlight(unit)}
              >
                {sentence}
              </button>
              <span className={styles.polarityChip}>
                {polarity}
                <span className={styles.adjudicated}>关系极性已裁定</span>
              </span>
              {seasonalState ? <span className={styles.quietFact}>{seasonalState}</span> : null}
              {ref ? (
                <EvidenceBadge
                  pack={ref.pack}
                  ruleId={ref.rule_id}
                  sourceAnchor={ref.source_anchor}
                />
              ) : null}
              {item.relation_adjudication.unresolved_checks.length ? (
                <details>
                  <summary>未决检查</summary>
                  <ul>
                    {item.relation_adjudication.unresolved_checks.map((check) => (
                      <li key={check}>{check}</li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </li>
          );
        })}
      </ul>
      {extraBoundary ? <p className={styles.note}>{extraBoundary}</p> : null}
      <p className={styles.note}>{MEIHUA_POLARITY_FOOTER}</p>
    </section>
  );
}

function FreeSummary({
  view,
  includeSeason,
}: Readonly<{
  view: MeihuaChartViewModel;
  includeSeason: boolean;
}>) {
  const text = freeSummaryText(view, includeSeason);
  if (!text) return null;
  return (
    <section className={styles.card} aria-label="基础摘要">
      <h2 className={styles.sectionTitle}>基础摘要</h2>
      <p className={styles.freeSummary}>{text}</p>
    </section>
  );
}

function jumpToS3(anchor: MeihuaS5Anchor) {
  const targetId = anchor.polarityId
    ? `meihua-polarity-${anchor.polarityId}`
    : `meihua-unit-${anchor.unit}`;
  const node = document.getElementById(targetId) ?? document.getElementById("meihua-s3-board");
  if (typeof node?.scrollIntoView === "function") {
    node.scrollIntoView({ block: "nearest" });
  }
  document.getElementById(`meihua-unit-${anchor.unit}`)?.focus();
}

function ReportSection({
  claims,
  view,
  onJump,
}: Readonly<{
  claims: ReadonlyArray<MeihuaS5Claim>;
  view: MeihuaChartViewModel;
  onJump: (anchor: MeihuaS5Anchor) => void;
}>) {
  const cards = claims
    .filter((claim) => claim.text.trim())
    .map((claim) => ({
      claim,
      anchors: resolveMeihuaS5Anchors(meihuaS5ClaimRefs(claim), view),
    }));
  if (!cards.length) return null;
  return (
    <section className={styles.card} id="meihua-s5-report" aria-labelledby="meihua-s5-report-title">
      <h2 id="meihua-s5-report-title" className={styles.sectionTitle}>
        报告
      </h2>
      <ul className={styles.claimList}>
        {cards.map(({ claim, anchors }) => (
          <li className={styles.claimCard} key={claim.claim_id}>
            <p>{claim.text}</p>
            {anchors.length ? (
              <div className={styles.anchorRow}>
                {anchors.map((anchor) => (
                  <button
                    className={styles.anchorJump}
                    key={`${claim.claim_id}-${anchor.unit}-${anchor.polarityId ?? "unit"}`}
                    type="button"
                    onClick={() => onJump(anchor)}
                  >
                    {anchor.label}
                  </button>
                ))}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function DeepReadEntry({
  view,
  showInterpretiveSections,
  offer,
  s4Phase,
}: Readonly<{
  view: MeihuaChartViewModel;
  showInterpretiveSections: boolean;
  offer?: MeihuaS4Offer | null;
  s4Phase?: MeihuaS4Phase;
}>) {
  if (s4Phase === "confirming") {
    return (
      <section className={styles.card} id="meihua-s4-deep" aria-labelledby="meihua-s4-deep-title">
        <h2 id="meihua-s4-deep-title" className={styles.sectionTitle}>
          深读
        </h2>
        <Status state="processing" title="确认中" description="正在等待服务端支付事实，不回显任何编号。" />
      </section>
    );
  }

  const quotes: string[] = [];
  if (view.body_use.relation) quotes.push(view.body_use.relation);
  if (showInterpretiveSections) {
    for (const item of view.core_facts?.interpretive_candidates?.relation_candidates ?? []) {
      quotes.push(polaritySentence(item));
      if (quotes.length >= 4) break;
    }
  }

  return (
    <section className={styles.card} id="meihua-s4-deep" aria-labelledby="meihua-s4-deep-title">
      <h2 id="meihua-s4-deep-title" className={styles.sectionTitle}>
        深读
      </h2>
      <p className={styles.skuCopy}>{SKU_COPY}</p>
      {quotes.length ? (
        <div>
          <p className={styles.kicker}>样例引用（已上屏事实）</p>
          <ul className={styles.quoteList}>
            {quotes.map((quote) => (
              <li key={quote}>
                <blockquote className={styles.quote}>{quote}</blockquote>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {offer ? (
        <div className={styles.offerCard}>
          <p className={styles.offerName}>{offer.name}</p>
          <p>{offer.coverage}</p>
          <p>{offer.priceText}</p>
          <p className={styles.note}>{offer.refundBoundary}</p>
          <p className={styles.note}>绑定当前这张已起之卦。未登录不会发起结账。</p>
          <Link className={styles.loginLink} href="/auth/login">
            登录后继续
          </Link>
        </div>
      ) : (
        <Status
          state="unavailable"
          title="测试期未开放"
          description="当前没有可购买的梅花深读，不会显示价格，也不会发起结账。"
        />
      )}
    </section>
  );
}

export function MeihuaS3Board({
  view,
  showInterpretiveSections,
  offer = null,
  s4Phase = "entry",
  reportClaims = [],
}: Readonly<{
  view: MeihuaChartViewModel;
  showInterpretiveSections: boolean;
  offer?: MeihuaS4Offer | null;
  s4Phase?: MeihuaS4Phase;
  reportClaims?: ReadonlyArray<MeihuaS5Claim>;
}>) {
  const [highlight, setHighlight] = useState<UnitId | null>(null);
  const [expanded, setExpanded] = useState<SlotId>("primary");
  const [polarityId, setPolarityId] = useState<string | null>(null);
  const deliverableClaims = reportClaims.filter((claim) => claim.text.trim());
  const nav = [
    { id: "meihua-s3-board", label: "盘面" },
    { id: "meihua-s3-body", label: "体用" },
    view.core_facts?.seasonal_strength ? { id: "meihua-s3-season", label: "旺衰" } : null,
    showInterpretiveSections && view.core_facts?.interpretive_candidates
      ? { id: "meihua-s3-polarity", label: "古籍极性" }
      : null,
    { id: "meihua-s4-deep", label: "深读" },
    deliverableClaims.length ? { id: "meihua-s5-report", label: "报告" } : null,
  ].filter((item): item is { id: string; label: string } => item !== null);

  function jumpFromReport(anchor: MeihuaS5Anchor) {
    setHighlight(anchor.unit);
    setExpanded(anchor.slot);
    setPolarityId(anchor.polarityId);
    jumpToS3(anchor);
  }

  return (
    <div className={styles.wrap} data-schema={view.schema_version}>
      <nav className={styles.sectionNav} aria-label="盘面章节">
        <ul>
          {nav.map((item) => (
            <li key={item.id}>
              <a href={`#${item.id}`}>{item.label}</a>
            </li>
          ))}
        </ul>
      </nav>
      <BasisBar view={view} />
      <MeihuaTriad
        view={view}
        highlight={highlight}
        expanded={expanded}
        onHighlight={(unit) => {
          setPolarityId(null);
          setHighlight(unit);
        }}
        onExpand={setExpanded}
      />
      <div className={styles.below}>
        <div className={styles.leftCol}>
          <BodyUseCard view={view} />
          <SeasonalFacts view={view} highlight={highlight} />
          <FreeSummary view={view} includeSeason={Boolean(view.core_facts?.seasonal_strength)} />
        </div>
        {showInterpretiveSections && view.core_facts?.interpretive_candidates ? (
          <PolarityEvidence
            candidates={view.core_facts.interpretive_candidates}
            interpretationStatus={view.core_facts.interpretation_status}
            highlight={highlight}
            polarityId={polarityId}
            onHighlight={(unit) => {
              setPolarityId(null);
              setHighlight(unit);
            }}
          />
        ) : null}
      </div>
      <DeepReadEntry
        view={view}
        showInterpretiveSections={showInterpretiveSections}
        offer={offer}
        s4Phase={s4Phase}
      />
      <ReportSection claims={deliverableClaims} view={view} onJump={jumpFromReport} />
    </div>
  );
}
