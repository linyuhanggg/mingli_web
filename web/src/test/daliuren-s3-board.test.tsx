import { act, cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { DaliurenBoard } from "@/components/readings/daliuren-board";
import type {
  DaliurenChartViewModel,
  DaliurenLessonMethod,
  DaliurenNoblePerson,
  DaliurenRuleSourceRef,
} from "@/view-models/registry";

const originalMatchMedia = window.matchMedia;

afterEach(() => {
  cleanup();
  if (originalMatchMedia) window.matchMedia = originalMatchMedia;
  else Reflect.deleteProperty(window, "matchMedia");
});

function stubCompactLessonGrid(compact: boolean) {
  window.matchMedia = ((query: string) =>
    ({
      matches: compact && query === "(max-width: 22.5rem)",
      media: query,
      onchange: null,
      addListener() {},
      removeListener() {},
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() {
        return false;
      },
    })) as typeof window.matchMedia;
}

type CoreFacts = NonNullable<DaliurenChartViewModel["core_facts"]>;
type TimingCandidate = NonNullable<CoreFacts["timing_candidates"]>[number];

const LESSON_METHOD_KEYS = [
  "calculated_transmissions",
  "calculation_source",
  "direct_direction",
  "primary",
  "selected_initial",
  "source_anchor",
  "use_method",
] as const satisfies readonly (keyof DaliurenLessonMethod)[];
const LESSON_METHOD_KEYS_ARE_EXHAUSTIVE: Exclude<
  keyof DaliurenLessonMethod,
  (typeof LESSON_METHOD_KEYS)[number]
> extends never
  ? true
  : never = true;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function requiredString(value: Record<string, unknown>, key: string): string {
  const field = value[key];
  if (typeof field !== "string" || !field.trim()) {
    throw new Error(`Daliuren Runtime golden fixture has invalid ${key}`);
  }
  return field;
}

function goldenLessonMethod(): DaliurenLessonMethod {
  const payload: unknown = JSON.parse(
    readFileSync(resolve(process.cwd(), "../backend/tests/fixtures/liuren-runtime-core-facts-v1.json"), "utf8"),
  );
  if (!isRecord(payload) || !isRecord(payload.lesson_method)) {
    throw new Error("Daliuren Runtime golden fixture has no lesson_method");
  }
  const value = payload.lesson_method;
  const actualKeys = Object.keys(value).sort();
  const expectedKeys = [...LESSON_METHOD_KEYS].sort();
  if (actualKeys.length !== expectedKeys.length || actualKeys.some((key, index) => key !== expectedKeys[index])) {
    throw new Error("Daliuren Runtime golden lesson_method does not match the stable seven-field contract");
  }
  if (value.direct_direction !== null && typeof value.direct_direction !== "string") {
    throw new Error("Daliuren Runtime golden fixture has invalid direct_direction");
  }
  return {
    calculated_transmissions: requiredString(value, "calculated_transmissions"),
    calculation_source: requiredString(value, "calculation_source"),
    direct_direction: value.direct_direction,
    primary: requiredString(value, "primary"),
    selected_initial: requiredString(value, "selected_initial"),
    source_anchor: requiredString(value, "source_anchor"),
    use_method: requiredString(value, "use_method"),
  };
}

function emptyFacts(overrides: Partial<CoreFacts> = {}): CoreFacts {
  return {
    day_hour: null,
    dimension_facts: null,
    earth_plate: null,
    heaven_plate: null,
    heavenly_generals: null,
    lesson_method: null,
    month_general: null,
    noble_person: null,
    plate_offset: null,
    structural_patterns: null,
    timing_candidates: null,
    xunkong: null,
    ...overrides,
  };
}

function candidate(overrides: Partial<TimingCandidate> = {}): TimingCandidate {
  return {
    id: "initial_group_upper_candidate",
    role: "event_response_candidate",
    anchor_earth_branch: "巳",
    branch: "酉",
    solar_date: "2026-09-02",
    day_ganzhi: "庚申",
    days_after_cast: 7,
    source_pack: "san-shi/liuren-miben",
    source_rule: "LM-R21",
    candidate_not_guarantee: true,
    ...overrides,
  };
}

function lessonMethod(overrides: Partial<CoreFacts["lesson_method"]> = {}): CoreFacts["lesson_method"] {
  return {
    calculated_transmissions: "初传酉，中传戌，末传亥",
    calculation_source: "classical_nine-method_algorithm",
    direct_direction: null,
    primary: "贼克课",
    selected_initial: "酉",
    source_anchor: "references/books/san-shi/liuren-miben/rules.md#LM-METHOD",
    use_method: "下贼上发用",
    ...overrides,
  };
}

function noblePerson(overrides: Partial<CoreFacts["noble_person"]> = {}): CoreFacts["noble_person"] {
  return {
    branch: "巳",
    day_night_profile: "甲戊庚牛羊",
    direction: "forward",
    earth_position: "巳",
    period: "day",
    profile: "昼贵人",
    source: "runtime_core_facts",
    ...overrides,
  };
}

function chart(overrides: Partial<DaliurenChartViewModel> = {}): DaliurenChartViewModel {
  return {
    schema_version: "daliuren-chart/v1",
    subject_ref: "daliuren:s3-fixture",
    question: "这件事何时可能出现回应？",
    lessons: [
      { lesson_id: "一课·日干", upper: "巳", lower: "丁" },
      { lesson_id: "二课·日支", upper: "卯", lower: "巳" },
      { lesson_id: "三课·辰干", upper: "酉", lower: "亥" },
      { lesson_id: "四课·辰支", upper: "未", lower: "酉" },
    ],
    transmissions: [
      { stage: "initial", branch: "酉", general: "贵人" },
      { stage: "middle", branch: "未", general: "太阴" },
      { stage: "final", branch: "巳", general: "白虎" },
    ],
    core_facts: null,
    ...overrides,
  };
}

function boardCss() {
  return readFileSync(resolve(process.cwd(), "src/components/readings/daliuren-board.module.css"), "utf8");
}

function plateCss() {
  return readFileSync(
    resolve(process.cwd(), "src/components/readings/daliuren-heaven-earth-plate.module.css"),
    "utf8",
  );
}

function board() {
  return screen.getByRole("region", { name: "课传" });
}

describe("大六壬 S3 课传盘面", () => {
  it("accepts the Runtime golden noble-person direction without a cast", () => {
    const payload: unknown = JSON.parse(
      readFileSync(resolve(process.cwd(), "../backend/tests/fixtures/liuren-runtime-core-facts-v1.json"), "utf8"),
    );
    if (typeof payload !== "object" || payload === null || !("noble_person" in payload)) {
      throw new Error("Daliuren Runtime golden fixture has no noble_person");
    }
    const noblePerson = payload.noble_person;
    if (typeof noblePerson !== "object" || noblePerson === null || !("direction" in noblePerson)) {
      throw new Error("Daliuren Runtime golden noble_person has no direction");
    }
    const { direction } = noblePerson;
    if (direction !== "forward" && direction !== "reverse") {
      throw new Error("Daliuren Runtime golden noble_person has an unsupported direction");
    }
    const typedDirection: DaliurenNoblePerson["direction"] = direction;

    expect(typedDirection).toBe("reverse");
  });

  it("renders four lessons right-to-left with server lesson names and upper above lower", () => {
    render(<DaliurenBoard view={chart()} />);

    const surface = board();
    const columns = surface.querySelectorAll("[data-lesson]");
    expect(columns).toHaveLength(4);
    expect(columns[0]).toHaveAttribute("data-lesson", "0");
    expect(columns[0]).toHaveTextContent("一课·日干");
    expect(columns[3]).toHaveAttribute("data-lesson", "3");
    expect(columns[3]).toHaveTextContent("四课·辰支");
    expect(within(surface).queryByText("一课")).not.toBeInTheDocument();

    const first = columns[0] as HTMLElement;
    const firstUpper = first.querySelector("[data-cell='lesson-0-upper']") as HTMLElement | null;
    const firstLower = first.querySelector("[data-cell='lesson-0-lower']") as HTMLElement | null;
    expect(firstUpper).not.toBeNull();
    expect(firstLower).not.toBeNull();
    expect(firstUpper).toHaveTextContent("巳");
    expect(firstLower).toHaveTextContent("丁");
    expect((firstUpper as HTMLElement).compareDocumentPosition(firstLower as HTMLElement) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(firstUpper).toHaveAttribute("data-element", "fire");
    expect(firstLower).not.toHaveAttribute("data-element");
    expect(columns[1]?.querySelector("[data-cell='lesson-1-upper']")).toHaveAttribute("data-element", "wood");
  });

  it("keeps ordinary lesson cells at least 44 by 44 pixels", () => {
    render(<DaliurenBoard view={chart()} />);

    expect(screen.getByRole("button", { name: "一课·日干 上神 巳" })).toBeVisible();
    expect(screen.getByRole("button", { name: "一课·日干 下神 丁" })).toBeVisible();
    expect(boardCss()).toMatch(
      /\.upper,\s*\.lower\s*\{[^}]*min-width:\s*var\(--target-min\);[^}]*min-height:\s*var\(--target-min\);/s,
    );
  });

  it("renders three transmission stairs with mapped stage labels and neutral general chips", () => {
    render(<DaliurenBoard view={chart()} />);

    const surface = board();
    const rows = surface.querySelectorAll("[data-stage]");
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveAttribute("data-stage", "initial");
    expect(rows[0]).toHaveTextContent("初传");
    expect(rows[0]).toHaveTextContent("酉");
    expect(rows[0]).toHaveTextContent("贵人");
    expect(rows[1]).toHaveAttribute("data-stage", "middle");
    expect(rows[1]).toHaveTextContent("中传");
    expect(rows[2]).toHaveAttribute("data-stage", "final");
    expect(rows[2]).toHaveTextContent("末传");
    expect(rows[2]).toHaveTextContent("白虎");
    expect(surface).not.toHaveTextContent("initial");
    expect(surface).not.toHaveTextContent("middle");
    expect(surface).not.toHaveTextContent("final");
    expect(rows[2]?.querySelector("[data-chip='general']")).toBeTruthy();
    expect(rows[2]?.querySelector("[data-chip='general']")).not.toHaveAttribute("data-luck");
  });

  it("keeps four lessons and three transmissions readable when core_facts is null", () => {
    render(<DaliurenBoard view={chart({ core_facts: null })} />);

    expect(screen.getAllByText("一课·日干").length).toBeGreaterThan(0);
    expect(screen.getAllByText("初传").length).toBeGreaterThan(0);
    expect(screen.getAllByText("白虎").length).toBeGreaterThan(0);
    expect(screen.queryByRole("table", { name: "应期候选" })).not.toBeInTheDocument();
    expect(screen.queryByText("以下为古籍规则产生的候选日期，不是保证的应期")).not.toBeInTheDocument();
    expect(screen.queryByText("天地盘")).not.toBeInTheDocument();
    expect(screen.queryByText("展开天地盘")).not.toBeInTheDocument();
    expect(screen.queryByText("课式")).not.toBeInTheDocument();
    expect(screen.queryByText("传法")).not.toBeInTheDocument();
    expect(screen.queryByText("待计算")).not.toBeInTheDocument();
    expect(screen.queryByText("大吉")).not.toBeInTheDocument();
    expect(screen.queryByText("大凶")).not.toBeInTheDocument();
    expect(screen.queryByText("成败")).not.toBeInTheDocument();
    expect(screen.queryByText("吉凶")).not.toBeInTheDocument();
    expect(screen.queryByText("day_hour")).not.toBeInTheDocument();
    expect(screen.queryByText("timing_candidates")).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/—|–/);
  });

  it("renders readable lesson method and pattern chips without leaking other core-fact keys", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({
            structural_patterns: ["元首课"],
            day_hour: { day: "丙午", hour: "卯" },
            lesson_method: lessonMethod(),
          }),
        })}
      />,
    );

    expect(screen.getAllByText("四课·辰支").length).toBeGreaterThan(0);
    expect(screen.getByText("贼克课")).toBeVisible();
    expect(screen.getAllByText("元首课").length).toBeGreaterThan(0);
    expect(screen.queryByText("天地盘")).not.toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "起课口径" })).getByText("丙午日 卯时")).toBeVisible();
    expect(within(screen.getByRole("region", { name: "课式与传法" })).queryByText("丙午日卯时")).not.toBeInTheDocument();
    expect(screen.queryByText("dimension_facts")).not.toBeInTheDocument();
    expect(screen.queryByText("plate_offset")).not.toBeInTheDocument();
  });

  it("renders the timing candidate table only when the list is non-empty", () => {
    const { rerender } = render(
      <DaliurenBoard view={chart({ core_facts: emptyFacts({ timing_candidates: [candidate()] }) })} />,
    );

    const table = screen.getByRole("table", { name: "应期候选" });
    expect(screen.getByText("以下为古籍规则产生的候选日期，不是保证的应期")).toBeVisible();
    expect(within(table).getByText("2026-09-02 · 庚申日")).toBeVisible();
    expect(within(table).getByRole("button", { name: "候选支 酉" })).toBeVisible();
    expect(within(table).getByText("第 7 天")).toBeVisible();
    expect(within(table).getByText("大六壬秘本 LM-R21")).toBeVisible();
    expect(screen.queryByText("san-shi/liuren-miben")).not.toBeInTheDocument();
    expect(screen.queryByText("candidate_not_guarantee")).not.toBeInTheDocument();
    expect(screen.queryByText("有界应期候选")).not.toBeInTheDocument();
    expect(board().querySelector("[data-stage] [data-badge='timing']")).toBeNull();

    rerender(<DaliurenBoard view={chart({ core_facts: emptyFacts({ timing_candidates: null }) })} />);
    expect(screen.queryByRole("table", { name: "应期候选" })).not.toBeInTheDocument();
    expect(screen.queryByText("以下为古籍规则产生的候选日期，不是保证的应期")).not.toBeInTheDocument();
    expect(screen.queryByText("本课未产生候选日期")).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={chart({ core_facts: emptyFacts({ timing_candidates: [] }) })} />);
    expect(screen.queryByRole("table", { name: "应期候选" })).not.toBeInTheDocument();
  });

  it("links equal facts and clears the click lock on repeat activation or Escape", async () => {
    const user = userEvent.setup();
    render(<DaliurenBoard view={chart()} />);

    const firstUpper = screen.getByRole("button", { name: "一课·日干 上神 巳" });
    const secondLower = screen.getByRole("button", { name: "二课·日支 下神 巳" });
    const finalTx = screen.getByRole("button", { name: "末传 巳 白虎" });
    const linkedSi = [firstUpper, secondLower, finalTx];

    for (const cell of linkedSi) {
      expect(cell).toHaveAttribute("data-active", "false");
      expect(cell).toHaveAttribute("aria-pressed", "false");
    }

    await user.click(firstUpper);
    for (const cell of linkedSi) {
      expect(cell).toHaveAttribute("data-active", "true");
      expect(cell).toHaveAttribute("aria-pressed", "true");
    }
    expect(firstUpper).toHaveFocus();

    await user.click(firstUpper);
    for (const cell of linkedSi) {
      expect(cell).toHaveAttribute("aria-pressed", "false");
      expect(cell).toHaveAttribute("data-active", "true");
    }
    expect(firstUpper).toHaveFocus();
    act(() => firstUpper.blur());
    await user.unhover(firstUpper);
    for (const cell of linkedSi) expect(cell).toHaveAttribute("data-active", "false");

    await user.click(finalTx);
    for (const cell of linkedSi) expect(cell).toHaveAttribute("data-active", "true");
    await user.keyboard("{Escape}");
    for (const cell of linkedSi) {
      expect(cell).toHaveAttribute("aria-pressed", "false");
      expect(cell).toHaveAttribute("data-active", "true");
    }
    expect(finalTx).toHaveFocus();
  });

  it("keeps the focused fact preview after Escape clears a lock", async () => {
    const user = userEvent.setup();
    render(<DaliurenBoard view={chart()} />);

    const firstUpper = screen.getByRole("button", { name: "一课·日干 上神 巳" });
    const secondLower = screen.getByRole("button", { name: "二课·日支 下神 巳" });
    await user.click(firstUpper);
    expect(firstUpper).toHaveAttribute("aria-pressed", "true");
    expect(firstUpper).toHaveAttribute("data-active", "true");
    expect(secondLower).toHaveAttribute("data-active", "true");

    await user.keyboard("{Escape}");
    expect(firstUpper).toHaveFocus();
    expect(firstUpper).toHaveAttribute("aria-pressed", "false");
    expect(firstUpper).toHaveAttribute("data-active", "true");
    expect(secondLower).toHaveAttribute("data-active", "true");

    act(() => firstUpper.blur());
    await user.unhover(firstUpper);
    expect(firstUpper).toHaveAttribute("data-active", "false");
    expect(secondLower).toHaveAttribute("data-active", "false");
  });

  it("temporarily links equal facts on focus and hover, then clears them on leave", async () => {
    const user = userEvent.setup();
    render(<DaliurenBoard view={chart()} />);

    const firstUpper = screen.getByRole("button", { name: "一课·日干 上神 巳" });
    const secondLower = screen.getByRole("button", { name: "二课·日支 下神 巳" });
    const finalTx = screen.getByRole("button", { name: "末传 巳 白虎" });
    const linkedSi = [firstUpper, secondLower, finalTx];

    act(() => firstUpper.focus());
    for (const cell of linkedSi) {
      expect(cell).toHaveAttribute("data-active", "true");
      expect(cell).toHaveAttribute("aria-pressed", "false");
    }

    act(() => firstUpper.blur());
    for (const cell of linkedSi) expect(cell).toHaveAttribute("data-active", "false");

    await user.hover(secondLower);
    for (const cell of linkedSi) expect(cell).toHaveAttribute("data-active", "true");

    await user.unhover(secondLower);
    for (const cell of linkedSi) expect(cell).toHaveAttribute("data-active", "false");
  });

  it("restores the persistent click lock after a different focus or hover preview leaves", async () => {
    const user = userEvent.setup();
    render(<DaliurenBoard view={chart()} />);

    const lockedSi = screen.getByRole("button", { name: "一课·日干 上神 巳" });
    const previewYou = screen.getByRole("button", { name: "初传 酉 贵人" });

    await user.click(lockedSi);
    await user.unhover(lockedSi);
    expect(lockedSi).toHaveAttribute("data-active", "true");
    expect(lockedSi).toHaveAttribute("aria-pressed", "true");

    act(() => previewYou.focus());
    expect(previewYou).toHaveAttribute("data-active", "true");
    expect(previewYou).toHaveAttribute("aria-pressed", "false");
    expect(lockedSi).toHaveAttribute("data-active", "false");
    expect(lockedSi).toHaveAttribute("aria-pressed", "true");

    act(() => previewYou.blur());
    expect(previewYou).toHaveAttribute("data-active", "false");
    expect(lockedSi).toHaveAttribute("data-active", "true");

    await user.hover(previewYou);
    expect(previewYou).toHaveAttribute("data-active", "true");
    expect(lockedSi).toHaveAttribute("data-active", "false");

    await user.unhover(previewYou);
    expect(previewYou).toHaveAttribute("data-active", "false");
    expect(lockedSi).toHaveAttribute("data-active", "true");
    expect(lockedSi).toHaveAttribute("aria-pressed", "true");
  });

  it("resets lock, preview and roving when the reading identity changes", async () => {
    const user = userEvent.setup();
    const firstReading = chart({ subject_ref: "daliuren:reading-a" });
    const { rerender } = render(<DaliurenBoard view={firstReading} />);

    const firstUpper = screen.getByRole("button", { name: "一课·日干 上神 巳" });
    await user.click(firstUpper);
    expect(firstUpper).toHaveAttribute("aria-pressed", "true");
    expect(firstUpper).toHaveAttribute("data-active", "true");
    expect(screen.getByRole("button", { name: "末传 巳 白虎" })).toHaveAttribute("tabindex", "-1");

    rerender(<DaliurenBoard view={chart({ subject_ref: "daliuren:reading-a" })} />);
    expect(screen.getByRole("button", { name: "一课·日干 上神 巳" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "一课·日干 上神 巳" })).toHaveAttribute("data-active", "true");

    rerender(
      <DaliurenBoard
        view={chart({
          subject_ref: "daliuren:reading-b",
          question: "另一课何时可能出现回应？",
        })}
      />,
    );

    const replacedUpper = screen.getByRole("button", { name: "一课·日干 上神 巳" });
    expect(replacedUpper).toHaveAttribute("aria-pressed", "false");
    expect(replacedUpper).toHaveAttribute("data-active", "false");
    expect(replacedUpper).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("button", { name: "末传 巳 白虎" })).toHaveAttribute("tabindex", "-1");
    expect(screen.getByRole("button", { name: "末传 巳 白虎" })).toHaveAttribute("aria-pressed", "false");
  });

  it("moves among the eight lesson cells and three transmission rows with arrow keys", async () => {
    const user = userEvent.setup();
    render(<DaliurenBoard view={chart()} />);

    await user.click(screen.getByRole("button", { name: "一课·日干 上神 巳" }));
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("button", { name: "二课·日支 上神 卯" })).toHaveFocus();

    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("button", { name: "二课·日支 下神 巳" })).toHaveFocus();

    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("button", { name: "初传 酉 贵人" })).toHaveFocus();

    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("button", { name: "中传 未 太阴" })).toHaveFocus();

    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("button", { name: "末传 巳 白虎" })).toHaveFocus();

    await user.keyboard("{ArrowUp}");
    expect(screen.getByRole("button", { name: "中传 未 太阴" })).toHaveFocus();

    await user.click(screen.getByRole("button", { name: "四课·辰支 上神 未" }));
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("button", { name: "三课·辰干 上神 酉" })).toHaveFocus();
  });

  it("moves through the 360 two-column lesson grid without diagonal jumps", async () => {
    stubCompactLessonGrid(true);
    const user = userEvent.setup();
    render(<DaliurenBoard view={chart()} />);

    const lesson0 = screen.getByRole("button", { name: "一课·日干 上神 巳" });
    const lesson1 = screen.getByRole("button", { name: "二课·日支 上神 卯" });
    const lesson1Lower = screen.getByRole("button", { name: "二课·日支 下神 巳" });
    const lesson2 = screen.getByRole("button", { name: "三课·辰干 上神 酉" });
    const lesson2Lower = screen.getByRole("button", { name: "三课·辰干 下神 亥" });
    const lesson3 = screen.getByRole("button", { name: "四课·辰支 上神 未" });
    const initial = screen.getByRole("button", { name: "初传 酉 贵人" });

    await user.click(lesson1);
    await user.keyboard("{ArrowLeft}");
    expect(lesson1).toHaveFocus();

    await user.keyboard("{ArrowRight}");
    expect(lesson0).toHaveFocus();

    await user.click(lesson1);
    await user.keyboard("{ArrowDown}");
    expect(lesson1Lower).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(lesson3).toHaveFocus();

    await user.click(lesson0);
    await user.keyboard("{ArrowDown}");
    await user.keyboard("{ArrowDown}");
    expect(lesson2).toHaveFocus();

    await user.click(lesson2Lower);
    await user.keyboard("{ArrowDown}");
    expect(initial).toHaveFocus();

    await user.keyboard("{ArrowUp}");
    expect(lesson2Lower).toHaveFocus();
  });

  it("moves from a transmission to the first and last plate cells with Home and End", async () => {
    const user = userEvent.setup();
    render(<DaliurenBoard view={chart()} />);

    const middle = screen.getByRole("button", { name: "中传 未 太阴" });
    const first = screen.getByRole("button", { name: "一课·日干 上神 巳" });
    const last = screen.getByRole("button", { name: "末传 巳 白虎" });

    await user.click(middle);
    await user.keyboard("{Home}");
    expect(first).toHaveFocus();
    expect(first).toHaveAttribute("tabindex", "0");
    expect(middle).toHaveAttribute("tabindex", "-1");

    await user.click(middle);
    await user.keyboard("{End}");
    expect(last).toHaveFocus();
    expect(last).toHaveAttribute("tabindex", "0");
    expect(middle).toHaveAttribute("tabindex", "-1");
  });

  it("states the B-tier facts-only boundary instead of leaving an unexplained shortened board", () => {
    render(
      <DaliurenBoard
        view={chart({ core_facts: emptyFacts({ timing_candidates: [candidate()] }) })}
        showInterpretiveSections={false}
      />,
    );

    expect(screen.getByText("当前只提供确定性盘面与事实，不提供断语。")).toBeVisible();
    expect(screen.getByRole("table", { name: "四课" })).toBeVisible();
    expect(screen.getByRole("table", { name: "三传" })).toBeVisible();
    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "应期候选" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "基础摘要" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "深读" })).not.toBeInTheDocument();
  });

  it("does not show the B-tier boundary on an interpretive board", () => {
    render(<DaliurenBoard view={chart()} />);
    expect(screen.queryByText("当前只提供确定性盘面与事实，不提供断语。")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "基础摘要" })).toBeVisible();
  });

  it("exposes semantic tables as the accessible alternative", () => {
    render(<DaliurenBoard view={chart()} />);

    const lessons = screen.getByRole("table", { name: "四课" });
    const transmissions = screen.getByRole("table", { name: "三传" });
    expect(within(lessons).getByRole("columnheader", { name: "课次" })).toBeVisible();
    expect(within(lessons).getByRole("cell", { name: "一课·日干" })).toBeVisible();
    expect(within(lessons).getAllByRole("cell", { name: "巳" }).length).toBeGreaterThan(0);
    expect(within(transmissions).getByRole("columnheader", { name: "阶段" })).toBeVisible();
    expect(within(transmissions).getByRole("cell", { name: "初传" })).toBeVisible();
    expect(within(transmissions).queryByText("initial")).not.toBeInTheDocument();
  });

  it("highlights the transmission matching candidate.branch, not the hover anchor", async () => {
    const user = userEvent.setup();
    render(
      <DaliurenBoard view={chart({ core_facts: emptyFacts({ timing_candidates: [candidate()] }) })} />,
    );

    const candidateButton = screen.getByRole("button", { name: "候选支 酉" });
    const initial = screen.getByRole("button", { name: "初传 酉 贵人" });
    const final = screen.getByRole("button", { name: "末传 巳 白虎" });

    act(() => candidateButton.focus());
    expect(initial).toHaveAttribute("data-active", "true");
    expect(final).toHaveAttribute("data-active", "false");
    act(() => candidateButton.blur());
    expect(initial).toHaveAttribute("data-active", "false");

    await user.hover(candidateButton);
    expect(initial).toHaveAttribute("data-active", "true");
    await user.unhover(candidateButton);
    expect(initial).toHaveAttribute("data-active", "false");

    await user.click(candidateButton);
    expect(initial).toHaveAttribute("data-active", "true");
    expect(final).toHaveAttribute("data-active", "false");
  });

  it("keeps matched timing candidate controls at least 44 by 44 pixels", () => {
    render(
      <DaliurenBoard view={chart({ core_facts: emptyFacts({ timing_candidates: [candidate()] }) })} />,
    );

    expect(screen.getByRole("button", { name: "候选支 酉" })).toBeVisible();
    const css = boardCss();
    expect(css).toMatch(/\.branchLink\s*\{[^}]*min-width:\s*var\(--target-min\)/s);
    expect(css).toMatch(/\.branchLink\s*\{[^}]*min-height:\s*var\(--target-min\)/s);
  });

  it("links the golden Runtime candidate by fact value even when it is absent from transmissions", async () => {
    const user = userEvent.setup();
    render(
      <DaliurenBoard
        view={chart({
          transmissions: [
            { stage: "initial", branch: "辰", general: "六合" },
            { stage: "middle", branch: "酉", general: "太阴" },
            { stage: "final", branch: "卯", general: "朱雀" },
          ],
          core_facts: emptyFacts({
            earth_plate: ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"],
            timing_candidates: [candidate({ branch: "未", anchor_earth_branch: "未" })],
          }),
        })}
      />,
    );

    const timingTable = screen.getByRole("table", { name: "应期候选" });
    const candidateButton = within(timingTable).getByRole("button", { name: "候选支 未" });
    expect(candidateButton).toBeVisible();
    expect(board().querySelector("[data-stage] [data-badge='timing']")).toBeNull();

    await user.click(screen.getByText("天地盘"));
    const earthTable = screen.getByRole("table", { name: "天地盘" });
    const anchor = earthTable.querySelector('[data-branch="未"]') as HTMLElement;
    expect(anchor).toHaveAttribute("data-timing", "true");
    expect(within(anchor).getByText("应期")).toBeVisible();
    expect(earthTable.querySelector('[data-branch="辰"]')).not.toHaveAttribute("data-timing");

    act(() => candidateButton.focus());
    expect(anchor).toHaveAttribute("data-active", "true");
    act(() => candidateButton.blur());
    expect(anchor).toHaveAttribute("data-active", "false");

    await user.hover(candidateButton);
    expect(anchor).toHaveAttribute("data-active", "true");
    await user.unhover(candidateButton);
    expect(anchor).toHaveAttribute("data-active", "false");

    await user.click(candidateButton);
    expect(anchor).toHaveAttribute("data-active", "true");
    expect(candidateButton).toHaveAttribute("aria-pressed", "true");
    await user.click(candidateButton);
    expect(candidateButton).toHaveAttribute("aria-pressed", "false");
    expect(anchor).toHaveAttribute("data-active", "true");
    act(() => candidateButton.blur());
    await user.unhover(candidateButton);
    expect(anchor).toHaveAttribute("data-active", "false");
  });

  it("uses paper-ink tokens, traditional column order and stair indents without glow or luck dye", () => {
    const css = boardCss();
    expect(css).toMatch(/\.lessons\s*\{[^}]*direction:\s*rtl/s);
    expect(css).toMatch(/\.lessons\s*\{[^}]*grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)/s);
    expect(css).toMatch(
      /@media \(max-width: 22\.5rem\)[\s\S]*\.lessons\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/s,
    );
    expect(css).not.toMatch(/22\.499rem/);
    expect(css).toMatch(/\.upper\s*\{[^}]*font-size:\s*var\(--font-size-emphasis\)/s);
    expect(css).toMatch(/\.lower\s*\{[^}]*font-size:\s*var\(--font-size-body\)/s);
    expect(css).toMatch(/\.branch\s*\{[^}]*font-size:\s*var\(--font-size-card\)/s);
    expect(css).toMatch(/\.general\s*\{[^}]*font-size:\s*var\(--font-size-label\)/s);
    expect(css).toMatch(/\.upper\[data-element="fire"\]\s*\{[^}]*var\(--element-fire\)/s);
    expect(css).toMatch(/\[data-stage="middle"\]\s*\{[^}]*margin-inline-start:\s*1\.5rem/s);
    expect(css).toMatch(/\[data-stage="final"\]\s*\{[^}]*margin-inline-start:\s*3rem/s);
    expect(css).toMatch(/font-family:\s*var\(--font-domain\)/);
    expect(css).toMatch(/var\(--color-canvas\)|var\(--color-surface\)/);
    expect(css).not.toMatch(/linear-gradient|radial-gradient|box-shadow:\s*0 0 \d+px|text-shadow/);
    expect(css).not.toMatch(/color-success|color-danger|surface-success|surface-danger/);
    expect(css).not.toMatch(/—|–/);
  });

  it("shows a lesson-and-transmission skeleton in loading mode without sample ganzhi or generals", () => {
    render(<DaliurenBoard view={chart()} mode="loading" />);

    const surface = board();
    expect(surface).toHaveAttribute("data-mode", "loading");
    expect(surface).toHaveAttribute("aria-busy", "true");
    expect(surface.querySelectorAll("[data-lesson]")).toHaveLength(4);
    expect(surface.querySelectorAll("[data-stage]")).toHaveLength(3);
    expect(screen.queryByText("巳")).not.toBeInTheDocument();
    expect(screen.queryByText("白虎")).not.toBeInTheDocument();
    expect(screen.queryByText("一课·日干")).not.toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "应期候选" })).not.toBeInTheDocument();
    expect(screen.queryByText("loading")).not.toBeInTheDocument();
  });
});

