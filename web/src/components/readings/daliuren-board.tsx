"use client";

import { useRef, useState, type KeyboardEvent } from "react";

import type { DaliurenChartViewModel } from "@/view-models/registry";

import styles from "./daliuren-board.module.css";
import { DaliurenCaliberBar } from "./daliuren-caliber-bar";
import { DaliurenHeavenEarthPlate } from "./daliuren-heaven-earth-plate";
import { DaliurenLessonMethod } from "./daliuren-lesson-method";
import { DaliurenDimensionEvidence } from "./daliuren-dimension-evidence";
import { DaliurenFreeSummary, type DaliurenS4Offer, type DaliurenS4Phase } from "./daliuren-free-summary";

export type DaliurenBoardMode = "ready" | "silhouette" | "loading";

type LessonIndex = 0 | 1 | 2 | 3;
type LessonPart = "upper" | "lower";
type StageId = DaliurenChartViewModel["transmissions"][number]["stage"];
type CellId = `lesson-${LessonIndex}-${LessonPart}` | `tx-${StageId}`;
type NavigationKey = "ArrowLeft" | "ArrowRight" | "ArrowUp" | "ArrowDown" | "Home" | "End";

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

const STAGE_LABEL: Readonly<Record<StageId, string>> = {
  initial: "初传",
  middle: "中传",
  final: "末传",
};

const VISUAL_LESSONS = [3, 2, 1, 0] as const;
const FIRST_CELL: CellId = "lesson-0-upper";
const LAST_CELL: CellId = "tx-final";
const NAVIGATION_KEYS: ReadonlySet<string> = new Set([
  "ArrowLeft",
  "ArrowRight",
  "ArrowUp",
  "ArrowDown",
  "Home",
  "End",
]);
const SOURCE_PACK_LABELS: Readonly<Record<string, string>> = {
  "san-shi/liuren-miben": "大六壬秘本",
};

function branchElement(value: string): string | undefined {
  return BRANCH_ELEMENTS[value];
}

function sourceLabel(pack: string, rule: string): string {
  return `${SOURCE_PACK_LABELS[pack] ?? "古籍"} ${rule}`;
}

function voidBranches(value: unknown): Set<string> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return new Set();
  const branches = (value as { branches?: unknown }).branches;
  if (!Array.isArray(branches)) return new Set();
  return new Set(
    branches.filter((item): item is string => typeof item === "string" && Boolean(item.trim())).map((item) => item.trim()),
  );
}

function isVoidCell(value: string, voids: Set<string>): boolean {
  const text = value.trim();
  if (!text || voids.size === 0) return false;
  if (voids.has(text)) return true;
  return voids.has(text.slice(-1));
}

function VoidMark() {
  return (
    <span className={styles.voidBadge} data-badge="void">
      空
    </span>
  );
}

function parseLesson(id: CellId): { index: LessonIndex; part: LessonPart } | null {
  const match = /^lesson-([0-3])-(upper|lower)$/.exec(id);
  if (!match) return null;
  return { index: Number(match[1]) as LessonIndex, part: match[2] as LessonPart };
}

const EMPTY_LESSONS: DaliurenChartViewModel["lessons"] = [
  { lesson_id: "", upper: "", lower: "" },
  { lesson_id: "", upper: "", lower: "" },
  { lesson_id: "", upper: "", lower: "" },
  { lesson_id: "", upper: "", lower: "" },
];

const EMPTY_TRANSMISSIONS: DaliurenChartViewModel["transmissions"] = [
  { stage: "initial", branch: "", general: "" },
  { stage: "middle", branch: "", general: "" },
  { stage: "final", branch: "", general: "" },
];

function transmissionCellForBranch(
  transmissions: DaliurenChartViewModel["transmissions"],
  branch: string,
): CellId | null {
  if (!branch) return null;
  const hit = transmissions.find((row) => row.branch === branch);
  return hit ? (`tx-${hit.stage}` as CellId) : null;
}

function cellFact(
  id: CellId,
  lessons: DaliurenChartViewModel["lessons"],
  transmissions: DaliurenChartViewModel["transmissions"],
): string {
  const lesson = parseLesson(id);
  if (lesson) return lessons[lesson.index]?.[lesson.part].trim() ?? "";
  const stage = id.slice(3) as StageId;
  return transmissions.find((item) => item.stage === stage)?.branch.trim() ?? "";
}