describe("大六壬 S3 M4 天地盘", () => {
  const EARTH = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"] as const;

  function plate(overrides: Partial<CoreFacts> = {}) {
    return chart({
      core_facts: emptyFacts({
        earth_plate: [...EARTH],
        ...overrides,
      }),
    });
  }

  function platePanel() {
    return screen.getByText("天地盘").closest("details");
  }

  it("renders a collapsed 天地盘 entry when earth_plate has twelve strings", async () => {
    const user = userEvent.setup();
    render(<DaliurenBoard view={plate()} />);

    const details = platePanel();
    expect(details).toBeTruthy();
    expect(details).not.toHaveAttribute("open");
    expect(within(details as HTMLElement).getByText("天地盘")).toBeVisible();

    await user.click(within(details as HTMLElement).getByText("天地盘"));
    expect(details).toHaveAttribute("open");

    const table = within(details as HTMLElement).getByRole("table", { name: "天地盘" });
    expect(within(table).getByRole("columnheader", { name: "地盘支" })).toBeVisible();
    expect(within(table).queryByRole("columnheader", { name: "天盘支" })).not.toBeInTheDocument();
    expect(within(table).queryByRole("columnheader", { name: "天将" })).not.toBeInTheDocument();
    expect(within(table).getAllByRole("row")).toHaveLength(13);
    expect([...table.querySelectorAll("tbody th, tbody td")].map((node) => node.textContent)).toEqual([
      ...EARTH,
    ]);
    expect(screen.queryByText("展开天地盘")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-DL/)).not.toBeInTheDocument();
    expect(screen.queryByText(/吉凶|大吉|大凶/)).not.toBeInTheDocument();
  });

  it("hides the whole entry when earth_plate is missing, empty or not twelve strings", () => {
    const { rerender } = render(<DaliurenBoard view={chart({ core_facts: emptyFacts({ earth_plate: null }) })} />);
    expect(screen.queryByText("天地盘")).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={chart({ core_facts: emptyFacts({ earth_plate: [] }) })} />);
    expect(screen.queryByText("天地盘")).not.toBeInTheDocument();

    rerender(
      <DaliurenBoard
        view={chart({ core_facts: emptyFacts({ earth_plate: ["子", "丑", "寅"] }) })}
      />,
    );
    expect(screen.queryByText("天地盘")).not.toBeInTheDocument();

    rerender(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({
            earth_plate: ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", ""] ,
          }),
        })}
      />,
    );
    expect(screen.queryByText("天地盘")).not.toBeInTheDocument();
  });

  it("maps heaven and general columns only from explicit keys that hit earth_plate", async () => {
    const user = userEvent.setup();
    render(
      <DaliurenBoard
        view={plate({
          heaven_plate: [
            { earth: "子", heaven: "戌" },
            { earth: "未", heaven: "巳" },
            { earth: "甲", heaven: "寅" },
            { heaven: "卯" },
          ] as CoreFacts["heaven_plate"],
          heavenly_generals: [
            { earth: "卯", heaven: "戌", general: "螣蛇" },
            { earth: "亥", heaven: "子", general: "天后" },
            { earth: "酉", heaven: "午", name: "白虎" },
            { heaven: "子", general: "贵人" },
          ] as CoreFacts["heavenly_generals"],
        })}
      />,
    );

    await user.click(screen.getByText("天地盘"));
    const table = screen.getByRole("table", { name: "天地盘" });
    expect(within(table).getByRole("columnheader", { name: "天盘支" })).toBeVisible();
    expect(within(table).getByRole("columnheader", { name: "天将" })).toBeVisible();
    expect(within(table).getByRole("row", { name: /子/ })).toHaveTextContent("戌");
    expect(within(table).getByRole("row", { name: /未/ })).toHaveTextContent("巳");
    expect(within(table).getByRole("row", { name: /卯/ })).toHaveTextContent("螣蛇");
    expect(within(table).getByRole("row", { name: /亥/ })).toHaveTextContent("天后");
    expect(within(table).queryByText("甲")).not.toBeInTheDocument();
    expect(within(table).queryByText("白虎")).not.toBeInTheDocument();
    expect(within(table).queryByText("贵人")).not.toBeInTheDocument();
    expect(screen.queryByText("earth_branch")).not.toBeInTheDocument();
    expect(screen.queryByText("heaven_branch")).not.toBeInTheDocument();
  });

  it("drops heaven and general columns when rows only provide legacy aliases", async () => {
    const user = userEvent.setup();
    render(
      <DaliurenBoard
        view={plate({
          heaven_plate: [{ earth_branch: "子", heaven_branch: "天盘戌" }, { label: "天盘" }] as unknown as CoreFacts["heaven_plate"],
          heavenly_generals: [{ earth_branch: "卯", general: "螣蛇" }] as unknown as CoreFacts["heavenly_generals"],
        })}
      />,
    );

    await user.click(screen.getByText("天地盘"));
    const table = screen.getByRole("table", { name: "天地盘" });
    expect(within(table).queryByRole("columnheader", { name: "天盘支" })).not.toBeInTheDocument();
    expect(within(table).queryByRole("columnheader", { name: "天将" })).not.toBeInTheDocument();
    expect(table.querySelector('[data-branch="子"]')).toBeTruthy();
    expect(within(table).queryByText("天盘戌")).not.toBeInTheDocument();
    expect(within(table).queryByText("螣蛇")).not.toBeInTheDocument();
  });

  it("marks the noble person's earth position instead of its heaven-plate branch", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <DaliurenBoard
        view={plate({
          noble_person: {
            branch: "卯",
            day_night_profile: "甲戊庚牛羊",
            direction: "forward",
            earth_position: "未",
            period: "day",
            profile: "昼贵人",
            source: "runtime_core_facts",
          },
        })}
      />,
    );

    await user.click(screen.getByText("天地盘"));
    const table = screen.getByRole("table", { name: "天地盘" });
    const nobleRow = table.querySelector('[data-branch="未"]');
    expect(nobleRow).toHaveAttribute("data-noble", "true");
    expect(within(nobleRow as HTMLElement).getByText("贵人落地")).toBeVisible();
    expect(nobleRow).toHaveAccessibleName(/未.*贵人落地/);
    expect(within(table).queryByRole("columnheader", { name: "天将" })).not.toBeInTheDocument();
    expect(table.querySelector('[data-branch="卯"]')).not.toHaveAttribute(
      "data-noble",
    );
    expect(screen.queryByText(/昼|夜|昼夜/)).not.toBeInTheDocument();

    rerender(
      <DaliurenBoard
        view={plate({ noble_person: { earth_branch: "午" } as unknown as CoreFacts["noble_person"] })}
      />,
    );
    expect(screen.getByRole("table", { name: "天地盘" }).querySelector('[data-branch="午"]')).not.toHaveAttribute(
      "data-noble",
    );
    expect(screen.getByRole("table", { name: "天地盘" }).querySelector('[data-branch="卯"]')).not.toHaveAttribute(
      "data-noble",
    );
    expect(screen.queryByText("贵人落地")).not.toBeInTheDocument();
  });

  it("keeps earth spokes fixed when plate_offset is nonzero and preserves offset only as metadata", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <DaliurenBoard view={plate({ plate_offset: 3 })} />,
    );

    await user.click(screen.getByText("天地盘"));
    const panel = screen.getByRole("table", { name: "天地盘" }).closest("[data-slot='heaven-earth']");
    const visualRing = panel?.querySelector("[data-ring='earth']");
    const earthZi = visualRing?.querySelector('[data-branch="子"]');
    expect(panel).toHaveAttribute("data-offset", "3");
    expect(visualRing).not.toHaveStyle("--plate-offset: 3");
    expect(earthZi).toHaveStyle("--spoke: 0");
    expect(plateCss()).toMatch(/--earth-radius:\s*8rem/);
    expect(plateCss()).toMatch(/--heaven-radius:\s*12rem/);
    expect(plateCss()).toMatch(/--general-radius:\s*16rem/);
    expect(plateCss()).toMatch(/translateY\(calc\(-1 \* var\(--earth-radius\)\)\)/);
    expect(plateCss()).not.toMatch(/translateY\(-7\.2rem\)/);
    expect(plateCss()).not.toContain("--plate-offset");

    rerender(<DaliurenBoard view={plate({ plate_offset: null })} />);
    expect(screen.getByRole("table", { name: "天地盘" }).closest("[data-slot='heaven-earth']")).not.toHaveAttribute(
      "data-offset",
    );
    expect(screen.queryByText("plate_offset")).not.toBeInTheDocument();
    expect(screen.queryByText("3")).not.toBeInTheDocument();
  });

  it("keeps loading and silhouette modes free of the plate", () => {
    const { rerender } = render(<DaliurenBoard view={plate()} mode="loading" />);
    expect(screen.queryByText("天地盘")).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={plate()} mode="silhouette" />);
    expect(screen.queryByText("天地盘")).not.toBeInTheDocument();
  });

  it("keeps the plate module off shared pages", () => {
    const boardSource = readFileSync(resolve(process.cwd(), "src/components/readings/daliuren-board.tsx"), "utf8");
    const plateSource = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-heaven-earth-plate.tsx"),
      "utf8",
    );
    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-heaven-earth-plate.module.css"),
      "utf8",
    );
    const runtime = readFileSync(resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"), "utf8");
    const experience = readFileSync(resolve(process.cwd(), "src/components/task/product-task-experience.tsx"), "utf8");
    expect(boardSource).toContain("daliuren-heaven-earth-plate");
    expect(plateSource).not.toMatch(/bazi-chart|liuyao-line-tower|runtime-chart|product-task-experience|GAP-DL/);
    expect(css).toMatch(/--color-evidence/);
    expect(css).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(css).not.toMatch(/color-success|color-danger|surface-success|surface-danger/);
    expect(css).not.toMatch(/linear-gradient|radial-gradient|box-shadow:\s*0 0/);
    expect(runtime).not.toContain("daliuren-heaven-earth-plate");
    expect(experience).not.toContain("daliuren-heaven-earth-plate");
  });
});

describe("大六壬 S3 M5 课式与传法", () => {
  function methodPanel() {
    return screen.getByRole("region", { name: "课式与传法" });
  }

  it("does not expose or consume the legacy transmission_method alias", () => {
    const registry = readFileSync(resolve(process.cwd(), "src/view-models/registry.ts"), "utf8");
    expect(registry).not.toContain("transmission_method");

    render(
      <DaliurenBoard
        view={chart({
          core_facts: {
            ...emptyFacts(),
            transmission_method: { text: "旧传法" },
          } as unknown as CoreFacts,
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "课式与传法" })).not.toBeInTheDocument();
    expect(screen.queryByText("旧传法")).not.toBeInTheDocument();
  });

  it("mirrors and renders the Runtime golden seven-field lesson_method contract", () => {
    const method = goldenLessonMethod();
    render(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({
            lesson_method: method,
          }),
        })}
      />,
    );

    const panel = methodPanel();
    expect(LESSON_METHOD_KEYS_ARE_EXHAUSTIVE).toBe(true);
    expect(Object.keys(method).sort()).toEqual([...LESSON_METHOD_KEYS].sort());
    expect(within(panel).getByText("课式")).toBeVisible();
    expect(within(panel).getByText("伏吟")).toBeVisible();
    expect(within(panel).getByText("发用")).toBeVisible();
    expect(within(panel).getByText("伏吟有克/重审")).toBeVisible();
    expect(within(panel).getByText("发用初传")).toBeVisible();
    expect(within(panel).getByText("辰")).toBeVisible();
    expect(within(panel).getByText("取传方向")).toBeVisible();
    expect(within(panel).getByText("下贼上")).toBeVisible();
    expect(within(panel).getByText("三传")).toBeVisible();
    expect(within(panel).getByText("辰酉卯")).toBeVisible();
    expect(within(panel).getByText("计算来源")).toBeVisible();
    expect(within(panel).getByText("古典九法")).toBeVisible();
    expect(within(panel).queryByText("classical_nine-method_algorithm")).not.toBeInTheDocument();
    expect(within(panel).getByText("来源定位")).toBeVisible();
    expect(within(panel).getByText("daliuren-daquan L7696/L7818")).toBeVisible();
    expect(within(panel).queryByText("传法")).not.toBeInTheDocument();
    expect(screen.queryByText("display_text")).not.toBeInTheDocument();
    expect(screen.queryByText("lesson_method")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-DL/)).not.toBeInTheDocument();
  });

  it("omits only the nullable direction row when Runtime returns null", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({ lesson_method: lessonMethod({ direct_direction: null }) }),
        })}
      />,
    );

    const panel = methodPanel();
    expect(within(panel).queryByText("取传方向")).not.toBeInTheDocument();
    expect(within(panel).getByText("发用初传")).toBeVisible();
    expect(within(panel).getByText("计算来源")).toBeVisible();
    expect(within(panel).getByText("来源定位")).toBeVisible();
  });

  it("does not invent a method sentence from lessons, transmissions, disallowed keys, or legacy aliases", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: {
            ...emptyFacts({
              lesson_method: lessonMethod({
                calculated_transmissions: "",
                calculation_source: "",
                direct_direction: null,
                primary: "",
                selected_initial: "",
                source_anchor: "",
                use_method: "",
              }),
              structural_patterns: null,
            }),
            transmission_method: { use_method: "发明传法" },
          } as unknown as CoreFacts,
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "课式与传法" })).not.toBeInTheDocument();
    expect(screen.queryByText("发明课式")).not.toBeInTheDocument();
    expect(screen.queryByText("发明传法")).not.toBeInTheDocument();
    expect(screen.queryByText("课式")).not.toBeInTheDocument();
    expect(screen.queryByText("传法")).not.toBeInTheDocument();
    expect(screen.queryByText("发用初传")).not.toBeInTheDocument();
    expect(screen.queryByText("取传方向")).not.toBeInTheDocument();
    expect(screen.queryByText("计算来源")).not.toBeInTheDocument();
    expect(screen.queryByText("来源定位")).not.toBeInTheDocument();
  });

  it("maps the classical nine-method source and fails closed for unknown source IDs", () => {
    const { rerender } = render(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({
            lesson_method: lessonMethod({ calculation_source: "classical_nine-method_algorithm" }),
          }),
        })}
      />,
    );

    const panel = methodPanel();
    expect(within(panel).getByText("计算来源")).toBeVisible();
    expect(within(panel).getByText("古典九法")).toBeVisible();
    expect(screen.queryByText("classical_nine-method_algorithm")).not.toBeInTheDocument();

    rerender(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({
            lesson_method: lessonMethod({ calculation_source: "language_model_guess" }),
          }),
        })}
      />,
    );

    expect(within(methodPanel()).getByText("课式")).toBeVisible();
    expect(within(methodPanel()).queryByText("计算来源")).not.toBeInTheDocument();
    expect(screen.queryByText("language_model_guess")).not.toBeInTheDocument();
    expect(screen.queryByText("classical_nine-method_algorithm")).not.toBeInTheDocument();
    expect(screen.queryByText("runtime_core_facts")).not.toBeInTheDocument();
  });

  it("renders non-empty structural patterns as inert chips without evidence gold", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({
            structural_patterns: ["", "  ", "元首课", "重审课"],
          }),
        })}
      />,
    );

    const panel = methodPanel();
    const chips = within(panel).getAllByText(/元首课|重审课/);
    expect(chips).toHaveLength(2);
    expect(within(panel).queryByRole("button", { name: "元首课" })).not.toBeInTheDocument();
    expect(within(panel).queryByRole("link", { name: "元首课" })).not.toBeInTheDocument();
    expect(panel.querySelector("[data-badge]")).toBeNull();
    expect(panel.querySelector("[data-chip='pattern']")).not.toHaveAttribute("data-luck");
    expect(screen.queryByText("课式")).not.toBeInTheDocument();
    expect(screen.queryByText("传法")).not.toBeInTheDocument();
  });

  it("hides the whole block when every M5 field is empty", () => {
    const { rerender } = render(<DaliurenBoard view={chart({ core_facts: emptyFacts() })} />);
    expect(screen.queryByRole("region", { name: "课式与传法" })).not.toBeInTheDocument();
    expect(screen.queryByText("课式")).not.toBeInTheDocument();
    expect(screen.queryByText("传法")).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={chart({ core_facts: emptyFacts({ structural_patterns: [] }) })} />);
    expect(screen.queryByRole("region", { name: "课式与传法" })).not.toBeInTheDocument();
  });

  it("keeps loading and silhouette modes free of method copy", () => {
    const view = chart({
      core_facts: emptyFacts({
        lesson_method: lessonMethod(),
        structural_patterns: ["元首课"],
      }),
    });
    const { rerender } = render(<DaliurenBoard view={view} mode="loading" />);
    expect(screen.queryByText("课式")).not.toBeInTheDocument();
    expect(screen.queryByText("贼克课")).not.toBeInTheDocument();
    expect(screen.queryByText("元首课")).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={view} mode="silhouette" />);
    expect(screen.queryByText("课式")).not.toBeInTheDocument();
    expect(screen.queryByText("元首课")).not.toBeInTheDocument();
  });

  it("keeps the lesson-method module off shared pages", () => {
    const boardSource = readFileSync(resolve(process.cwd(), "src/components/readings/daliuren-board.tsx"), "utf8");
    const methodSource = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-lesson-method.tsx"),
      "utf8",
    );
    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-lesson-method.module.css"),
      "utf8",
    );
    const runtime = readFileSync(resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"), "utf8");
    const experience = readFileSync(resolve(process.cwd(), "src/components/task/product-task-experience.tsx"), "utf8");
    expect(boardSource).toContain("daliuren-lesson-method");
    expect(methodSource).not.toMatch(/bazi-chart|liuyao-line-tower|runtime-chart|product-task-experience|GAP-DL/);
    expect(css).toMatch(/--color-text/);
    expect(css).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(css).not.toMatch(/color-success|color-danger|surface-success|surface-danger|--color-evidence/);
    expect(css).not.toMatch(/linear-gradient|radial-gradient|box-shadow:\s*0 0/);
    expect(runtime).not.toContain("daliuren-lesson-method");
    expect(experience).not.toContain("daliuren-lesson-method");
  });
});