function isNavigationKey(key: string): key is NavigationKey {
  return NAVIGATION_KEYS.has(key);
}

function neighbor(id: CellId, key: NavigationKey): CellId {
  if (key === "Home") return FIRST_CELL;
  if (key === "End") return LAST_CELL;
  const lesson = parseLesson(id);
  if (lesson) {
    const visual = VISUAL_LESSONS.indexOf(lesson.index);
    if (key === "ArrowLeft" && visual > 0) {
      return `lesson-${VISUAL_LESSONS[visual - 1]}-${lesson.part}`;
    }
    if (key === "ArrowRight" && visual < VISUAL_LESSONS.length - 1) {
      return `lesson-${VISUAL_LESSONS[visual + 1]}-${lesson.part}`;
    }
    if (key === "ArrowDown" && lesson.part === "upper") return `lesson-${lesson.index}-lower`;
    if (key === "ArrowDown" && lesson.part === "lower") return "tx-initial";
    if (key === "ArrowUp" && lesson.part === "lower") return `lesson-${lesson.index}-upper`;
    return id;
  }
  if (id === "tx-initial") {
    if (key === "ArrowDown") return "tx-middle";
    if (key === "ArrowUp") return "lesson-0-lower";
    return id;
  }
  if (id === "tx-middle") {
    if (key === "ArrowDown") return "tx-final";
    if (key === "ArrowUp") return "tx-initial";
    return id;
  }
  if (key === "ArrowUp") return "tx-middle";
  return id;
}