describe("大六壬 S3 M6a 维度证据", () => {
  type FactObject = NonNullable<CoreFacts["dimension_facts"]>;

  function runtimeRuleSourceRefs(
    ruleKey:
      | "state_general_landing_correspondence"
      | "wealth_present_miben"
      | "wealth_void_miben"
      | "work_target_present",
  ): readonly DaliurenRuleSourceRef[] {
    const payload: unknown = JSON.parse(
      readFileSync(
        resolve(process.cwd(), "../core/mingli-master/references/inference/liuren-rules-v1.json"),
        "utf8",
      ),
    );
    if (!isRecord(payload) || !isRecord(payload.rules) || !isRecord(payload.rules[ruleKey])) {
      throw new Error(`Daliuren Runtime rules have no ${ruleKey}`);
    }
    const refs = payload.rules[ruleKey].source_refs;
    if (!Array.isArray(refs)) throw new Error(`Daliuren Runtime rule ${ruleKey} has no source_refs`);
    return refs.map((ref) => {
      if (!isRecord(ref)) throw new Error(`Daliuren Runtime rule ${ruleKey} has an invalid source ref`);
      const pack = requiredString(ref, "pack");
      const ruleId = requiredString(ref, "rule_id");
      const quoteId = typeof ref.quote_id === "string" && ref.quote_id.trim() ? ref.quote_id : undefined;
      const sourceAnchor =
        typeof ref.source_anchor === "string" && ref.source_anchor.trim() ? ref.source_anchor : undefined;
      return {
        pack,
        rule_id: ruleId,
        ...(quoteId ? { quote_id: quoteId } : {}),
        ...(sourceAnchor ? { source_anchor: sourceAnchor } : {}),
      };
    });
  }

  function goldenDimensionFacts(): FactObject {
    const payload = JSON.parse(
      readFileSync(resolve(process.cwd(), "../backend/tests/fixtures/liuren-runtime-core-facts-v1.json"), "utf8"),
    ) as { dimension_facts?: FactObject };
    if (!payload.dimension_facts) throw new Error("Daliuren Runtime golden fixture has no dimension_facts");
    return payload.dimension_facts;
  }

  function matchedEntry(overrides: Record<string, unknown> = {}) {
    return {
      activation_id: "act-1",
      dependency_group: "group",
      fact_paths: ["fact:/chart/lessons/0"],
      observation: { display_text: "初传与日干同类", extra: "忽略观察" },
      polarity: "support",
      rule_id: "LM-R01",
      rule_key: "lm-r01",
      source_refs: [
        {
          pack: "san-shi/liuren-miben",
          rule_id: "LM-R01",
          source_anchor: "rules.md#L10-L16",
        },
      ],
      status: "matched",
      weight_class: "primary",
      ...overrides,
    };
  }

  function evidence(overrides: Record<string, unknown> = {}) {
    return {
      catalog_schema: "rule-evidence/v1",
      hard_verdict: null,
      matched: [matchedEntry()],
      not_evaluated: [
        {
          activation_id: "skip-1",
          reason: "not requested",
          rule_id: "SKIP-9",
          rule_key: "skip",
          source_refs: [{ pack: "san-shi/liuren-miben", rule_id: "SKIP-9" }],
          status: "not_evaluated",
        },
      ],
      requires_school_adjudication: false,
      scope_boundaries: [],
      status: "matched",
      ...overrides,
    };
  }

  function dimension(overrides: Record<string, unknown> = {}) {
    return {
      canonical_dimension: "relationship",
      requested_dimension: "relationship",
      rule_evidence: evidence(),
      ...overrides,
    };
  }

  function factsWithDimensions(blocks: Record<string, unknown>): CoreFacts {
    return emptyFacts({
      dimension_facts: blocks as FactObject,
    });
  }

  function panel() {
    return screen.getByRole("region", { name: "维度证据" });
  }

  function stateStatus(
    stage: "initial" | "middle" | "final",
    branch: string,
    heavenlyGeneral: string,
    overrides: Record<string, unknown> = {},
  ) {
    return {
      stage,
      branch,
      six_relative: "兄弟",
      heavenly_general: heavenlyGeneral,
      season_strength: "休",
      is_xunkong: false,
      ...overrides,
    };
  }

  function runtimeStateEvidence(overrides: Record<string, unknown> = {}) {
    return evidence({
      catalog_schema: "mingli-liuren-executable-rules-v1",
      matched: [],
      not_evaluated: [],
      requires_school_adjudication: true,
      scope_boundaries: [],
      status: "not_bound",
      ...overrides,
    });
  }

  function presentMoneyProjection(overrides: Record<string, unknown> = {}) {
    const wealthStageStrength = [
      { stage: "initial", branch: "辰", six_relative: "妻财", season_strength: "旺" },
      { stage: "final", branch: "亥", six_relative: "妻财", season_strength: "休" },
    ];
    const wealthVoidStatus = [
      { stage: "initial", branch: "辰", six_relative: "妻财", is_xunkong: false },
      { stage: "final", branch: "亥", six_relative: "妻财", is_xunkong: true },
    ];
    return {
      canonical_dimension: "money",
      requested_dimension: "money",
      status: "calculated_facts_not_verdict",
      source_rule_ids: ["LM-R20"],
      wealth_presence: true,
      wealth_stage_strength: wealthStageStrength,
      wealth_void_status: wealthVoidStatus,
      wealth_general_modifier: [
        {
          stage: "initial",
          heavenly_general: "勾陈",
          landing_branch: "辰",
          source_pack: "san-shi/liuren-miben",
          source_rule: "LM-R01",
          role: "imagery_correspondence_not_observed_activity",
          status: "source_correspondence_matched",
          source_text: "勾陈临辰",
          source_anchor: "fulltext.md#L10",
          six_relative: "妻财",
        },
        {
          stage: "final",
          heavenly_general: "白虎",
          landing_branch: "亥",
          source_pack: "san-shi/liuren-miben",
          source_rule: "LM-R01",
          role: "imagery_correspondence_not_observed_activity",
          status: "no_exact_source_correspondence",
          six_relative: "妻财",
        },
      ],
      rule_evidence: runtimeStateEvidence({
        matched: [
          matchedEntry({
            activation_id: "liuren.wealth.present.miben",
            dependency_group: "wealth_receipt_availability",
            fact_paths: ["dimension_facts.money.wealth_presence"],
            observation: {
              wealth_presence: true,
              wealth_stages: wealthStageStrength,
            },
            polarity: "support",
            rule_id: "LM-R20",
            rule_key: "wealth_present_miben",
            source_refs: runtimeRuleSourceRefs("wealth_present_miben"),
            weight_class: "primary",
          }),
          matchedEntry({
            activation_id: "liuren.wealth.void",
            dependency_group: "wealth_receipt_availability",
            fact_paths: ["dimension_facts.money.wealth_void_status"],
            observation: {
              wealth_void_rows: [wealthVoidStatus[1]],
            },
            polarity: "oppose",
            rule_id: "LM-R20",
            rule_key: "wealth_void_miben",
            source_refs: runtimeRuleSourceRefs("wealth_void_miben"),
            weight_class: "primary",
          }),
        ],
        status: "matched_evidence",
      }),
      ...overrides,
    };
  }

  function malformedPresentMoneyProjection(
    kind: "cross_field" | "extra_field" | "general_enum" | "matched_source" | "modifier_source" | "stage_order",
  ): Record<string, unknown> {
    const projection = structuredClone(presentMoneyProjection()) as Record<string, unknown>;
    if (kind === "extra_field") {
      projection.raw_dump = "不得展示 money extra";
      return projection;
    }
    const strengthRows = projection.wealth_stage_strength as Record<string, unknown>[];
    const voidRows = projection.wealth_void_status as Record<string, unknown>[];
    const modifierRows = projection.wealth_general_modifier as Record<string, unknown>[];
    if (kind === "stage_order") {
      projection.wealth_stage_strength = [...strengthRows].reverse();
      projection.wealth_void_status = [...voidRows].reverse();
      projection.wealth_general_modifier = [...modifierRows].reverse();
    } else if (kind === "general_enum") {
      modifierRows[0] = { ...modifierRows[0], heavenly_general: "未知天将" };
    } else if (kind === "cross_field") {
      modifierRows[0] = { ...modifierRows[0], landing_branch: "午" };
    } else if (kind === "modifier_source") {
      modifierRows[0] = { ...modifierRows[0], source_rule: "LM-R02" };
    } else {
      const ruleEvidence = projection.rule_evidence as Record<string, unknown>;
      const matched = ruleEvidence.matched as Record<string, unknown>[];
      const sourceRefs = matched[0]?.source_refs as Record<string, unknown>[];
      sourceRefs[0] = { ...sourceRefs[0], source_anchor: "fulltext.md#drift" };
    }
    return projection;
  }

  function matchedOutcomeProjection(overrides: Record<string, unknown> = {}) {
    return {
      canonical_dimension: "outcome",
      requested_dimension: "outcome",
      status: "calculated_facts_not_verdict",
      source_rule_ids: ["LR-17"],
      subject_object_relation: {
        subject: "day_stem",
        subject_value: "甲",
        subject_element: "木",
        object: "day_branch",
        object_value: "申",
        object_element: "金",
        relation: "object_overcomes_subject",
      },
      transmissions_to_day: [
        {
          stage: "initial",
          subject: "transmission_branch",
          subject_value: "巳",
          subject_element: "火",
          object: "day_stem",
          object_value: "甲",
          object_element: "木",
          relation: "object_generates_subject",
        },
        {
          stage: "middle",
          subject: "transmission_branch",
          subject_value: "申",
          subject_element: "金",
          object: "day_stem",
          object_value: "甲",
          object_element: "木",
          relation: "subject_overcomes_object",
        },
        {
          stage: "final",
          subject: "transmission_branch",
          subject_value: "卯",
          subject_element: "木",
          object: "day_stem",
          object_value: "甲",
          object_element: "木",
          relation: "same_element",
        },
      ],
      initial_final_relation: {
        subject: "initial_branch",
        subject_value: "巳",
        subject_element: "火",
        object: "final_branch",
        object_value: "卯",
        object_element: "木",
        relation: "object_generates_subject",
      },
      stage_flow: [
        {
          from_stage: "initial",
          to_stage: "middle",
          subject: "from_branch",
          subject_value: "巳",
          subject_element: "火",
          object: "to_branch",
          object_value: "申",
          object_element: "金",
          relation: "subject_overcomes_object",
        },
        {
          from_stage: "middle",
          to_stage: "final",
          subject: "from_branch",
          subject_value: "申",
          subject_element: "金",
          object: "to_branch",
          object_value: "卯",
          object_element: "木",
          relation: "subject_overcomes_object",
        },
      ],
      rule_evidence: runtimeStateEvidence({
        matched: [
          matchedEntry({
            activation_id: "liuren.subject_object.branch_overcomes_day",
            dependency_group: "liuren.subject_object_relation",
            fact_paths: ["dimension_facts.outcome.subject_object_relation"],
            observation: { relation: "object_overcomes_subject" },
            polarity: "oppose",
            rule_id: "LR-17",
            rule_key: "day_branch_overcomes_stem",
            source_refs: [
              {
                pack: "san-shi/liuren-zhiyin",
                rule_id: "LR-17",
                quote_id: "LZ-Q054",
                source_anchor: "fulltext.md#L557",
              },
            ],
          }),
        ],
        status: "matched_evidence",
      }),
      ...overrides,
    };
  }

  function boundWorkProjection(
    requestedDimension: "work" | "career" = "work",
    targetRelative: "官鬼" | "父母" = "官鬼",
  ) {
    const sixRelativeStages = [
      { stage: "initial", branch: "辰", six_relative: "妻财" },
      { stage: "middle", branch: "酉", six_relative: "官鬼" },
      { stage: "final", branch: "亥", six_relative: "官鬼" },
    ];
    const stageStatus = [
      stateStatus("initial", "辰", "勾陈", { six_relative: "妻财", season_strength: "旺" }),
      stateStatus("middle", "酉", "天后", { six_relative: "官鬼", season_strength: "囚" }),
      stateStatus("final", "亥", "白虎", {
        six_relative: "官鬼",
        season_strength: "unknown",
        is_xunkong: true,
      }),
    ];
    const targetStrength =
      targetRelative === "官鬼"
        ? [
            {
              stage: "middle",
              branch: "酉",
              six_relative: "官鬼",
              season_strength: "囚",
              is_xunkong: false,
            },
            {
              stage: "final",
              branch: "亥",
              six_relative: "官鬼",
              season_strength: "unknown",
              is_xunkong: true,
            },
          ]
        : [];
    const targetGeneralModifier =
      targetRelative === "官鬼"
        ? [
            {
              stage: "middle",
              heavenly_general: "天后",
              landing_branch: "酉",
              source_pack: "san-shi/liuren-miben",
              source_rule: "LM-R01",
              role: "imagery_correspondence_not_observed_activity",
              status: "source_correspondence_matched",
              source_text: "天后临酉",
              source_anchor: "fulltext.md#L11",
              six_relative: "官鬼",
            },
            {
              stage: "final",
              heavenly_general: "白虎",
              landing_branch: "亥",
              source_pack: "san-shi/liuren-miben",
              source_rule: "LM-R01",
              role: "imagery_correspondence_not_observed_activity",
              status: "no_exact_source_correspondence",
              six_relative: "官鬼",
            },
          ]
        : [];
    const targetPresence = targetRelative === "官鬼";
    const observation = targetPresence
      ? {
          target_relative: targetRelative,
          target_strength: targetStrength,
          target_general_modifier: targetGeneralModifier,
        }
      : {
          target_relative: targetRelative,
          target_presence: false,
          target_contract_status: "bound",
        };
    const targetEvidence = matchedEntry({
      activation_id: "liuren.target.work.present",
      confidence_ceiling: "medium",
      dependency_group: "liuren.target.work.presence",
      fact_paths: [
        "dimension_facts.work.target_relative",
        "dimension_facts.work.target_presence",
      ],
      observation,
      polarity: "support",
      rule_id: "LR-19",
      rule_key: "work_target_present",
      source_refs: runtimeRuleSourceRefs("work_target_present"),
      status: targetPresence ? "matched" : "scope_boundary",
      weight_class: "primary",
    });
    return {
      canonical_dimension: "work",
      requested_dimension: requestedDimension,
      status: "calculated_facts_not_verdict",
      source_rule_ids: targetPresence ? ["LR-19"] : [],
      six_relative_stages: sixRelativeStages,
      stage_status: stageStatus,
      subject_object_relation: {
        subject: "day_stem",
        subject_value: "甲",
        subject_element: "木",
        object: "day_branch",
        object_value: "寅",
        object_element: "木",
        relation: "same_element",
      },
      target_relative: targetRelative,
      target_contract_status: "bound",
      target_presence: targetPresence,
      target_strength: targetStrength,
      target_general_modifier: targetGeneralModifier,
      rule_evidence: runtimeStateEvidence({
        matched: targetPresence ? [targetEvidence] : [],
        scope_boundaries: targetPresence ? [] : [targetEvidence],
        status: targetPresence ? "matched_evidence" : "scope_boundary",
      }),
    };
  }

  function missingWorkProjection(requestedDimension: "work" | "career" = "work") {
    return {
      canonical_dimension: "work",
      requested_dimension: requestedDimension,
      status: "calculated_facts_not_verdict",
      source_rule_ids: [],
      six_relative_stages: [
        { stage: "initial", branch: "巳", six_relative: "子孙" },
        { stage: "middle", branch: "申", six_relative: "官鬼" },
        { stage: "final", branch: "卯", six_relative: "兄弟" },
      ],
      stage_status: [
        stateStatus("initial", "巳", "勾陈", { six_relative: "子孙" }),
        stateStatus("middle", "申", "天后", { six_relative: "官鬼" }),
        stateStatus("final", "卯", "白虎", { six_relative: "兄弟" }),
      ],
      subject_object_relation: {
        subject: "day_stem",
        subject_value: "甲",
        subject_element: "木",
        object: "day_branch",
        object_value: "寅",
        object_element: "木",
        relation: "same_element",
      },
      target_relative: null,
      target_contract_status: "missing_target_relative",
      target_presence: false,
      target_strength: [],
      target_general_modifier: [],
      rule_evidence: runtimeStateEvidence({
        not_evaluated: [
          {
            rule_key: "work_target_present",
            activation_id: "liuren.target.work.present",
            rule_id: "LR-19",
            status: "required_fact_missing",
            reason: "work_target_relative_not_supplied",
            source_refs: [
              {
                pack: "san-shi/liuren-zhiyin",
                rule_id: "LR-19",
                quote_id: "LZ-Q056",
                source_anchor: "fulltext.md#L777",
              },
            ],
          },
        ],
      }),
    };
  }

  it("renders the real Runtime relationship and timing observations under frozen Chinese titles", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({ dimension_facts: goldenDimensionFacts() }),
        })}
      />,
    );

    const block = panel();
    const relationship = within(block).getByRole("group", { name: "关系" });
    const timing = within(block).getByRole("group", { name: "时机" });
    expect(within(relationship).getByText("LR-17")).toBeVisible();
    expect(within(relationship).getByText("主客关系：客体克主体")).toBeVisible();
    expect(relationship).toHaveTextContent("日干与日支：乙（木）与酉（金）：后者克前者");
    expect(relationship).toHaveTextContent("三传六亲：初传 辰 · 妻财；中传 酉 · 官鬼；末传 卯 · 兄弟");
    expect(relationship).toHaveTextContent("三传流转：初传至中传 辰（土）与酉（金）：前者生后者");
    expect(within(timing).getByText("LM-R21")).toBeVisible();
    expect(
      within(timing).getByText("规则候选支：未 · 候选日期：2026-07-20（乙未日） · 相对节奏：较快"),
    ).toBeVisible();
    expect(block).not.toHaveTextContent(/object_overcomes_subject|candidate_branch|candidate_date|relative_speed/);
    expect(block).not.toHaveTextContent(/relationship|timing/);
    expect(block).not.toHaveTextContent(/hard_verdict|吉凶|成败|大吉|大凶/);
  });

  it("renders outcome, money, state and work observations under frozen Chinese titles", () => {
    const correspondence = {
      stage: "initial",
      heavenly_general: "勾陈",
      landing_branch: "辰",
      source_pack: "san-shi/liuren-miben",
      source_rule: "LM-R01",
      role: "imagery_correspondence_not_observed_activity",
      status: "source_correspondence_matched",
      source_text: "勾陈临辰",
      source_anchor: "fulltext.md#L10",
    };
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            outcome: dimension({
              canonical_dimension: "outcome",
              requested_dimension: "outcome",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({ rule_id: "LR-17", observation: { relation: "subject_overcomes_object" } }),
                  matchedEntry({
                    rule_id: "LR-18",
                    observation: {
                      relations: [
                        "subject_generates_object",
                        "subject_generates_object",
                        "subject_generates_object",
                      ],
                    },
                  }),
                  matchedEntry({
                    rule_id: "LM-R02",
                    observation: { stage: "middle", branch: "午", is_xunkong: true },
                  }),
                ],
              }),
            }),
            money: dimension({
              canonical_dimension: "money",
              requested_dimension: "money",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LM-R08",
                    observation: {
                      wealth_presence: true,
                      wealth_stages: [
                        { stage: "initial", branch: "辰", six_relative: "妻财", season_strength: "旺" },
                      ],
                    },
                  }),
                  matchedEntry({
                    rule_id: "LM-R09",
                    observation: {
                      wealth_void_rows: [
                        { stage: "initial", branch: "辰", six_relative: "妻财", is_xunkong: true },
                      ],
                    },
                  }),
                  matchedEntry({
                    rule_id: "LM-R02",
                    observation: { stage: "middle", branch: "午", is_xunkong: true },
                  }),
                ],
              }),
            }),
            state: dimension({
              canonical_dimension: "state",
              requested_dimension: "state",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LM-R01",
                    observation: {
                      matched_count: 1,
                      stages: ["initial"],
                      correspondences: [correspondence],
                    },
                  }),
                ],
              }),
            }),
            work: boundWorkProjection(),
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByRole("group", { name: "结果" })).toHaveTextContent("结构关系：主体克客体");
    expect(within(block).getByRole("group", { name: "结果" })).toHaveTextContent(
      "三传与日干关系：三传支均生日干",
    );
    expect(within(block).getByRole("group", { name: "结果" })).toHaveTextContent("中传旬空：午");
    expect(within(block).getByRole("group", { name: "求财" })).toHaveTextContent("妻财入传：初传 辰（旺）");
    expect(within(block).getByRole("group", { name: "求财" })).toHaveTextContent("妻财旬空：初传 辰");
    expect(within(block).getByRole("group", { name: "状态" })).toHaveTextContent(
      "天将落地类象：初传 勾陈落辰 · 共 1 条",
    );
    expect(within(block).getByRole("group", { name: "事业" })).toHaveTextContent(
      "工作所取六亲：官鬼 · 入传状态：中传 酉（囚，非旬空）、末传 亥（强弱未提供，旬空） · 天将落地类象：中传 天后落酉、末传 白虎落亥（无精确类象对应）",
    );
    expect(block).not.toHaveTextContent(
      /subject_overcomes_object|subject_generates_object|wealth_presence|matched_count|target_relative|source_correspondence_matched/,
    );
    expect(block).not.toHaveTextContent(/outcome|money|state|work/);
    expect(block).not.toHaveTextContent(/吉凶|成败|大吉|大凶|hard_verdict/);
  });

  it.each([
    ["work", "官鬼"],
    ["career", "官鬼"],
    ["work", "父母"],
    ["career", "父母"],
  ] as const)(
    "renders the complete bound %s projection for a %s target without inventing a verdict",
    (requestedDimension, targetRelative) => {
      render(
        <DaliurenBoard
          view={chart({
            core_facts: factsWithDimensions({
              work: boundWorkProjection(requestedDimension, targetRelative),
            }),
          })}
        />,
      );

      const work = within(panel()).getByRole("group", { name: "事业" });
      expect(work).toHaveTextContent("日干与日支：甲（木）与寅（木）：五行同类");
      expect(work).toHaveTextContent("三传六亲：初传 辰 · 妻财；中传 酉 · 官鬼；末传 亥 · 官鬼");
      expect(work).toHaveTextContent(
        "三传状态：初传 辰 · 六亲妻财 · 天将勾陈 · 旺 · 非旬空；中传 酉 · 六亲官鬼 · 天将天后 · 囚 · 非旬空；末传 亥 · 六亲官鬼 · 天将白虎 · 强弱未提供 · 旬空",
      );
      expect(within(work).getByText("LR-19")).toBeVisible();
      expect(work).toHaveTextContent(
        targetRelative === "官鬼"
          ? "工作所取六亲：官鬼 · 入传状态"
          : "工作所取六亲：父母 · 未入三传",
      );
      expect(work).not.toHaveTextContent(
        /target_relative|target_presence|target_strength|subject_object_relation|吉凶|成败|保证|硬判/,
      );
    },
  );

  it("deduplicates career and work alias blocks into one 事业 group", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            career: boundWorkProjection("career", "官鬼"),
            work: boundWorkProjection("work", "官鬼"),
          }),
        })}
      />,
    );

    const work = within(panel()).getByRole("group", { name: "事业" });
    expect(within(panel()).getAllByRole("group", { name: "事业" })).toHaveLength(1);
    expect(within(work).getAllByText(/工作所取六亲：官鬼/).length).toBe(1);
    expect(within(work).getAllByText(/日干与日支：甲（木）与寅（木）：五行同类/).length).toBe(1);
    expect(within(work).getAllByText(/三传六亲：初传 辰 · 妻财/).length).toBe(1);
    expect(work).not.toHaveTextContent(/canonical_dimension|requested_dimension|吉凶|成败|保证|硬判/);
  });

  it("fails the whole bound work group closed for malformed, drifting or unbound evidence", () => {
    const mutate = (change: (projection: Record<string, unknown>) => void) => {
      const projection = structuredClone(boundWorkProjection()) as Record<string, unknown>;
      change(projection);
      return projection;
    };
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            extra_field: mutate((projection) => {
              projection.raw_dump = "不得展示 work extra";
            }),
            invalid_branch: mutate((projection) => {
              const rows = projection.six_relative_stages as Record<string, unknown>[];
              rows[0] = { ...rows[0], branch: "非法支" };
            }),
            wrong_stage_order: mutate((projection) => {
              const rows = projection.stage_status as Record<string, unknown>[];
              projection.stage_status = [rows[1], rows[0], rows[2]];
            }),
            unknown_general: mutate((projection) => {
              const rows = projection.stage_status as Record<string, unknown>[];
              rows[1] = { ...rows[1], heavenly_general: "未知天将" };
            }),
            cross_field_drift: mutate((projection) => {
              const rows = projection.stage_status as Record<string, unknown>[];
              rows[1] = { ...rows[1], branch: "申" };
            }),
            matched_metadata_drift: mutate((projection) => {
              const envelope = projection.rule_evidence as Record<string, unknown>;
              const matched = envelope.matched as Record<string, unknown>[];
              matched[0] = { ...matched[0], dependency_group: "drift" };
            }),
            matched_observation_drift: mutate((projection) => {
              const envelope = projection.rule_evidence as Record<string, unknown>;
              const matched = envelope.matched as Record<string, unknown>[];
              const observation = matched[0]?.observation as Record<string, unknown>;
              const strengths = observation.target_strength as Record<string, unknown>[];
              matched[0] = {
                ...matched[0],
                observation: {
                  ...observation,
                  target_strength: [{ ...strengths[0], branch: "申" }, ...strengths.slice(1)],
                },
              };
            }),
          }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/不得展示 work extra|工作所取六亲|三传六亲|三传状态/);
  });

  it("appends validated present-money general modifiers in Runtime stage order", async () => {
    const user = userEvent.setup();
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({ money: presentMoneyProjection() }),
        })}
      />,
    );

    const money = within(panel()).getByRole("group", { name: "求财" });
    const rows = [...money.querySelectorAll(":scope > ul > li")].map(
      (row) => row.querySelector("summary")?.textContent ?? row.textContent,
    );
    expect(rows).toHaveLength(4);
    expect(rows[0]).toContain("LM-R20妻财入传：初传 辰（旺）、末传 亥（休）");
    expect(rows[1]).toContain("LM-R20妻财旬空：末传 亥");
    expect(rows[2]).toContain("LM-R01妻财天将落地类象：初传 勾陈落辰");
    expect(rows[3]).toContain("LM-R01妻财天将落地类象：末传 白虎落亥（无精确类象对应）");

    const initialModifier = within(money).getByText("妻财天将落地类象：初传 勾陈落辰").closest("li");
    await user.click((initialModifier as HTMLElement).querySelector("summary") as HTMLElement);
    expect(within(initialModifier as HTMLElement).getByText("san-shi/liuren-miben · LM-R01 · fulltext.md#L10")).toBeVisible();
    expect(money).not.toHaveTextContent(/wealth_general_modifier|source_correspondence_matched|吉凶|成败|保证|hard_verdict/);
  });

  it.each([
    ["extra top-level field", "extra_field"],
    ["non-Runtime stage order", "stage_order"],
    ["unknown heavenly-general enum", "general_enum"],
    ["wealth branch mismatch", "cross_field"],
    ["modifier source drift", "modifier_source"],
    ["matched source drift", "matched_source"],
  ] as const)("fails the whole present-money group closed for %s", (_label, kind) => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({ money: malformedPresentMoneyProjection(kind) }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/妻财入传|妻财天将落地类象|不得展示|未知天将|fulltext\.md#drift/);
  });

  it("merges exact and unavailable top-level state correspondences in Runtime order", () => {
    const initial = {
      stage: "initial",
      heavenly_general: "勾陈",
      landing_branch: "辰",
      source_pack: "san-shi/liuren-miben",
      source_rule: "LM-R01",
      role: "imagery_correspondence_not_observed_activity",
      status: "source_correspondence_matched",
      source_text: "勾陈临辰",
      source_anchor: "fulltext.md#L10",
    };
    const final = {
      ...initial,
      stage: "final",
      heavenly_general: "白虎",
      landing_branch: "亥",
      source_text: "白虎临亥",
      source_anchor: "fulltext.md#L12",
    };
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            state: dimension({
              canonical_dimension: "state",
              requested_dimension: "state",
              status: "calculated_facts_not_verdict",
              source_rule_ids: ["LM-R01", "LR-09"],
              stage_status: [
                stateStatus("initial", "辰", "勾陈", {
                  six_relative: "妻财",
                  season_strength: "旺",
                }),
                stateStatus("middle", "酉", "天空", {
                  six_relative: "官鬼",
                  season_strength: "囚",
                  is_xunkong: true,
                }),
                stateStatus("final", "亥", "白虎", {
                  six_relative: "父母",
                  season_strength: "unknown",
                }),
              ],
              general_landing_correspondences: [
                initial,
                {
                  stage: "middle",
                  heavenly_general: "天空",
                  landing_branch: "酉",
                  source_pack: "san-shi/liuren-miben",
                  source_rule: "LM-R01",
                  role: "imagery_correspondence_not_observed_activity",
                  status: "no_exact_source_correspondence",
                },
                final,
              ],
              rule_evidence: runtimeStateEvidence({
                matched: [
                  matchedEntry({
                    rule_id: "LM-R01",
                    observation: {
                      matched_count: 2,
                      stages: ["initial", "final"],
                      correspondences: [initial, final],
                    },
                  }),
                ],
                status: "matched_evidence",
              }),
            }),
          }),
        })}
      />,
    );

    const state = within(panel()).getByRole("group", { name: "状态" });
    expect(state).toHaveTextContent(
      "三传状态：初传 辰 · 六亲妻财 · 天将勾陈 · 旺 · 非旬空；中传 酉 · 六亲官鬼 · 天将天空 · 囚 · 旬空；末传 亥 · 六亲父母 · 天将白虎 · 强弱未提供 · 非旬空",
    );
    expect(state).toHaveTextContent(
      "天将落地类象：初传 勾陈落辰、中传 天空落酉（缺少精确类象来源）、末传 白虎落亥 · 共 3 条",
    );
    expect(state).not.toHaveTextContent(
      /no_exact_source_correspondence|source_correspondence_matched|season_strength|is_xunkong|hard_verdict|吉凶|成败/,
    );
  });

  it("renders an all-unavailable state group as a neutral source boundary", () => {
    const unavailable = (stage: "initial" | "middle" | "final", branch: string) => ({
      stage,
      heavenly_general: "天空",
      landing_branch: branch,
      source_pack: "san-shi/liuren-miben",
      source_rule: "LM-R01",
      role: "imagery_correspondence_not_observed_activity",
      status: "no_exact_source_correspondence",
    });
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            state: dimension({
              canonical_dimension: "state",
              requested_dimension: "state",
              status: "calculated_facts_not_verdict",
              source_rule_ids: ["LR-09"],
              stage_status: [
                stateStatus("initial", "酉", "天空", { season_strength: "相" }),
                stateStatus("middle", "戌", "天空", {
                  six_relative: "官鬼",
                  season_strength: "死",
                  is_xunkong: true,
                }),
                stateStatus("final", "亥", "天空", {
                  six_relative: "父母",
                  season_strength: "unknown",
                }),
              ],
              general_landing_correspondences: [
                unavailable("initial", "酉"),
                unavailable("middle", "戌"),
                unavailable("final", "亥"),
              ],
              rule_evidence: runtimeStateEvidence(),
            }),
          }),
        })}
      />,
    );

    const state = within(panel()).getByRole("group", { name: "状态" });
    expect(state).toHaveTextContent(
      "三传状态：初传 酉 · 六亲兄弟 · 天将天空 · 相 · 非旬空；中传 戌 · 六亲官鬼 · 天将天空 · 死 · 旬空；末传 亥 · 六亲父母 · 天将天空 · 强弱未提供 · 非旬空",
    );
    expect(state).toHaveTextContent(
      "天将落地类象：初传 天空落酉（缺少精确类象来源）、中传 天空落戌（缺少精确类象来源）、末传 天空落亥（缺少精确类象来源） · 共 3 条",
    );
    expect(state).not.toHaveTextContent(
      /no_exact_source_correspondence|season_strength|is_xunkong|hard_verdict|吉凶|成败|保证/,
    );
  });

  it("fails the whole state group closed for unknown statuses, extra fields or matched drift", () => {
    const exact = {
      stage: "initial",
      heavenly_general: "勾陈",
      landing_branch: "辰",
      source_pack: "san-shi/liuren-miben",
      source_rule: "LM-R01",
      role: "imagery_correspondence_not_observed_activity",
      status: "source_correspondence_matched",
      source_text: "勾陈临辰",
      source_anchor: "fulltext.md#L10",
    };
    const unavailable = (stage: "middle" | "final", branch: string) => ({
      stage,
      heavenly_general: "天空",
      landing_branch: branch,
      source_pack: "san-shi/liuren-miben",
      source_rule: "LM-R01",
      role: "imagery_correspondence_not_observed_activity",
      status: "no_exact_source_correspondence",
    });
    const topLevelState = (rows: readonly unknown[], ruleEvidence: Record<string, unknown>) =>
      dimension({
        canonical_dimension: "state",
        requested_dimension: "state",
        status: "calculated_facts_not_verdict",
        source_rule_ids: ["LM-R01", "LR-09"],
        stage_status: [
          stateStatus("initial", "辰", "勾陈", { six_relative: "妻财", season_strength: "旺" }),
          stateStatus("middle", "酉", "天空", {
            six_relative: "官鬼",
            season_strength: "囚",
            is_xunkong: true,
          }),
          stateStatus("final", "亥", "天空", {
            six_relative: "父母",
            season_strength: "unknown",
          }),
        ],
        general_landing_correspondences: rows,
        rule_evidence: ruleEvidence,
      });
    const matched = runtimeStateEvidence({
      matched: [
        matchedEntry({
          rule_id: "LM-R01",
          observation: {
            matched_count: 1,
            stages: ["initial"],
            correspondences: [exact],
          },
        }),
      ],
      status: "matched_evidence",
    });
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            unknown_status: topLevelState(
              [exact, { ...unavailable("middle", "酉"), status: "future_status" }, unavailable("final", "亥")],
              matched,
            ),
            extra_field: topLevelState(
              [exact, { ...unavailable("middle", "酉"), raw_dump: "不得展示额外字段" }, unavailable("final", "亥")],
              matched,
            ),
            matched_drift: topLevelState(
              [exact, unavailable("middle", "酉"), unavailable("final", "亥")],
              runtimeStateEvidence({
                matched: [
                  matchedEntry({
                    rule_id: "LM-R01",
                    observation: {
                      matched_count: 1,
                      stages: ["initial"],
                      correspondences: [{ ...exact, landing_branch: "巳" }],
                    },
                  }),
                ],
                status: "matched_evidence",
              }),
            ),
          }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/future_status|不得展示额外字段|天将落地类象|raw_dump/);
  });

  it("fails the whole state group closed for malformed, out-of-order or source-drift stage status", () => {
    const initial = {
      stage: "initial",
      heavenly_general: "勾陈",
      landing_branch: "辰",
      source_pack: "san-shi/liuren-miben",
      source_rule: "LM-R01",
      role: "imagery_correspondence_not_observed_activity",
      status: "source_correspondence_matched",
      source_text: "勾陈临辰",
      source_anchor: "fulltext.md#L10",
    };
    const unavailable = (stage: "middle" | "final", branch: string, general: string) => ({
      stage,
      heavenly_general: general,
      landing_branch: branch,
      source_pack: "san-shi/liuren-miben",
      source_rule: "LM-R01",
      role: "imagery_correspondence_not_observed_activity",
      status: "no_exact_source_correspondence",
    });
    const correspondences = [initial, unavailable("middle", "酉", "天空"), unavailable("final", "亥", "白虎")];
    const statusRows = [
      stateStatus("initial", "辰", "勾陈", { six_relative: "妻财", season_strength: "旺" }),
      stateStatus("middle", "酉", "天空", {
        six_relative: "官鬼",
        season_strength: "囚",
        is_xunkong: true,
      }),
      stateStatus("final", "亥", "白虎", {
        six_relative: "父母",
        season_strength: "unknown",
      }),
    ];
    const matched = runtimeStateEvidence({
      matched: [
        matchedEntry({
          rule_id: "LM-R01",
          observation: {
            matched_count: 1,
            stages: ["initial"],
            correspondences: [initial],
          },
        }),
      ],
      status: "matched_evidence",
    });
    const projection = (overrides: Record<string, unknown> = {}) =>
      dimension({
        canonical_dimension: "state",
        requested_dimension: "state",
        status: "calculated_facts_not_verdict",
        source_rule_ids: ["LM-R01", "LR-09"],
        stage_status: statusRows,
        general_landing_correspondences: correspondences,
        rule_evidence: matched,
        ...overrides,
      });

    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            missing_rows: projection({ stage_status: [] }),
            extra_field: projection({
              stage_status: [{ ...statusRows[0], raw_dump: "不得展示状态原始字段" }, ...statusRows.slice(1)],
            }),
            unknown_strength: projection({
              stage_status: [statusRows[0], { ...statusRows[1], season_strength: "未来旺衰" }, statusRows[2]],
            }),
            malformed_void: projection({
              stage_status: [statusRows[0], { ...statusRows[1], is_xunkong: "true" }, statusRows[2]],
            }),
            wrong_stage_order: projection({
              stage_status: [statusRows[1], statusRows[0], statusRows[2]],
            }),
            cross_field_drift: projection({
              stage_status: [statusRows[0], { ...statusRows[1], branch: "午" }, statusRows[2]],
            }),
            source_rule_drift: projection({
              source_rule_ids: ["LR-09", "LM-R01"],
            }),
            evidence_source_drift: projection({
              rule_evidence: { ...matched, catalog_schema: "future-evidence-schema" },
            }),
          }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(
      /不得展示状态原始字段|未来旺衰|future-evidence-schema|三传状态|天将落地类象|raw_dump/,
    );
  });

  it("renders the Runtime location shape as neutral symbolic direction candidates with source boundaries", async () => {
    const user = userEvent.setup();
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            location: dimension({
              canonical_dimension: "location",
              requested_dimension: "location",
              rule_evidence: evidence({ matched: [], status: "not_bound" }),
              stage_branch_directions: [
                {
                  stage: "initial",
                  branch: "酉",
                  direction: "west",
                  direction_chinese: "正西",
                  declared_source_anchor: "liuren-miben L573",
                  source_binding_status: "unverified_source_excerpt_not_in_release",
                  scope: "symbolic_direction_candidate_only",
                },
                {
                  stage: "middle",
                  branch: "未",
                  direction: "southwest",
                  direction_chinese: "西南",
                  declared_source_anchor: "liuren-miben L569",
                  source_binding_status: "unverified_source_excerpt_not_in_release",
                  scope: "symbolic_direction_candidate_only",
                },
                {
                  stage: "final",
                  branch: "巳",
                  direction: "southeast",
                  direction_chinese: "东南",
                  declared_source_anchor: "liuren-miben L565",
                  source_binding_status: "unverified_source_excerpt_not_in_release",
                  scope: "symbolic_direction_candidate_only",
                },
              ],
            }),
          }),
        })}
      />,
    );

    const location = within(panel()).getByRole("group", { name: "方位" });
    expect(within(location).getByText("方位候选")).toBeVisible();
    expect(location).toHaveTextContent(
      "三传象意方位候选：初传 酉 · 正西；中传 未 · 西南；末传 巳 · 东南 · 边界：只表示地支对应的象意方向；来源摘录尚未纳入签名发行",
    );
    expect(location).not.toHaveTextContent(
      /west|southwest|southeast|symbolic_direction_candidate_only|unverified_source_excerpt_not_in_release/,
    );

    await user.click(within(location).getByText("方位候选"));
    expect([...location.querySelectorAll("[data-source-ref]")].map((row) => row.textContent)).toEqual([
      "来源标注 · liuren-miben L573",
      "来源标注 · liuren-miben L569",
      "来源标注 · liuren-miben L565",
    ]);
  });

  it("renders typed no-match money, work and timing facts without inventing a verdict", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            money: dimension({
              canonical_dimension: "money",
              requested_dimension: "money",
              source_rule_ids: ["LM-R20"],
              wealth_presence: false,
              wealth_stage_strength: [],
              wealth_void_status: [],
              wealth_general_modifier: [],
              rule_evidence: evidence({
                matched: [],
                status: "scope_boundary",
                scope_boundaries: [
                  matchedEntry({
                    rule_id: "LM-R20",
                    status: "scope_boundary",
                    observation: { wealth_presence: false },
                  }),
                ],
              }),
            }),
            timing: dimension({
              canonical_dimension: "timing",
              requested_dimension: "timing",
              source_rule_ids: ["DLR-16"],
              relative_speed: "relatively_faster",
              rule_evidence: evidence({ matched: [], status: "not_bound" }),
            }),
            work: boundWorkProjection("work", "父母"),
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByRole("group", { name: "求财" })).toHaveTextContent("妻财未入三传");
    expect(within(block).getByRole("group", { name: "事业" })).toHaveTextContent(
      "工作所取六亲：父母 · 未入三传",
    );
    expect(within(block).getByRole("group", { name: "时机" })).toHaveTextContent("相对节奏：较快");
    expect(block).not.toHaveTextContent(/wealth_presence|target_presence|relative_speed|吉凶|成败|保证/);
  });

  it("fails closed when no-match deterministic fields disagree with their typed scope boundary", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            money: dimension({
              canonical_dimension: "money",
              requested_dimension: "money",
              source_rule_ids: ["LM-R20"],
              wealth_presence: false,
              wealth_stage_strength: [],
              wealth_void_status: [],
              wealth_general_modifier: [],
              rule_evidence: evidence({
                matched: [],
                status: "scope_boundary",
                scope_boundaries: [
                  matchedEntry({
                    rule_id: "LM-R20",
                    status: "scope_boundary",
                    observation: { wealth_presence: true },
                  }),
                ],
              }),
            }),
            timing: dimension({
              canonical_dimension: "timing",
              requested_dimension: "timing",
              source_rule_ids: ["DLR-16"],
              relative_speed: "unresolved",
              candidate_branch: null,
              candidate_date: null,
              rule_evidence: evidence({ matched: [], status: "not_bound" }),
            }),
            work: dimension({
              canonical_dimension: "work",
              requested_dimension: "work",
              source_rule_ids: [],
              target_relative: "官鬼",
              target_contract_status: "bound",
              target_presence: false,
              target_strength: [],
              target_general_modifier: [],
              rule_evidence: evidence({
                matched: [],
                status: "scope_boundary",
                scope_boundaries: [
                  matchedEntry({
                    rule_id: "LR-19",
                    status: "scope_boundary",
                    observation: {
                      target_relative: "妻财",
                      target_presence: false,
                      target_contract_status: "bound",
                    },
                  }),
                ],
              }),
            }),
          }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/妻财未入三传|工作所取六亲|相对节奏|unresolved/);
  });

  it("keeps compatible wealth-absence and middle-transmission void observations", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            money: dimension({
              canonical_dimension: "money",
              requested_dimension: "money",
              source_rule_ids: ["LM-R10", "MINGLI-LR-SCOPE-02"],
              wealth_presence: false,
              wealth_stage_strength: [],
              wealth_void_status: [],
              wealth_general_modifier: [],
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LM-R10",
                    observation: { stage: "middle", branch: "未", is_xunkong: true },
                  }),
                ],
                status: "matched",
                scope_boundaries: [
                  matchedEntry({
                    rule_id: "MINGLI-LR-SCOPE-02",
                    status: "scope_boundary",
                    observation: { wealth_presence: false },
                  }),
                ],
              }),
            }),
          }),
        })}
      />,
    );

    const money = within(panel()).getByRole("group", { name: "求财" });
    expect(money).toHaveTextContent("妻财未入三传");
    expect(money).toHaveTextContent("中传旬空：未");
    expect(money).not.toHaveTextContent(/wealth_presence|stage|is_xunkong/);
  });

  it("renders typed top-level outcome facts when no judgment rule matches", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            outcome: dimension({
              canonical_dimension: "outcome",
              requested_dimension: "outcome",
              status: "calculated_facts_not_verdict",
              source_rule_ids: [],
              subject_object_relation: {
                subject: "day_stem",
                subject_value: "甲",
                subject_element: "木",
                object: "day_branch",
                object_value: "寅",
                object_element: "木",
                relation: "same_element",
              },
              transmissions_to_day: [
                {
                  stage: "initial",
                  subject: "transmission_branch",
                  subject_value: "巳",
                  subject_element: "火",
                  object: "day_stem",
                  object_value: "甲",
                  object_element: "木",
                  relation: "object_generates_subject",
                },
                {
                  stage: "middle",
                  subject: "transmission_branch",
                  subject_value: "申",
                  subject_element: "金",
                  object: "day_stem",
                  object_value: "甲",
                  object_element: "木",
                  relation: "subject_overcomes_object",
                },
                {
                  stage: "final",
                  subject: "transmission_branch",
                  subject_value: "卯",
                  subject_element: "木",
                  object: "day_stem",
                  object_value: "甲",
                  object_element: "木",
                  relation: "same_element",
                },
              ],
              initial_final_relation: {
                subject: "initial_branch",
                subject_value: "巳",
                subject_element: "火",
                object: "final_branch",
                object_value: "卯",
                object_element: "木",
                relation: "object_generates_subject",
              },
              stage_flow: [
                {
                  from_stage: "initial",
                  to_stage: "middle",
                  subject: "from_branch",
                  subject_value: "巳",
                  subject_element: "火",
                  object: "to_branch",
                  object_value: "申",
                  object_element: "金",
                  relation: "subject_overcomes_object",
                },
                {
                  from_stage: "middle",
                  to_stage: "final",
                  subject: "from_branch",
                  subject_value: "申",
                  subject_element: "金",
                  object: "to_branch",
                  object_value: "卯",
                  object_element: "木",
                  relation: "subject_overcomes_object",
                },
              ],
              rule_evidence: runtimeStateEvidence({ status: "not_calculated" }),
            }),
          }),
        })}
      />,
    );

    const outcome = within(panel()).getByRole("group", { name: "结果" });
    expect(outcome).toHaveTextContent("日干与日支：甲（木）与寅（木）：五行同类");
    expect(outcome).toHaveTextContent("三传与日干：初传 巳（火）与甲（木）：后者生前者");
    expect(outcome).toHaveTextContent("初末关系：巳（火）与卯（木）：后者生前者");
    expect(outcome).toHaveTextContent("三传流转：初传至中传 巳（火）与申（金）：前者克后者");
    expect(outcome).not.toHaveTextContent(/same_element|object_generates_subject|subject_overcomes_object|吉凶|成败|保证/);
  });

  it("preserves validated top-level outcome facts and matched source evidence together", async () => {
    const user = userEvent.setup();
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({ outcome: matchedOutcomeProjection() }),
        })}
      />,
    );

    const outcome = within(panel()).getByRole("group", { name: "结果" });
    expect(outcome).toHaveTextContent("LR-17");
    expect(outcome).toHaveTextContent("结构关系：客体克主体");
    expect(outcome).toHaveTextContent("日干与日支：甲（木）与申（金）：后者克前者");
    expect(outcome).toHaveTextContent("三传与日干：初传 巳（火）与甲（木）：后者生前者");
    expect(outcome).toHaveTextContent("初末关系：巳（火）与卯（木）：后者生前者");
    expect(outcome).toHaveTextContent("三传流转：初传至中传 巳（火）与申（金）：前者克后者");

    const matched = within(outcome).getByText("结构关系：客体克主体").closest("details");
    expect(matched).not.toBeNull();
    await user.click((matched as HTMLElement).querySelector("summary") as HTMLElement);
    expect(within(matched as HTMLElement).getByText(/san-shi\/liuren-zhiyin · LR-17 · LZ-Q054/)).toBeVisible();
    expect(outcome).not.toHaveTextContent(/object_overcomes_subject|hard_verdict|吉凶|成败|保证/);
  });

  it("fails closed for malformed or internally inconsistent top-level outcome facts", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            outcome: dimension({
              canonical_dimension: "outcome",
              requested_dimension: "outcome",
              status: "calculated_facts_not_verdict",
              source_rule_ids: [],
              subject_object_relation: {
                subject: "day_stem",
                subject_value: "甲",
                subject_element: "木",
                object: "day_branch",
                object_value: "寅",
                object_element: "木",
                relation: "same_element",
                raw_dump: "不得展示",
              },
              transmissions_to_day: [],
              initial_final_relation: {},
              stage_flow: [],
              rule_evidence: evidence({ matched: [], status: "not_bound" }),
            }),
          }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/不得展示|日干与日支|三传与日干|初末关系|三传流转/);
  });

  it("renders typed top-level relationship facts when no judgment rule matches", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            relationship: dimension({
              canonical_dimension: "relationship",
              requested_dimension: "relationship",
              status: "calculated_facts_not_verdict",
              source_rule_ids: [],
              subject_object_relation: {
                subject: "day_stem",
                subject_value: "甲",
                subject_element: "木",
                object: "day_branch",
                object_value: "寅",
                object_element: "木",
                relation: "same_element",
              },
              six_relative_stages: [
                { stage: "initial", branch: "巳", six_relative: "子孙" },
                { stage: "middle", branch: "申", six_relative: "官鬼" },
                { stage: "final", branch: "子", six_relative: "父母" },
              ],
              stage_flow: [
                {
                  from_stage: "initial",
                  to_stage: "middle",
                  subject: "from_branch",
                  subject_value: "巳",
                  subject_element: "火",
                  object: "to_branch",
                  object_value: "申",
                  object_element: "金",
                  relation: "subject_overcomes_object",
                },
                {
                  from_stage: "middle",
                  to_stage: "final",
                  subject: "from_branch",
                  subject_value: "申",
                  subject_element: "金",
                  object: "to_branch",
                  object_value: "子",
                  object_element: "水",
                  relation: "subject_generates_object",
                },
              ],
              rule_evidence: evidence({
                matched: [],
                requires_school_adjudication: true,
                status: "not_bound",
              }),
            }),
          }),
        })}
      />,
    );

    const relationship = within(panel()).getByRole("group", { name: "关系" });
    expect(relationship).toHaveTextContent("日干与日支：甲（木）与寅（木）：五行同类");
    expect(relationship).toHaveTextContent("三传六亲：初传 巳 · 子孙；中传 申 · 官鬼；末传 子 · 父母");
    expect(relationship).toHaveTextContent("三传流转：初传至中传 巳（火）与申（金）：前者克后者");
    expect(relationship).not.toHaveTextContent(
      /same_element|subject_generates_object|subject_overcomes_object|six_relative_stages|stage_flow|吉凶|成败|保证/,
    );
  });

  it("fails the whole relationship group closed for malformed or conflicting top-level projections", () => {
    const validProjection = {
      canonical_dimension: "relationship",
      requested_dimension: "relationship",
      status: "calculated_facts_not_verdict",
      source_rule_ids: [] as string[],
      subject_object_relation: {
        subject: "day_stem",
        subject_value: "甲",
        subject_element: "木",
        object: "day_branch",
        object_value: "寅",
        object_element: "木",
        relation: "same_element",
      },
      six_relative_stages: [
        { stage: "initial", branch: "巳", six_relative: "子孙" },
        { stage: "middle", branch: "申", six_relative: "官鬼" },
        { stage: "final", branch: "子", six_relative: "父母" },
      ],
      stage_flow: [
        {
          from_stage: "initial",
          to_stage: "middle",
          subject: "from_branch",
          subject_value: "巳",
          subject_element: "火",
          object: "to_branch",
          object_value: "申",
          object_element: "金",
          relation: "subject_overcomes_object",
        },
        {
          from_stage: "middle",
          to_stage: "final",
          subject: "from_branch",
          subject_value: "申",
          subject_element: "金",
          object: "to_branch",
          object_value: "子",
          object_element: "水",
          relation: "subject_generates_object",
        },
      ],
      rule_evidence: evidence({
        matched: [],
        requires_school_adjudication: true,
        status: "not_bound",
      }),
    };
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            extra_field: { ...validProjection, raw_dump: "不得展示额外字段" },
            unknown_relative: {
              ...validProjection,
              six_relative_stages: [
                { stage: "initial", branch: "巳", six_relative: "未来枚举" },
                ...validProjection.six_relative_stages.slice(1),
              ],
            },
            wrong_stage_order: {
              ...validProjection,
              six_relative_stages: [
                validProjection.six_relative_stages[1],
                validProjection.six_relative_stages[0],
                validProjection.six_relative_stages[2],
              ],
            },
            cross_field_drift: {
              ...validProjection,
              stage_flow: [
                { ...validProjection.stage_flow[0], subject_value: "午" },
                validProjection.stage_flow[1],
              ],
            },
            invalid_branch: {
              ...validProjection,
              six_relative_stages: [
                { ...validProjection.six_relative_stages[0], branch: "非法支" },
                ...validProjection.six_relative_stages.slice(1),
              ],
              stage_flow: [
                { ...validProjection.stage_flow[0], subject_value: "非法支" },
                validProjection.stage_flow[1],
              ],
            },
            invalid_stem: {
              ...validProjection,
              subject_object_relation: {
                ...validProjection.subject_object_relation,
                subject_value: "非法干",
              },
            },
            branch_element_drift: {
              ...validProjection,
              stage_flow: [
                {
                  ...validProjection.stage_flow[0],
                  subject_element: "水",
                  object_element: "木",
                  relation: "subject_generates_object",
                },
                validProjection.stage_flow[1],
              ],
            },
            stem_element_drift: {
              ...validProjection,
              subject_object_relation: {
                ...validProjection.subject_object_relation,
                subject_element: "水",
                relation: "subject_generates_object",
              },
            },
            day_branch_element_drift: {
              ...validProjection,
              subject_object_relation: {
                ...validProjection.subject_object_relation,
                object_element: "火",
                relation: "subject_generates_object",
              },
            },
            matched_conflict: {
              ...validProjection,
              source_rule_ids: ["LR-17"],
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LR-17",
                    observation: { relation: "object_overcomes_subject" },
                  }),
                ],
                requires_school_adjudication: true,
                status: "matched_evidence",
              }),
            },
          }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/不得展示额外字段|未来枚举|日干与日支|三传六亲|主客关系/);
  });

  it.each(["work", "career"] as const)(
    "renders the neutral missing-target boundary for a public %s request",
    (requestedDimension) => {
      render(
        <DaliurenBoard
          view={chart({
            core_facts: factsWithDimensions({ work: missingWorkProjection(requestedDimension) }),
          })}
        />,
      );

      const work = within(panel()).getByRole("group", { name: "事业" });
      expect(work).toHaveTextContent("目标边界");
      expect(work).toHaveTextContent("未绑定目标六亲");
      expect(work).not.toHaveTextContent(
        /missing_target_relative|required_fact_missing|work_target_relative_not_supplied|吉凶|成败|保证|硬判/,
      );
    },
  );

  it("fails matched and missing-target groups closed for extra fields or top-level conflicts", () => {
    const outcome = matchedOutcomeProjection();
    const outcomeEvidence = outcome.rule_evidence;
    const outcomeMatched = outcomeEvidence.matched;
    if (!Array.isArray(outcomeMatched) || !isRecord(outcomeMatched[0])) {
      throw new Error("Daliuren matched outcome fixture has no evidence record");
    }
    const relationship = goldenDimensionFacts().relationship;
    if (!isRecord(relationship) || !isRecord(relationship.rule_evidence)) {
      throw new Error("Daliuren Runtime golden fixture has no relationship evidence");
    }
    const relationshipMatched = relationship.rule_evidence.matched;
    if (!Array.isArray(relationshipMatched) || !isRecord(relationshipMatched[0])) {
      throw new Error("Daliuren Runtime golden fixture has no relationship match");
    }
    const missingWork = missingWorkProjection();

    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            outcome_extra: { ...outcome, raw_dump: "不得展示 outcome extra" },
            outcome_conflict: {
              ...outcome,
              rule_evidence: {
                ...outcomeEvidence,
                matched: [
                  matchedEntry({
                    activation_id: "liuren.subject_object.day_overcomes_branch",
                    dependency_group: "liuren.subject_object_relation",
                    fact_paths: ["dimension_facts.outcome.subject_object_relation"],
                    observation: { relation: "subject_overcomes_object" },
                    rule_id: "LR-17",
                    rule_key: "day_stem_overcomes_branch",
                    source_refs: [
                      {
                        pack: "san-shi/liuren-zhiyin",
                        rule_id: "LR-17",
                        quote_id: "LZ-Q054",
                        source_anchor: "fulltext.md#L557",
                      },
                    ],
                  }),
                ],
              },
            },
            outcome_matched_extra: {
              ...outcome,
              rule_evidence: {
                ...outcomeEvidence,
                matched: [{ ...outcomeMatched[0], raw_dump: "不得展示 matched extra" }],
              },
            },
            relationship_extra: { ...relationship, raw_dump: "不得展示 relationship extra" },
            relationship_conflict: {
              ...relationship,
              rule_evidence: {
                ...relationship.rule_evidence,
                matched: [
                  {
                    ...relationshipMatched[0],
                    observation: { relation: "subject_overcomes_object" },
                  },
                ],
              },
            },
            work_extra: { ...missingWork, raw_dump: "不得展示 work extra" },
            work_conflict: {
              ...missingWork,
              stage_status: [
                { ...missingWork.stage_status[0], branch: "午" },
                ...missingWork.stage_status.slice(1),
              ],
            },
          }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/不得展示|结构关系|三传六亲|未绑定目标六亲/);
  });

  it.each([
    [
      "money",
      dimension({
        canonical_dimension: "money",
        requested_dimension: "money",
        source_rule_ids: ["LM-R20"],
        wealth_presence: false,
        wealth_stage_strength: [],
        wealth_void_status: [],
        wealth_general_modifier: [],
        rule_evidence: evidence({
          matched: [
            matchedEntry({
              rule_id: "LM-R20",
              observation: {
                wealth_presence: true,
                wealth_stages: [
                  { stage: "initial", branch: "酉", six_relative: "妻财", season_strength: "旺" },
                ],
              },
            }),
          ],
          status: "scope_boundary",
          scope_boundaries: [
            matchedEntry({
              rule_id: "LM-R20",
              status: "scope_boundary",
              observation: { wealth_presence: false },
            }),
          ],
        }),
      }),
    ],
    [
      "work",
      dimension({
        canonical_dimension: "work",
        requested_dimension: "work",
        source_rule_ids: [],
        target_relative: "官鬼",
        target_contract_status: "bound",
        target_presence: false,
        target_strength: [],
        target_general_modifier: [],
        rule_evidence: evidence({
          matched: [
            matchedEntry({
              rule_id: "LR-19",
              observation: {
                target_relative: "官鬼",
                target_strength: [
                  {
                    stage: "initial",
                    branch: "酉",
                    six_relative: "官鬼",
                    season_strength: "旺",
                    is_xunkong: false,
                  },
                ],
                target_general_modifier: [],
              },
            }),
          ],
          status: "scope_boundary",
          scope_boundaries: [
            matchedEntry({
              rule_id: "LR-19",
              status: "scope_boundary",
              observation: {
                target_relative: "官鬼",
                target_presence: false,
                target_contract_status: "bound",
              },
            }),
          ],
        }),
      }),
    ],
  ])("fails closed when %s no-match boundaries conflict with matched facts", (_dimension, block) => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({ contradiction: block }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/妻财入传|妻财未入三传|工作所取六亲|入传状态/);
  });

  it("fails closed when a location row breaks the typed candidate or source-boundary contract", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            keep: dimension({
              canonical_dimension: "relationship",
              requested_dimension: "relationship",
              rule_evidence: evidence({
                matched: [matchedEntry({ observation: { relation: "object_overcomes_subject" } })],
              }),
            }),
            malformed_location: dimension({
              canonical_dimension: "location",
              requested_dimension: "location",
              rule_evidence: evidence({ matched: [], status: "not_bound" }),
              stage_branch_directions: [
                {
                  stage: "initial",
                  branch: "酉",
                  direction: "west",
                  direction_chinese: "正东",
                  declared_source_anchor: "liuren-miben L573",
                  source_binding_status: "unverified_source_excerpt_not_in_release",
                  scope: "symbolic_direction_candidate_only",
                },
                {
                  stage: "middle",
                  branch: "未",
                  direction: "southwest",
                  direction_chinese: "西南",
                  declared_source_anchor: "liuren-miben L569",
                  source_binding_status: "unverified_source_excerpt_not_in_release",
                  scope: "symbolic_direction_candidate_only",
                },
                {
                  stage: "final",
                  branch: "巳",
                  direction: "southeast",
                  direction_chinese: "东南",
                  declared_source_anchor: "liuren-miben L565",
                  source_binding_status: "verified",
                  scope: "actual_location",
                },
              ],
            }),
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByRole("group", { name: "关系" })).toBeVisible();
    expect(within(block).queryByRole("group", { name: "方位" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/actual_location|verified|正东/);
  });

  it("continues to fail closed for a truly unknown canonical dimension instead of exposing its id or generic text", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            unknown: dimension({
              canonical_dimension: "future_signal",
              requested_dimension: "future_signal",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "FUTURE-1",
                    observation: { display_text: "不得展示未知维度" },
                  }),
                ],
              }),
            }),
          }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(screen.queryByText("future_signal")).not.toBeInTheDocument();
    expect(screen.queryByText("不得展示未知维度")).not.toBeInTheDocument();
  });

  it("fails closed for unknown, extra or inconsistent outcome, money, state and work observations", () => {
    const correspondence = {
      stage: "initial",
      heavenly_general: "勾陈",
      landing_branch: "辰",
      source_pack: "san-shi/liuren-miben",
      source_rule: "LM-R01",
      role: "imagery_correspondence_not_observed_activity",
      status: "source_correspondence_matched",
      source_text: "勾陈临辰",
      source_anchor: "fulltext.md#L10",
    };
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            outcome: dimension({
              canonical_dimension: "outcome",
              requested_dimension: "outcome",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    observation: {
                      relations: [
                        "subject_generates_object",
                        "subject_generates_object",
                        "subject_generates_object",
                      ],
                      raw_dump: "不得展示 outcome",
                    },
                  }),
                ],
              }),
            }),
            money: dimension({
              canonical_dimension: "money",
              requested_dimension: "money",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    observation: {
                      wealth_presence: true,
                      wealth_stages: [
                        {
                          stage: "initial",
                          branch: "辰",
                          six_relative: "妻财",
                          season_strength: "旺",
                          extra: "不得展示 money",
                        },
                      ],
                    },
                  }),
                ],
              }),
            }),
            state: dimension({
              canonical_dimension: "state",
              requested_dimension: "state",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    observation: {
                      matched_count: 2,
                      stages: ["initial"],
                      correspondences: [correspondence],
                    },
                  }),
                ],
              }),
            }),
            work: dimension({
              canonical_dimension: "work",
              requested_dimension: "work",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    observation: {
                      target_relative: "官鬼",
                      target_strength: [
                        {
                          stage: "middle",
                          branch: "酉",
                          six_relative: "官鬼",
                          season_strength: "囚",
                          is_xunkong: false,
                        },
                      ],
                      target_general_modifier: [
                        { ...correspondence, six_relative: "官鬼", extra: "不得展示 work" },
                      ],
                    },
                  }),
                ],
              }),
            }),
          }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/不得展示|subject_generates_object|wealth_presence|matched_count|target_relative/);
  });

  it("fails closed for extra or malformed relationship and timing observation fields", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            relationship: dimension({
              canonical_dimension: "relationship",
              requested_dimension: "relationship",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LR-17",
                    observation: { relation: "object_overcomes_subject", raw_dump: "不得展示" },
                  }),
                ],
              }),
            }),
            timing: dimension({
              canonical_dimension: "timing",
              requested_dimension: "timing",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LM-R21",
                    observation: {
                      candidate_branch: { branch: "未" },
                      candidate_date: null,
                      relative_speed: "relatively_faster",
                    },
                  }),
                ],
              }),
            }),
          }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(screen.queryByText("不得展示")).not.toBeInTheDocument();
    expect(screen.queryByText(/object_overcomes_subject|relatively_faster/)).not.toBeInTheDocument();
  });

  it("renders grouped matched facts with rule id and observation, and hides not_evaluated", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            relationship: dimension({
              canonical_dimension: "relationship",
              requested_dimension: "relationship",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LR-17",
                    observation: { relation: "object_overcomes_subject" },
                    source_refs: [{ pack: "san-shi/liuren-zhiyin", rule_id: "LR-17" }],
                  }),
                ],
              }),
            }),
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByRole("group", { name: "关系" })).toBeVisible();
    expect(within(block).getByText("LR-17")).toBeVisible();
    expect(within(block).getByText("主客关系：客体克主体")).toBeVisible();
    expect(within(block).queryByText("SKIP-9")).not.toBeInTheDocument();
    expect(within(block).queryByText("not requested")).not.toBeInTheDocument();
    expect(within(block).queryByText("暂无证据")).not.toBeInTheDocument();
    expect(within(block).queryByText(/吉凶|成败|大吉|大凶|hard_verdict/)).not.toBeInTheDocument();
    expect(screen.queryByText("dimension_facts")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-DL/)).not.toBeInTheDocument();
  });

  it("drops a dimension when hard_verdict is not null or the block shape is incomplete", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            bad_verdict: dimension({
              canonical_dimension: "timing",
              rule_evidence: evidence({ hard_verdict: "auspicious" }),
            }),
            missing_requested: {
              canonical_dimension: "relationship",
              rule_evidence: evidence(),
            },
            keep: dimension({
              canonical_dimension: "relationship",
              requested_dimension: "relationship",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LR-17",
                    observation: { relation: "object_overcomes_subject" },
                  }),
                ],
              }),
            }),
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).queryByRole("group", { name: "时机" })).not.toBeInTheDocument();
    expect(within(block).queryByText("auspicious")).not.toBeInTheDocument();
    expect(within(block).getByRole("group", { name: "关系" })).toBeVisible();
    expect(within(block).getByText("主客关系：客体克主体")).toBeVisible();
  });

  it("drops matched rows without a rule id or with malformed observation keys", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            relationship: dimension({
              canonical_dimension: "relationship",
              requested_dimension: "relationship",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({ rule_id: "", observation: { relation: "object_overcomes_subject" } }),
                  matchedEntry({ rule_id: "LM-R01", observation: { primary: "发明事实" } }),
                  matchedEntry({
                    rule_id: "LR-17",
                    observation: { relation: "object_overcomes_subject" },
                  }),
                ],
              }),
            }),
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).queryByText("发明事实")).not.toBeInTheDocument();
    expect(within(block).getByText("LR-17")).toBeVisible();
    expect(within(block).getByText("主客关系：客体克主体")).toBeVisible();
  });

  it("preserves every Runtime source ref in order without claiming exact verification", async () => {
    const user = userEvent.setup();
    const stateSources = runtimeRuleSourceRefs("state_general_landing_correspondence");
    const moneySources = runtimeRuleSourceRefs("wealth_void_miben");
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            outcome: dimension({
              canonical_dimension: "outcome",
              requested_dimension: "outcome",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LM-R01",
                    observation: { relation: "subject_overcomes_object" },
                    source_refs: stateSources,
                  }),
                  matchedEntry({
                    rule_id: "LM-R20",
                    observation: { stage: "middle", branch: "午", is_xunkong: true },
                    source_refs: moneySources,
                  }),
                ],
              }),
            }),
          }),
        })}
      />,
    );

    const block = panel();
    const stateEntry = within(block).getByText("结构关系：主体克客体").closest("li");
    const moneyEntry = within(block).getByText("中传旬空：午").closest("li");
    await user.click((stateEntry as HTMLElement).querySelector("summary") as HTMLElement);
    await user.click((moneyEntry as HTMLElement).querySelector("summary") as HTMLElement);

    const stateRows = [...(stateEntry as HTMLElement).querySelectorAll("[data-source-ref]")];
    expect(stateRows.map((row) => row.textContent)).toEqual([
      "san-shi/liuren-miben · LM-R01 · fulltext.md#L82-L359",
      "san-shi/liuren-miben · LM-R01 · fulltext.md#L600-L771",
    ]);
    const moneyRows = [...(moneyEntry as HTMLElement).querySelectorAll("[data-source-ref]")];
    expect(moneyRows.map((row) => row.textContent)).toEqual([
      "san-shi/liuren-miben · LM-R20 · LM-Q072 · fulltext.md#L4917",
      "san-shi/liuren-miben · LM-R10 · LM-Q051 · fulltext.md#L3568",
    ]);
    expect(block).not.toHaveTextContent(/可核验|原文/);
    expect(block.querySelector("[data-badge='evidence']")).toBeNull();
  });

  it("hides the whole block when nothing is renderable", () => {
    const { rerender } = render(<DaliurenBoard view={chart({ core_facts: emptyFacts() })} />);
    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();

    rerender(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            empty: dimension({
              canonical_dimension: "relationship",
              requested_dimension: "relationship",
              rule_evidence: evidence({ matched: [] }),
            }),
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(screen.queryByText("暂无证据")).not.toBeInTheDocument();
  });

  it("keeps loading and silhouette modes free of dimension evidence", () => {
    const view = chart({
      core_facts: factsWithDimensions({
        relationship: dimension({
          canonical_dimension: "relationship",
          requested_dimension: "relationship",
          rule_evidence: evidence({
            matched: [
              matchedEntry({
                rule_id: "LR-17",
                observation: { relation: "object_overcomes_subject" },
              }),
            ],
          }),
        }),
      }),
    });
    const { rerender } = render(<DaliurenBoard view={view} mode="loading" />);
    expect(screen.queryByText("维度证据")).not.toBeInTheDocument();
    expect(screen.queryByText("LR-17")).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={view} mode="silhouette" />);
    expect(screen.queryByText("LR-17")).not.toBeInTheDocument();
  });

  it("keeps the dimension-evidence module off shared pages", () => {
    const boardSource = readFileSync(resolve(process.cwd(), "src/components/readings/daliuren-board.tsx"), "utf8");
    const evidenceSource = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-dimension-evidence.tsx"),
      "utf8",
    );
    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-dimension-evidence.module.css"),
      "utf8",
    );
    const runtime = readFileSync(resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"), "utf8");
    const experience = readFileSync(resolve(process.cwd(), "src/components/task/product-task-experience.tsx"), "utf8");
    expect(boardSource).toContain("daliuren-dimension-evidence");
    expect(evidenceSource).not.toMatch(/bazi-chart|liuyao-line-tower|runtime-chart|product-task-experience|GAP-DL/);
    expect(css).not.toMatch(/--color-evidence/);
    expect(css).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(css).not.toMatch(/color-success|color-danger|surface-success|surface-danger/);
    expect(css).not.toMatch(/linear-gradient|radial-gradient|box-shadow:\s*0 0/);
    expect(runtime).not.toContain("daliuren-dimension-evidence");
    expect(experience).not.toContain("daliuren-dimension-evidence");
  });
});

describe("大六壬 S3 M7 免费摘要 + 深读入口", () => {
  const OFFER = {
    name: "大六壬课传深读",
    coverage: "当前这张已排出课盘的四课三传",
    priceText: "由服务端标价",
    refundBoundary: "未交付可退",
  };

  function blankLessons(): DaliurenChartViewModel["lessons"] {
    return [
      { lesson_id: "", upper: "", lower: "" },
      { lesson_id: "", upper: "", lower: "" },
      { lesson_id: "", upper: "", lower: "" },
      { lesson_id: "", upper: "", lower: "" },
    ];
  }

  function blankTransmissions(): DaliurenChartViewModel["transmissions"] {
    return [
      { stage: "initial", branch: "", general: "" },
      { stage: "middle", branch: "", general: "" },
      { stage: "final", branch: "", general: "" },
    ];
  }

  function summary() {
    return screen.getByRole("region", { name: "基础摘要" });
  }

  it("restates on-screen lessons, transmissions and pattern names", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({
            structural_patterns: ["元首课"],
            lesson_method: lessonMethod(),
            timing_candidates: [candidate()],
          }),
        })}
      />,
    );

    const block = summary();
    expect(block).toHaveTextContent("四课");
    expect(block).toHaveTextContent("巳");
    expect(block).toHaveTextContent("丁");
    expect(block).toHaveTextContent("三传");
    expect(block).toHaveTextContent("酉");
    expect(block).toHaveTextContent("贵人");
    expect(block).toHaveTextContent("课体 元首课");
    expect(block).not.toHaveTextContent("贼克课");
    expect(block).not.toHaveTextContent("庚申");
    expect(block).not.toHaveTextContent(/吉凶|成败|强弱|大吉|大凶/);
    expect(block).not.toHaveTextContent(/GAP-DL/);
  });

  it("drops missing clauses and hides the summary when nothing can be restated", () => {
    const { rerender } = render(
      <DaliurenBoard
        view={chart({
          lessons: blankLessons(),
          core_facts: emptyFacts({ structural_patterns: ["元首课"] }),
        })}
      />,
    );
    expect(summary()).toHaveTextContent("三传");
    expect(summary()).toHaveTextContent("课体 元首课");
    expect(summary()).not.toHaveTextContent("四课");

    rerender(
      <DaliurenBoard
        view={chart({
          lessons: blankLessons(),
          transmissions: blankTransmissions(),
          core_facts: emptyFacts(),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "基础摘要" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
  });

  it("shows the no-offer deep-read gate with on-screen quotes and no checkout", () => {
    render(<DaliurenBoard view={chart({ core_facts: emptyFacts({ structural_patterns: ["元首课"] }) })} />);

    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
    expect(screen.getByRole("status", { name: "测试期未开放" })).toHaveAttribute("data-state", "unavailable");
    const deep = screen.getByRole("heading", { name: "深读" }).closest("section");
    expect(deep).toHaveTextContent("一课·日干");
    expect(deep).toHaveTextContent("巳");
    expect(deep).toHaveTextContent("白虎");
    expect(deep).toHaveTextContent("元首课");
    expect(deep).not.toHaveTextContent(/吉凶|大吉|大凶|旺衰/);
    expect(deep).not.toHaveTextContent(/GAP-DL/);
    expect(screen.queryByText(/¥|￥|\d+\s*元/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买|支付/ })).not.toBeInTheDocument();
    expect(screen.queryByText("reading_version_id")).not.toBeInTheDocument();
  });

  it("does not quote lesson_method or timing facts in the deep-read samples", () => {
    render(
      <DaliurenBoard
        view={chart({
          lessons: blankLessons(),
          transmissions: blankTransmissions(),
          core_facts: emptyFacts({
            lesson_method: lessonMethod(),
            timing_candidates: [candidate()],
          }),
        })}
      />,
    );

    const deep = screen.getByRole("heading", { name: "深读" }).closest("section");
    expect(deep).not.toHaveTextContent("贼克课");
    expect(deep).not.toHaveTextContent("庚申");
    expect(deep).not.toHaveTextContent("元首课");
  });

  it("renders a passed offer card without inventing checkout, and confirming only says 确认中", () => {
    const { rerender } = render(<DaliurenBoard view={chart()} offer={OFFER} />);

    expect(screen.getByText("大六壬课传深读")).toBeVisible();
    expect(screen.getByText("当前这张已排出课盘的四课三传")).toBeVisible();
    expect(screen.getByText("由服务端标价")).toBeVisible();
    expect(screen.getByText("未交付可退")).toBeVisible();
    expect(screen.getByText("绑定当前这张已排出的课盘")).toBeVisible();
    expect(screen.getByRole("link", { name: "登录后继续" })).toHaveAttribute("href", "/auth/login");
    expect(screen.queryByRole("status", { name: "测试期未开放" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买/ })).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={chart()} offer={OFFER} s4Phase="confirming" />);
    expect(screen.getByRole("status", { name: "确认中" })).toBeVisible();
    expect(screen.queryByText("由服务端标价")).not.toBeInTheDocument();
    expect(screen.queryByText(/订单号/)).not.toBeInTheDocument();
  });

  it("uses locked and fake-gateway copy without treating them as paid", () => {
    const { rerender } = render(<DaliurenBoard view={chart()} s4Phase="locked" />);
    expect(screen.getByRole("status", { name: "已锁定" })).toHaveAttribute("data-state", "locked");
    expect(screen.queryByRole("status", { name: "测试期未开放" })).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={chart()} offer={OFFER} s4Phase="gateway_unavailable" />);
    expect(screen.getByRole("status", { name: "支付暂时不可用" })).toHaveAttribute("data-state", "unavailable");
    expect(screen.queryByText("由服务端标价")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买|支付/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "登录后继续" })).not.toBeInTheDocument();
  });

  it("keeps loading and silhouette modes free of summary and deep-read copy", () => {
    const { rerender } = render(<DaliurenBoard view={chart()} mode="loading" />);
    expect(screen.queryByRole("region", { name: "基础摘要" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "深读" })).not.toBeInTheDocument();
    expect(screen.queryByText("测试期未开放")).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={chart()} mode="silhouette" />);
    expect(screen.queryByRole("heading", { name: "深读" })).not.toBeInTheDocument();
  });

  it("keeps the free-summary module off shared pages and off other arts", () => {
    const boardSource = readFileSync(resolve(process.cwd(), "src/components/readings/daliuren-board.tsx"), "utf8");
    const summarySource = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-free-summary.tsx"),
      "utf8",
    );
    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-free-summary.module.css"),
      "utf8",
    );
    const runtime = readFileSync(resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"), "utf8");
    const experience = readFileSync(resolve(process.cwd(), "src/components/task/product-task-experience.tsx"), "utf8");
    expect(boardSource).toContain("daliuren-free-summary");
    expect(summarySource).not.toMatch(/ziwei-free-summary|bazi-chart|liuyao-line-tower|runtime-chart|product-task-experience|GAP-DL/);
    expect(css).toMatch(/--color-text/);
    expect(css).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(css).not.toMatch(/color-success|color-danger|surface-success|surface-danger/);
    expect(css).not.toMatch(/linear-gradient|radial-gradient|box-shadow:\s*0 0/);
    expect(runtime).not.toContain("daliuren-free-summary");
    expect(experience).not.toContain("daliuren-free-summary");
  });
});