export function DaliurenBoard({
  view,
  mode = "ready",
  offer = null,
  s4Phase = "entry",
}: Readonly<{
  view?: DaliurenChartViewModel;
  mode?: DaliurenBoardMode;
  offer?: DaliurenS4Offer | null;
  s4Phase?: DaliurenS4Phase;
}>) {
  const [activeFact, setActiveFact] = useState<string | null>(null);
  const [rovingId, setRovingId] = useState<CellId>(FIRST_CELL);
  const cellRefs = useRef<Partial<Record<CellId, HTMLButtonElement | null>>>({});
  const lessons = view?.lessons ?? EMPTY_LESSONS;
  const transmissions = view?.transmissions ?? EMPTY_TRANSMISSIONS;
  const candidates = mode === "ready" ? (view?.core_facts?.timing_candidates ?? null) : null;
  const showTiming = Boolean(candidates && candidates.length > 0);
  const anchored = new Set(
    (candidates ?? []).map((item) => item.anchor_earth_branch).filter((item) => item.length > 0),
  );
  const voids = mode === "ready" && view?.core_facts ? voidBranches(view.core_facts.xunkong) : new Set<string>();

  function isActive(value: string): boolean {
    const fact = value.trim();
    return Boolean(fact && activeFact === fact);
  }

  function focusAndLock(id: CellId) {
    const fact = cellFact(id, lessons, transmissions);
    setRovingId(id);
    setActiveFact(fact || null);
    cellRefs.current[id]?.focus();
  }

  function toggleLock(id: CellId) {
    const fact = cellFact(id, lessons, transmissions);
    setRovingId(id);
    setActiveFact((current) => (fact && current !== fact ? fact : null));
    cellRefs.current[id]?.focus();
  }

  function onCellKeyDown(event: KeyboardEvent<HTMLButtonElement>, id: CellId) {
    if (event.key === "Escape") {
      event.preventDefault();
      setActiveFact(null);
      return;
    }
    if (!isNavigationKey(event.key)) return;
    event.preventDefault();
    focusAndLock(neighbor(id, event.key));
  }

  return (
    <section className={styles.wrap} data-mode={mode} aria-label="课传" aria-busy={mode === "loading" || undefined}>
      {mode === "ready" ? (
        <DaliurenCaliberBar
          dayHour={view?.core_facts?.day_hour ?? null}
          monthGeneral={view?.core_facts?.month_general ?? null}
          noblePerson={view?.core_facts?.noble_person ?? null}
          question={view?.question ?? null}
          xunkong={view?.core_facts?.xunkong ?? null}
        />
      ) : null}
      <div className={styles.board}>
        <div className={styles.lessons}>
          {lessons.map((lesson, index) => {
            const lessonIndex = index as LessonIndex;
            const upperId: CellId = `lesson-${lessonIndex}-upper`;
            const lowerId: CellId = `lesson-${lessonIndex}-lower`;
            return (
              <div className={styles.column} data-lesson={String(lessonIndex)} key={lesson.lesson_id || `lesson-${lessonIndex}`}>
                {mode === "ready" ? <p className={styles.lessonName}>{lesson.lesson_id}</p> : <p className={styles.lessonName} />}
                {mode === "ready" ? (
                  <button
                    className={styles.upper}
                    type="button"
                    data-cell={upperId}
                    data-element={branchElement(lesson.upper)}
                    data-active={isActive(lesson.upper) ? "true" : "false"}
                    data-void={isVoidCell(lesson.upper, voids) ? "true" : undefined}
                    tabIndex={rovingId === upperId ? 0 : -1}
                    aria-pressed={isActive(lesson.upper)}
                    aria-label={`${lesson.lesson_id} 上神 ${lesson.upper}`}
                    ref={(node) => {
                      cellRefs.current[upperId] = node;
                    }}
                    onClick={() => toggleLock(upperId)}
                    onKeyDown={(event) => onCellKeyDown(event, upperId)}
                  >
                    {lesson.upper}
                    {isVoidCell(lesson.upper, voids) ? <VoidMark /> : null}
                  </button>
                ) : (
                  <span className={styles.upper} data-skeleton={mode === "loading" ? "true" : undefined} />
                )}
                <span className={styles.rule} aria-hidden="true" />
                {mode === "ready" ? (
                  <button
                    className={styles.lower}
                    type="button"
                    data-cell={lowerId}
                    data-element={branchElement(lesson.lower)}
                    data-active={isActive(lesson.lower) ? "true" : "false"}
                    data-void={isVoidCell(lesson.lower, voids) ? "true" : undefined}
                    tabIndex={rovingId === lowerId ? 0 : -1}
                    aria-pressed={isActive(lesson.lower)}
                    aria-label={`${lesson.lesson_id} 下神 ${lesson.lower}`}
                    ref={(node) => {
                      cellRefs.current[lowerId] = node;
                    }}
                    onClick={() => toggleLock(lowerId)}
                    onKeyDown={(event) => onCellKeyDown(event, lowerId)}
                  >
                    {lesson.lower}
                    {isVoidCell(lesson.lower, voids) ? <VoidMark /> : null}
                  </button>
                ) : (
                  <span className={styles.lower} data-skeleton={mode === "loading" ? "true" : undefined} />
                )}
              </div>
            );
          })}
        </div>

        <div className={styles.stairs}>
          {transmissions.map((item) => {
            const id: CellId = `tx-${item.stage}`;
            return (
              <div className={styles.tx} data-stage={item.stage} key={item.stage}>
                {mode === "ready" ? (
                  <button
                    className={styles.txButton}
                    type="button"
                    data-cell={id}
                    data-active={isActive(item.branch) ? "true" : "false"}
                    data-void={isVoidCell(item.branch, voids) ? "true" : undefined}
                    tabIndex={rovingId === id ? 0 : -1}
                    aria-pressed={isActive(item.branch)}
                    aria-label={`${STAGE_LABEL[item.stage]} ${item.branch} ${item.general}`}
                    ref={(node) => {
                      cellRefs.current[id] = node;
                    }}
                    onClick={() => toggleLock(id)}
                    onKeyDown={(event) => onCellKeyDown(event, id)}
                  >
                    <span className={styles.stage}>{STAGE_LABEL[item.stage]}</span>
                    <span className={styles.branch} data-element={branchElement(item.branch)}>
                      {item.branch}
                    </span>
                    <span className={styles.general} data-chip="general">
                      {item.general}
                    </span>
                    {isVoidCell(item.branch, voids) ? <VoidMark /> : null}
                  </button>
                ) : (
                  <>
                    <span className={styles.stage}>{STAGE_LABEL[item.stage]}</span>
                    <span className={styles.branch} data-skeleton={mode === "loading" ? "true" : undefined} />
                    <span className={styles.general} data-skeleton={mode === "loading" ? "true" : undefined} />
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {mode === "ready" ? (
        <div className={styles.semantics}>
          <table className={styles.table}>
            <caption>四课</caption>
            <thead>
              <tr>
                <th scope="col">课次</th>
                <th scope="col">上</th>
                <th scope="col">下</th>
              </tr>
            </thead>
            <tbody>
              {lessons.map((lesson, index) => (
                <tr
                  data-active={isActive(lesson.upper) || isActive(lesson.lower) ? "true" : "false"}
                  key={lesson.lesson_id || `lesson-${index}`}
                >
                  <td>{lesson.lesson_id}</td>
                  <td>{lesson.upper}</td>
                  <td>{lesson.lower}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className={styles.table}>
            <caption>三传</caption>
            <thead>
              <tr>
                <th scope="col">阶段</th>
                <th scope="col">地支</th>
                <th scope="col">天将</th>
              </tr>
            </thead>
            <tbody>
              {transmissions.map((item) => (
                <tr data-active={isActive(item.branch) ? "true" : "false"} key={item.stage}>
                  <td>{STAGE_LABEL[item.stage]}</td>
                  <td>{item.branch}</td>
                  <td>{item.general}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {mode === "ready" ? (
        <DaliurenHeavenEarthPlate
          anchorEarthBranches={anchored}
          earthPlate={view?.core_facts?.earth_plate ?? null}
          heavenPlate={view?.core_facts?.heaven_plate ?? null}
          heavenlyGenerals={view?.core_facts?.heavenly_generals ?? null}
          noblePerson={view?.core_facts?.noble_person ?? null}
          plateOffset={view?.core_facts?.plate_offset ?? null}
          xunkong={view?.core_facts?.xunkong ?? null}
        />
      ) : null}

      {mode === "ready" ? (
        <DaliurenLessonMethod
          lessonMethod={view?.core_facts?.lesson_method ?? null}
          structuralPatterns={view?.core_facts?.structural_patterns ?? null}
        />
      ) : null}

      {mode === "ready" ? (
        <DaliurenDimensionEvidence dimensionFacts={view?.core_facts?.dimension_facts ?? null} />
      ) : null}

      {showTiming && candidates ? (
        <section className={styles.timing} aria-labelledby="daliuren-timing-title">
          <h2 id="daliuren-timing-title" className={styles.sectionTitle}>
            应期候选
          </h2>
          <p className={styles.note}>以下为古籍规则产生的候选日期，不是保证的应期</p>
          <table className={styles.table}>
            <caption className={styles.srOnly}>应期候选</caption>
            <thead>
              <tr>
                <th scope="col">候选日期</th>
                <th scope="col">候选支</th>
                <th scope="col">距起课</th>
                <th scope="col">出处</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((item) => {
                const target = transmissionCellForBranch(transmissions, item.branch);
                return (
                  <tr key={`${item.solar_date}-${item.branch}-${item.days_after_cast}`}>
                    <td className={styles.date}>{`${item.solar_date} · ${item.day_ganzhi}日`}</td>
                    <td>
                      {target ? (
                        <button
                          className={styles.branchLink}
                          type="button"
                          aria-label={`候选支 ${item.branch}`}
                          onClick={() => toggleLock(target)}
                          onKeyDown={(event) => {
                            if (event.key !== "Escape") return;
                            event.preventDefault();
                            setActiveFact(null);
                          }}
                        >
                          {item.branch}
                        </button>
                      ) : (
                        <span className={styles.branch}>{item.branch}</span>
                      )}
                    </td>
                    <td>{`第 ${item.days_after_cast} 天`}</td>
                    <td className={styles.source}>{sourceLabel(item.source_pack, item.source_rule)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      ) : null}

      {mode === "ready" ? (
        <DaliurenFreeSummary
          lessons={lessons}
          offer={offer}
          s4Phase={s4Phase}
          structuralPatterns={view?.core_facts?.structural_patterns ?? null}
          transmissions={transmissions}
        />
      ) : null}
    </section>
  );
}