describe("大六壬 S3 M1 起课口径条", () => {
  function caliber() {
    return screen.getByRole("region", { name: "起课口径" });
  }

  it("shows the question as-is when core_facts is null", () => {
    render(<DaliurenBoard view={chart()} />);
    expect(caliber()).toHaveTextContent("这件事何时可能出现回应？");
    expect(within(caliber()).queryByText("课式")).not.toBeInTheDocument();
    expect(screen.queryByText("昼贵人")).not.toBeInTheDocument();
    expect(screen.queryByText("夜贵人")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-DL/)).not.toBeInTheDocument();
  });

  it("folds a long question behind 展开 and leaves short questions unfolded", async () => {
    const user = userEvent.setup();
    const long = "这件事后续会不会出现明确回应，以及大约会在什么时候出现？";
    const { rerender } = render(<DaliurenBoard view={chart({ question: long })} />);

    const block = caliber();
    expect(within(block).getByText("展开")).toBeVisible();
    expect(within(block).queryByText(long)).not.toBeVisible();
    await user.click(within(block).getByText("展开"));
    expect(within(block).getByText(long)).toBeVisible();

    rerender(<DaliurenBoard view={chart()} />);
    expect(within(caliber()).queryByText("展开")).not.toBeInTheDocument();
    expect(within(caliber()).getByText("这件事何时可能出现回应？")).toBeVisible();
  });

  it("keeps the long-question disclosure target at least 44 by 44 pixels", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-caliber-bar.module.css"),
      "utf8",
    );

    expect(css).toMatch(
      /\.summary\s*\{[^}]*min-height:\s*var\(--target-min\);[^}]*min-width:\s*var\(--target-min\);/s,
    );
  });

  it("renders typed caliber fields and hides internal field names", () => {
    render(
      <DaliurenBoard
        view={chart({
          question: "",
          core_facts: emptyFacts({
            day_hour: { day: "丙午", hour: "卯" },
            month_general: { branch: "亥", name: "登明" },
            noble_person: noblePerson({ branch: "巳" }),
            xunkong: { xun: "甲子", branches: ["辰", "巳"] },
          }),
        })}
      />,
    );

    const block = caliber();
    expect(within(block).getByText("丙午日 卯时")).toBeVisible();
    expect(within(block).getByText("月将：亥（登明）")).toBeVisible();
    expect(within(block).getByText("贵人：巳")).toBeVisible();
    expect(within(block).getByText("旬空：甲子旬 · 辰巳")).toBeVisible();
    expect(screen.queryByText("day_hour")).not.toBeInTheDocument();
    expect(screen.queryByText("month_general")).not.toBeInTheDocument();
    expect(screen.queryByText("昼贵人")).not.toBeInTheDocument();
    expect(caliber().querySelector("[data-void]")).toBeNull();
  });

  it("fail-closes malformed caliber objects instead of reading loose adapter aliases", () => {
    const { rerender } = render(
      <DaliurenBoard
        view={chart({
          question: "",
          core_facts: emptyFacts({
            day_hour: { note: "丙午日 卯时起课", display_text: "旧时辰" } as unknown as CoreFacts["day_hour"],
            month_general: { text: "月将：亥（登明）" } as unknown as CoreFacts["month_general"],
            noble_person: { label: "贵人在巳" } as unknown as CoreFacts["noble_person"],
            xunkong: { name: "旬空：辰巳" } as unknown as CoreFacts["xunkong"],
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "起课口径" })).not.toBeInTheDocument();
    expect(screen.queryByText("旧时辰")).not.toBeInTheDocument();
    expect(screen.queryByText("月将：亥（登明）")).not.toBeInTheDocument();
    expect(screen.queryByText("贵人在巳")).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={chart({ question: "   ", core_facts: emptyFacts() })} />);
    expect(screen.queryByRole("region", { name: "起课口径" })).not.toBeInTheDocument();
  });

  it("does not render partial typed caliber records", () => {
    render(
      <DaliurenBoard
        view={chart({
          question: "",
          core_facts: emptyFacts({
            day_hour: { hour: "卯" } as unknown as CoreFacts["day_hour"],
            month_general: { branch: "亥" } as unknown as CoreFacts["month_general"],
            noble_person: { earth_position: "巳" } as unknown as CoreFacts["noble_person"],
            xunkong: { xun: "甲子" } as unknown as CoreFacts["xunkong"],
          }),
        })}
      />,
    );

    expect(screen.queryByRole("region", { name: "起课口径" })).not.toBeInTheDocument();
    expect(screen.queryByText("月将：亥")).not.toBeInTheDocument();
    expect(screen.queryByText("贵人：巳")).not.toBeInTheDocument();
    expect(screen.queryByText("旬空：甲子")).not.toBeInTheDocument();
  });

  it("keeps loading and silhouette modes free of the caliber bar", () => {
    const view = chart({
      core_facts: emptyFacts({
        day_hour: { day: "丙午", hour: "卯" },
      }),
    });
    const { rerender } = render(<DaliurenBoard view={view} mode="loading" />);
    expect(screen.queryByRole("region", { name: "起课口径" })).not.toBeInTheDocument();
    expect(screen.queryByText("这件事何时可能出现回应？")).not.toBeInTheDocument();
    expect(screen.queryByText("丙午日 卯时起课")).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={view} mode="silhouette" />);
    expect(screen.queryByRole("region", { name: "起课口径" })).not.toBeInTheDocument();
    expect(screen.queryByText("丙午日 卯时起课")).not.toBeInTheDocument();
  });

  it("keeps the caliber module off shared pages", () => {
    const boardSource = readFileSync(resolve(process.cwd(), "src/components/readings/daliuren-board.tsx"), "utf8");
    const caliberSource = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-caliber-bar.tsx"),
      "utf8",
    );
    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-caliber-bar.module.css"),
      "utf8",
    );
    const runtime = readFileSync(resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"), "utf8");
    const experience = readFileSync(resolve(process.cwd(), "src/components/task/product-task-experience.tsx"), "utf8");
    expect(boardSource).toContain("daliuren-caliber-bar");
    expect(caliberSource).not.toMatch(/ziwei-caliber-bar|bazi-chart|runtime-chart|product-task-experience|GAP-DL|昼贵人|夜贵人/);
    expect(css).toMatch(/--color-text/);
    expect(css).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(css).not.toMatch(/color-success|color-danger|surface-success|surface-danger/);
    expect(css).not.toMatch(/linear-gradient|radial-gradient|box-shadow:\s*0 0/);
    expect(runtime).not.toContain("daliuren-caliber-bar");
    expect(experience).not.toContain("daliuren-caliber-bar");
  });
});

describe("大六壬 S3 旬空角标", () => {
  function voided() {
    return chart({
      core_facts: emptyFacts({
        xunkong: { xun: "甲子", branches: ["辰", "巳", "  "] } as unknown as CoreFacts["xunkong"],
      }),
    });
  }

  it("marks matching lesson and transmission branches from xunkong.branches only", () => {
    render(<DaliurenBoard view={voided()} />);

    const firstUpper = screen.getByRole("button", { name: "一课·日干 上神 巳" });
    const secondLower = screen.getByRole("button", { name: "二课·日支 下神 巳" });
    const finalTx = screen.getByRole("button", { name: "末传 巳 白虎" });
    expect(firstUpper).toHaveAttribute("data-void", "true");
    expect(secondLower).toHaveAttribute("data-void", "true");
    expect(finalTx).toHaveAttribute("data-void", "true");
    expect(within(firstUpper).getByText("空")).toBeVisible();
    expect(within(finalTx).getByText("空")).toBeVisible();

    expect(screen.getByRole("button", { name: "一课·日干 下神 丁" })).not.toHaveAttribute("data-void");
    expect(screen.getByRole("button", { name: "三课·辰干 上神 酉" })).not.toHaveAttribute("data-void");
    expect(screen.getByRole("button", { name: "初传 酉 贵人" })).not.toHaveAttribute("data-void");
    expect(within(firstUpper).queryByText("甲子")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-DL/)).not.toBeInTheDocument();
  });

  it("does not invent void marks from xun, empty arrays, silhouette or missing core_facts", () => {
    const { rerender } = render(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({
            xunkong: { xun: "甲子", branches: [] } as unknown as CoreFacts["xunkong"],
          }),
        })}
      />,
    );
    expect(board().querySelector("[data-void]")).toBeNull();
    expect(screen.queryByText("空")).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={chart()} />);
    expect(board().querySelector("[data-void]")).toBeNull();

    rerender(<DaliurenBoard mode="silhouette" view={voided()} />);
    expect(board().querySelector("[data-void]")).toBeNull();
    expect(screen.queryByText("空")).not.toBeInTheDocument();

    rerender(<DaliurenBoard mode="loading" view={voided()} />);
    expect(board().querySelector("[data-void]")).toBeNull();
  });

  it("keeps void badges in paper-ink tokens and off shared pages", () => {
    const css = boardCss();
    const boardSource = readFileSync(resolve(process.cwd(), "src/components/readings/daliuren-board.tsx"), "utf8");
    const runtime = readFileSync(resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"), "utf8");
    const experience = readFileSync(resolve(process.cwd(), "src/components/task/product-task-experience.tsx"), "utf8");
    expect(css).toMatch(/\[data-void="true"\][^{]*\{[\s\S]*--color-text/);
    expect(css).not.toMatch(/color-success|color-danger|surface-success|surface-danger/);
    expect(boardSource).not.toMatch(/liuyao|GAP-DL|runtime-chart|product-task-experience/);
    expect(runtime).not.toMatch(/data-void/);
    expect(experience).not.toMatch(/data-void/);
  });
});

describe("大六壬 S3 天地盘旬空角标", () => {
  const EARTH = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"] as const;

  function plate(overrides: Partial<CoreFacts> = {}) {
    return chart({
      core_facts: emptyFacts({
        earth_plate: [...EARTH],
        heaven_plate: [
          { earth: "辰", heaven: "戌" },
          { earth: "巳", heaven: "亥" },
        ],
        heavenly_generals: [
          { earth: "辰", heaven: "戌", general: "天后" },
          { earth: "巳", heaven: "亥", general: "贵人" },
        ],
        noble_person: {
          branch: "巳",
          day_night_profile: "甲戊庚牛羊",
          direction: "forward",
          earth_position: "巳",
          period: "day",
          profile: "昼贵人",
          source: "runtime_core_facts",
        },
        ...overrides,
      }),
    });
  }

  async function openPlate() {
    const user = userEvent.setup();
    await user.click(screen.getByText("天地盘"));
    return screen.getByRole("table", { name: "天地盘" }).closest("[data-slot='heaven-earth']") as HTMLElement;
  }

  it("propagates focus, hover and click-lock facts into the ring and semantic table", async () => {
    const user = userEvent.setup();
    render(
      <DaliurenBoard
        view={plate({
          heaven_plate: [
            { earth: "辰", heaven: "巳" },
            { earth: "巳", heaven: "亥" },
          ],
        })}
      />,
    );

    const panel = await openPlate();
    const boardFact = screen.getByRole("button", { name: "一课·日干 上神 巳" });
    const earthRing = panel.querySelector('ol [data-branch="巳"]') as HTMLElement;
    const heavenRing = panel.querySelector('ol [data-branch="辰"]') as HTMLElement;
    const earthRow = panel.querySelector('table [data-branch="巳"]') as HTMLElement;
    const heavenRow = panel.querySelector('table [data-branch="辰"]') as HTMLElement;
    const linkedPlatePositions = [earthRing, heavenRing, earthRow, heavenRow];

    for (const position of linkedPlatePositions) expect(position).toHaveAttribute("data-active", "false");

    act(() => boardFact.focus());
    for (const position of linkedPlatePositions) expect(position).toHaveAttribute("data-active", "true");
    expect(boardFact).toHaveAttribute("aria-pressed", "false");

    act(() => boardFact.blur());
    for (const position of linkedPlatePositions) expect(position).toHaveAttribute("data-active", "false");

    await user.hover(boardFact);
    for (const position of linkedPlatePositions) expect(position).toHaveAttribute("data-active", "true");
    await user.unhover(boardFact);
    for (const position of linkedPlatePositions) expect(position).toHaveAttribute("data-active", "false");

    await user.click(boardFact);
    for (const position of linkedPlatePositions) expect(position).toHaveAttribute("data-active", "true");
    expect(boardFact).toHaveAttribute("aria-pressed", "true");

    await user.click(boardFact);
    expect(boardFact).toHaveAttribute("aria-pressed", "false");
    for (const position of linkedPlatePositions) expect(position).toHaveAttribute("data-active", "true");
    act(() => boardFact.blur());
    await user.unhover(boardFact);
    for (const position of linkedPlatePositions) expect(position).toHaveAttribute("data-active", "false");
  });

  it("links transmission generals onto repeated plate positions without activating them from a shared branch", async () => {
    const user = userEvent.setup();
    const GOLDEN_GENERALS = [
      ["子", "太常"],
      ["丑", "白虎"],
      ["寅", "天空"],
      ["卯", "青龙"],
      ["辰", "勾陈"],
      ["巳", "六合"],
      ["午", "朱雀"],
      ["未", "腾蛇"],
      ["申", "贵人"],
      ["酉", "天后"],
      ["戌", "太阴"],
      ["亥", "玄武"],
    ] as const;
    render(
      <DaliurenBoard
        view={chart({
          lessons: [
            { lesson_id: "一课·日干", upper: "辰", lower: "乙" },
            { lesson_id: "二课·日支", upper: "辰", lower: "辰" },
            { lesson_id: "三课·辰干", upper: "酉", lower: "酉" },
            { lesson_id: "四课·辰支", upper: "酉", lower: "酉" },
          ],
          transmissions: [
            { stage: "initial", branch: "辰", general: "勾陈" },
            { stage: "middle", branch: "酉", general: "天后" },
            { stage: "final", branch: "卯", general: "青龙" },
          ],
          core_facts: emptyFacts({
            earth_plate: [...EARTH],
            heaven_plate: EARTH.map((branch) => ({ earth: branch, heaven: branch })),
            heavenly_generals: GOLDEN_GENERALS.map(([earth, general]) => ({
              earth,
              heaven: earth,
              general,
            })),
          }),
        })}
      />,
    );

    const panel = await openPlate();
    const lessonChen = screen.getByRole("button", { name: "一课·日干 上神 辰" });
    const initial = screen.getByRole("button", { name: "初传 辰 勾陈" });
    const middle = screen.getByRole("button", { name: "中传 酉 天后" });
    const initialGeneral = initial.querySelector("[data-chip='general']") as HTMLElement;
    const middleGeneral = middle.querySelector("[data-chip='general']") as HTMLElement;
    const chenGeneral = panel.querySelector('table [data-branch="辰"] td:last-child') as HTMLElement;
    const youGeneral = panel.querySelector('table [data-branch="酉"] td:last-child') as HTMLElement;
    const maoGeneral = panel.querySelector('table [data-branch="卯"] td:last-child') as HTMLElement;
    const chenRow = panel.querySelector('table [data-branch="辰"]') as HTMLElement;
    const youRow = panel.querySelector('table [data-branch="酉"]') as HTMLElement;

    act(() => lessonChen.focus());
    expect(lessonChen).toHaveAttribute("data-active", "true");
    expect(initial).toHaveAttribute("data-active", "true");
    expect(initialGeneral).toHaveAttribute("data-active", "false");
    expect(chenRow).toHaveAttribute("data-active", "true");
    expect(youRow).toHaveAttribute("data-active", "false");
    expect(youGeneral).toHaveAttribute("data-active", "false");
    expect(maoGeneral).toHaveAttribute("data-active", "false");
    act(() => lessonChen.blur());

    act(() => initial.focus());
    expect(initial).toHaveAttribute("data-active", "true");
    expect(initialGeneral).toHaveAttribute("data-active", "true");
    expect(middleGeneral).toHaveAttribute("data-active", "false");
    expect(chenRow).toHaveAttribute("data-active", "true");
    expect(youRow).toHaveAttribute("data-active", "false");
    expect(youGeneral).toHaveAttribute("data-active", "false");
    expect(maoGeneral).toHaveAttribute("data-active", "false");
    expect(panel.querySelector('table [data-branch="辰"] td:last-child')).toHaveAttribute("data-active", "true");
    act(() => initial.blur());

    await user.click(middle);
    expect(middle).toHaveAttribute("aria-pressed", "true");
    expect(middleGeneral).toHaveAttribute("data-active", "true");
    expect(initialGeneral).toHaveAttribute("data-active", "false");
    expect(youRow).toHaveAttribute("data-active", "true");
    expect(youGeneral).toHaveAttribute("data-active", "true");
    expect(chenRow).toHaveAttribute("data-active", "false");
    expect(chenGeneral).toHaveAttribute("data-active", "false");
    expect(maoGeneral).toHaveAttribute("data-active", "false");
  });

  it("lets plate earth, heaven and general facts initiate highlight and lock", async () => {
    const user = userEvent.setup();
    const GOLDEN_GENERALS = [
      ["子", "太常"],
      ["丑", "白虎"],
      ["寅", "天空"],
      ["卯", "青龙"],
      ["辰", "勾陈"],
      ["巳", "六合"],
      ["午", "朱雀"],
      ["未", "腾蛇"],
      ["申", "贵人"],
      ["酉", "天后"],
      ["戌", "太阴"],
      ["亥", "玄武"],
    ] as const;
    render(
      <DaliurenBoard
        view={chart({
          lessons: [
            { lesson_id: "一课·日干", upper: "辰", lower: "乙" },
            { lesson_id: "二课·日支", upper: "辰", lower: "辰" },
            { lesson_id: "三课·辰干", upper: "酉", lower: "酉" },
            { lesson_id: "四课·辰支", upper: "酉", lower: "酉" },
          ],
          transmissions: [
            { stage: "initial", branch: "辰", general: "勾陈" },
            { stage: "middle", branch: "酉", general: "天后" },
            { stage: "final", branch: "卯", general: "青龙" },
          ],
          core_facts: emptyFacts({
            earth_plate: [...EARTH],
            heaven_plate: EARTH.map((branch) => ({ earth: branch, heaven: branch })),
            heavenly_generals: GOLDEN_GENERALS.map(([earth, general]) => ({
              earth,
              heaven: earth,
              general,
            })),
          }),
        })}
      />,
    );

    const panel = await openPlate();
    const table = screen.getByRole("table", { name: "天地盘" });
    const initial = screen.getByRole("button", { name: "初传 辰 勾陈" });
    const lessonChen = screen.getByRole("button", { name: "一课·日干 上神 辰" });
    const plateGouchen = within(table).getByRole("button", { name: "天将 勾陈" });
    const plateChenEarth = within(table).getByRole("button", { name: "地盘 辰" });
    const plateTaichang = within(table).getByRole("button", { name: "天将 太常" });
    const chenRow = panel.querySelector('table [data-branch="辰"]') as HTMLElement;
    const youRow = panel.querySelector('table [data-branch="酉"]') as HTMLElement;
    const ziRow = panel.querySelector('table [data-branch="子"]') as HTMLElement;
    const chenGeneral = panel.querySelector('table [data-branch="辰"] td:last-child') as HTMLElement;
    const youGeneral = panel.querySelector('table [data-branch="酉"] td:last-child') as HTMLElement;
    const initialGeneral = initial.querySelector("[data-chip='general']") as HTMLElement;

    act(() => plateGouchen.focus());
    expect(plateGouchen).toHaveAttribute("aria-pressed", "false");
    expect(chenRow).toHaveAttribute("data-active", "true");
    expect(chenGeneral).toHaveAttribute("data-active", "true");
    expect(initial).toHaveAttribute("data-active", "true");
    expect(initialGeneral).toHaveAttribute("data-active", "true");
    expect(lessonChen).toHaveAttribute("data-active", "false");
    expect(youRow).toHaveAttribute("data-active", "false");
    expect(youGeneral).toHaveAttribute("data-active", "false");
    act(() => plateGouchen.blur());
    expect(chenRow).toHaveAttribute("data-active", "false");
    expect(initial).toHaveAttribute("data-active", "false");

    await user.hover(plateGouchen);
    expect(chenGeneral).toHaveAttribute("data-active", "true");
    expect(initialGeneral).toHaveAttribute("data-active", "true");
    await user.unhover(plateGouchen);
    expect(chenGeneral).toHaveAttribute("data-active", "false");

    await user.click(plateGouchen);
    expect(plateGouchen).toHaveAttribute("aria-pressed", "true");
    expect(chenGeneral).toHaveAttribute("data-active", "true");
    expect(initialGeneral).toHaveAttribute("data-active", "true");
    expect(lessonChen).toHaveAttribute("aria-pressed", "false");
    expect(youGeneral).toHaveAttribute("data-active", "false");

    await user.click(plateChenEarth);
    expect(plateChenEarth).toHaveAttribute("aria-pressed", "true");
    expect(plateGouchen).toHaveAttribute("aria-pressed", "false");
    expect(lessonChen).toHaveAttribute("data-active", "true");
    expect(initial).toHaveAttribute("data-active", "true");
    expect(initialGeneral).toHaveAttribute("data-active", "false");
    expect(chenGeneral).toHaveAttribute("data-active", "false");
    expect(youGeneral).toHaveAttribute("data-active", "false");

    await user.click(plateTaichang);
    expect(plateTaichang).toHaveAttribute("aria-pressed", "true");
    expect(ziRow).toHaveAttribute("data-active", "true");
    expect(initial).toHaveAttribute("data-active", "false");
    expect(lessonChen).toHaveAttribute("data-active", "false");
    expect(chenRow).toHaveAttribute("data-active", "false");

    act(() => plateTaichang.focus());
    await user.keyboard("{Escape}");
    expect(plateTaichang).toHaveAttribute("aria-pressed", "false");
    expect(plateTaichang).toHaveFocus();
    expect(ziRow).toHaveAttribute("data-active", "true");
    act(() => plateTaichang.blur());
    await user.unhover(plateTaichang);
    expect(ziRow).toHaveAttribute("data-active", "false");

    expect(plateCss()).toMatch(/\.fact\s*\{[^}]*min-width:\s*var\(--target-min\)/s);
    expect(plateCss()).toMatch(/\.fact\s*\{[^}]*min-height:\s*var\(--target-min\)/s);
  });

  it("gives ≥64rem ring .earth/.heaven/.general their own 44px hit area, not the spoke", async () => {
    const user = userEvent.setup();
    const GOLDEN_GENERALS = [
      ["子", "太常"],
      ["丑", "白虎"],
      ["寅", "天空"],
      ["卯", "青龙"],
      ["辰", "勾陈"],
      ["巳", "六合"],
      ["午", "朱雀"],
      ["未", "腾蛇"],
      ["申", "贵人"],
      ["酉", "天后"],
      ["戌", "太阴"],
      ["亥", "玄武"],
    ] as const;
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    render(
      <DaliurenBoard
        view={chart({
          lessons: [
            { lesson_id: "一课·日干", upper: "辰", lower: "乙" },
            { lesson_id: "二课·日支", upper: "辰", lower: "辰" },
            { lesson_id: "三课·辰干", upper: "酉", lower: "酉" },
            { lesson_id: "四课·辰支", upper: "酉", lower: "酉" },
          ],
          transmissions: [
            { stage: "initial", branch: "辰", general: "勾陈" },
            { stage: "middle", branch: "酉", general: "天后" },
            { stage: "final", branch: "卯", general: "青龙" },
          ],
          core_facts: emptyFacts({
            earth_plate: [...EARTH],
            heaven_plate: EARTH.map((branch) => ({ earth: branch, heaven: branch })),
            heavenly_generals: GOLDEN_GENERALS.map(([earth, general]) => ({
              earth,
              heaven: earth,
              general,
            })),
          }),
        })}
      />,
    );

    const panel = await openPlate();
    const ring = panel.querySelector("[data-ring='earth']") as HTMLElement;
    const table = screen.getByRole("table", { name: "天地盘" });
    const initial = screen.getByRole("button", { name: "初传 辰 勾陈" });
    const lessonChen = screen.getByRole("button", { name: "一课·日干 上神 辰" });
    const plateGouchen = within(table).getByRole("button", { name: "天将 勾陈" });
    const chenSpoke = ring.querySelector('[data-branch="辰"]') as HTMLElement;
    const [ringEarth, ringHeaven, ringGeneral] = [
      ...chenSpoke.querySelectorAll(":scope > [role='presentation']"),
    ] as HTMLElement[];
    const youSpoke = ring.querySelector('[data-branch="酉"]') as HTMLElement;
    const ringYouHeaven = [...youSpoke.querySelectorAll(":scope > [role='presentation']")][1] as HTMLElement;

    expect(ring).toHaveAttribute("aria-hidden", "true");
    expect(ringEarth).toBeTruthy();
    expect(ringGeneral).toBeTruthy();
    expect(ringEarth).toHaveAttribute("data-fact", "earth");
    expect(ringHeaven).toHaveAttribute("data-fact", "heaven");
    expect(ringGeneral).toHaveAttribute("data-fact", "general");
    expect(ring.querySelectorAll("[data-fact]")).toHaveLength(36);
    expect(ringEarth).not.toHaveAttribute("aria-label");
    expect(ringEarth).not.toHaveAttribute("aria-pressed");
    expect(ringEarth).not.toHaveAttribute("tabindex");
    expect(ringGeneral).not.toHaveAttribute("aria-label");
    expect(ringGeneral).not.toHaveAttribute("aria-pressed");
    expect(ring.querySelectorAll("[aria-label]")).toHaveLength(0);

    const css = plateCss();
    const pointerRule =
      /\.earth\[role="presentation"\],\s*\.heaven\[role="presentation"\],\s*\.general\[role="presentation"\]\s*\{[^}]*min-width:\s*var\(--target-min\);[^}]*min-height:\s*var\(--target-min\);/s;
    expect(css).toMatch(pointerRule);
    expect(css).toMatch(/\.spoke\s*\{[^}]*pointer-events:\s*none/s);
    expect(css).toMatch(/\.ring\s*\{[^}]*width:\s*37rem/s);
    expect(css).toMatch(/\.ring\s*\{[^}]*height:\s*37rem/s);
    expect(css).toMatch(/--earth-radius:\s*8rem/);
    expect(css).toMatch(/--heaven-radius:\s*12rem/);
    expect(css).toMatch(/--general-radius:\s*16rem/);
    expect(css).toMatch(/--angle:\s*calc\(var\(--spoke\) \* 30deg\)/);
    expect(css).toMatch(/translateY\(calc\(-1 \* var\(--earth-radius\)\)\)/);
    expect(css).toMatch(/translateY\(calc\(-1 \* var\(--heaven-radius\)\)\)/);
    expect(css).toMatch(/translateY\(calc\(-1 \* var\(--general-radius\)\)\)/);
    expect(css).toMatch(/\.spoke\s*\{[^}]*width:\s*0;[^}]*height:\s*0/s);
    expect(css).toMatch(/@media \(min-width: 64rem\)[\s\S]*\.body\s*\{[^}]*gap:\s*var\(--space-lg\)/);
    expect(css).toMatch(/\.earth\s*>\s*\.voidBadge/);
    expect(css).not.toMatch(/overflow:\s*hidden/);
    expect(css).not.toMatch(/min\(100%/);
    expect(css).not.toMatch(/translateY\(-7\.2rem\)/);
    expect(css).not.toMatch(/\.spoke\s*\{[^}]*min-height:\s*var\(--target-min\)/s);
    expect(css).not.toMatch(/\.earth[^{]*\{[^}]*z-index/s);
    expect(css).not.toMatch(/\.heaven[^{]*\{[^}]*z-index/s);
    expect(css).not.toMatch(/\.general[^{]*\{[^}]*z-index/s);

    document.documentElement.style.setProperty("--target-min", "44px");
    for (const fact of [ringEarth, ringHeaven, ringGeneral]) {
      expect(fact).toHaveStyle({ minWidth: "var(--target-min)", minHeight: "var(--target-min)" });
      const style = window.getComputedStyle(fact);
      const width = style.minWidth === "var(--target-min)" ? 44 : Number.parseFloat(style.minWidth);
      const height = style.minHeight === "var(--target-min)" ? 44 : Number.parseFloat(style.minHeight);
      expect(width).toBeGreaterThanOrEqual(44);
      expect(height).toBeGreaterThanOrEqual(44);
      expect(fact).not.toBe(chenSpoke);
    }

    await user.hover(ringGeneral);
    expect(initial).toHaveAttribute("data-active", "true");
    expect(plateGouchen).toHaveAttribute("aria-pressed", "false");
    expect(lessonChen).toHaveAttribute("data-active", "false");
    await user.unhover(ringGeneral);
    expect(initial).toHaveAttribute("data-active", "false");

    await user.click(ringGeneral);
    expect(plateGouchen).toHaveAttribute("aria-pressed", "true");
    expect(initial).toHaveAttribute("data-active", "true");
    expect(lessonChen).toHaveAttribute("aria-pressed", "false");
    expect(ringGeneral).not.toHaveAttribute("aria-pressed");

    await user.click(ringEarth);
    expect(within(table).getByRole("button", { name: "地盘 辰" })).toHaveAttribute("aria-pressed", "true");
    expect(plateGouchen).toHaveAttribute("aria-pressed", "false");
    expect(lessonChen).toHaveAttribute("data-active", "true");

    await user.click(ringYouHeaven);
    expect(within(table).getByRole("button", { name: "天盘 酉" })).toHaveAttribute("aria-pressed", "true");
    expect(within(table).getByRole("button", { name: "地盘 辰" })).toHaveAttribute("aria-pressed", "false");

    act(() => plateGouchen.focus());
    expect(plateGouchen).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(within(table).getByRole("button", { name: "天盘 酉" })).toHaveAttribute("aria-pressed", "false");
  });

  it("unlocks a composite transmission lock from any pressed linked plate fact", async () => {
    const user = userEvent.setup();
    const GOLDEN_GENERALS = [
      ["子", "太常"],
      ["丑", "白虎"],
      ["寅", "天空"],
      ["卯", "青龙"],
      ["辰", "勾陈"],
      ["巳", "六合"],
      ["午", "朱雀"],
      ["未", "腾蛇"],
      ["申", "贵人"],
      ["酉", "天后"],
      ["戌", "太阴"],
      ["亥", "玄武"],
    ] as const;
    render(
      <DaliurenBoard
        view={chart({
          lessons: [
            { lesson_id: "一课·日干", upper: "辰", lower: "乙" },
            { lesson_id: "二课·日支", upper: "辰", lower: "辰" },
            { lesson_id: "三课·辰干", upper: "酉", lower: "酉" },
            { lesson_id: "四课·辰支", upper: "酉", lower: "酉" },
          ],
          transmissions: [
            { stage: "initial", branch: "辰", general: "勾陈" },
            { stage: "middle", branch: "酉", general: "天后" },
            { stage: "final", branch: "卯", general: "青龙" },
          ],
          core_facts: emptyFacts({
            earth_plate: [...EARTH],
            heaven_plate: EARTH.map((branch) => ({ earth: branch, heaven: branch })),
            heavenly_generals: GOLDEN_GENERALS.map(([earth, general]) => ({
              earth,
              heaven: earth,
              general,
            })),
          }),
        })}
      />,
    );

    await openPlate();
    const table = screen.getByRole("table", { name: "天地盘" });
    const initial = screen.getByRole("button", { name: "初传 辰 勾陈" });
    const plateGouchen = within(table).getByRole("button", { name: "天将 勾陈" });

    await user.click(initial);
    expect(initial).toHaveAttribute("aria-pressed", "true");
    expect(plateGouchen).toHaveAttribute("aria-pressed", "true");

    await user.click(plateGouchen);
    expect(plateGouchen).toHaveAttribute("aria-pressed", "false");
    expect(initial).toHaveAttribute("aria-pressed", "false");
  });

  it("moves through the semantic heaven-earth table with arrow keys", async () => {
    const user = userEvent.setup();
    const GOLDEN_GENERALS = [
      ["子", "太常"],
      ["丑", "白虎"],
      ["寅", "天空"],
      ["卯", "青龙"],
      ["辰", "勾陈"],
      ["巳", "六合"],
      ["午", "朱雀"],
      ["未", "腾蛇"],
      ["申", "贵人"],
      ["酉", "天后"],
      ["戌", "太阴"],
      ["亥", "玄武"],
    ] as const;
    render(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({
            earth_plate: [...EARTH],
            heaven_plate: EARTH.map((branch) => ({ earth: branch, heaven: branch })),
            heavenly_generals: GOLDEN_GENERALS.map(([earth, general]) => ({
              earth,
              heaven: earth,
              general,
            })),
          }),
        })}
      />,
    );

    const panel = await openPlate();
    const table = within(panel).getByRole("table", { name: "天地盘" });
    const ziEarth = within(table).getByRole("button", { name: "地盘 子" });
    const ziHeaven = within(table).getByRole("button", { name: "天盘 子" });
    const ziGeneral = within(table).getByRole("button", { name: "天将 太常" });
    const chouEarth = within(table).getByRole("button", { name: "地盘 丑" });
    const chouHeaven = within(table).getByRole("button", { name: "天盘 丑" });
    const chouGeneral = within(table).getByRole("button", { name: "天将 白虎" });
    const haiGeneral = within(table).getByRole("button", { name: "天将 玄武" });

    expect(ziEarth).toHaveAttribute("tabindex", "0");
    expect(ziHeaven).toHaveAttribute("tabindex", "-1");
    expect(ziGeneral).toHaveAttribute("tabindex", "-1");
    expect(chouEarth).toHaveAttribute("tabindex", "-1");

    await user.click(ziEarth);
    await user.keyboard("{ArrowRight}");
    expect(ziHeaven).toHaveFocus();
    expect(ziHeaven).toHaveAttribute("tabindex", "0");
    expect(ziEarth).toHaveAttribute("tabindex", "-1");

    await user.keyboard("{ArrowRight}");
    expect(ziGeneral).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(ziGeneral).toHaveFocus();

    await user.keyboard("{ArrowDown}");
    expect(chouGeneral).toHaveFocus();
    await user.keyboard("{ArrowLeft}");
    expect(chouHeaven).toHaveFocus();
    await user.keyboard("{ArrowLeft}");
    expect(chouEarth).toHaveFocus();
    await user.keyboard("{ArrowUp}");
    expect(ziEarth).toHaveFocus();

    await user.keyboard("{End}");
    expect(haiGeneral).toHaveFocus();
    expect(haiGeneral).toHaveAttribute("tabindex", "0");
    await user.keyboard("{Home}");
    expect(ziEarth).toHaveFocus();
    expect(ziEarth).toHaveAttribute("tabindex", "0");
  });

  it("marks matching earth-plate branches from xunkong.branches only", async () => {
    render(
      <DaliurenBoard
        view={plate({
          xunkong: { xun: "甲子", branches: ["辰", "巳", "  "] } as unknown as CoreFacts["xunkong"],
        })}
      />,
    );

    const panel = await openPlate();
    const chen = panel.querySelector('table [data-branch="辰"]') as HTMLElement;
    const si = panel.querySelector('table [data-branch="巳"]') as HTMLElement;
    const you = panel.querySelector('table [data-branch="酉"]') as HTMLElement;
    expect(chen).toHaveAttribute("data-void", "true");
    expect(si).toHaveAttribute("data-void", "true");
    expect(you).not.toHaveAttribute("data-void");
    expect(within(chen).getByText("空")).toBeVisible();
    expect(within(si).getByText("空")).toBeVisible();
    expect(within(chen).queryByText("戌")).not.toHaveAttribute("data-void");
    expect(panel.querySelector('[data-slot="heaven"] [data-void]')).toBeNull();
    expect(screen.getByRole("button", { name: "一课·日干 上神 巳" })).toHaveAttribute("data-void", "true");
    expect(screen.queryByText(/GAP-DL/)).not.toBeInTheDocument();
  });

  it("does not invent plate voids from xun, empty arrays or a missing plate", () => {
    const { rerender } = render(
      <DaliurenBoard
        view={plate({
          xunkong: { xun: "甲子", branches: [] } as unknown as CoreFacts["xunkong"],
        })}
      />,
    );
    expect(screen.getByText("天地盘").closest("[data-slot='heaven-earth']")?.querySelector("[data-void]")).toBeNull();

    rerender(<DaliurenBoard view={chart({ core_facts: emptyFacts({ xunkong: { xun: "甲子", branches: ["辰"] } as unknown as CoreFacts["xunkong"] }) })} />);
    expect(screen.queryByText("天地盘")).not.toBeInTheDocument();
  });

  it("keeps plate void badges in paper-ink tokens", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-heaven-earth-plate.module.css"),
      "utf8",
    );
    const source = readFileSync(
      resolve(process.cwd(), "src/components/readings/daliuren-heaven-earth-plate.tsx"),
      "utf8",
    );
    expect(css).toMatch(/\[data-void="true"\][^{]*\{[\s\S]*--color-text/);
    expect(css).not.toMatch(/color-success|color-danger|surface-success|surface-danger/);
    expect(source).not.toMatch(/GAP-DL|runtime-chart|product-task-experience/);
  });
});
