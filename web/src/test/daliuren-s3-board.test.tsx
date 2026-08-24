import { cleanup, render, screen, within } from "@testing-library/react";
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

afterEach(cleanup);

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
    calculation_source: "runtime_core_facts",
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

  it("highlights a lesson cell or transmission row on click and focus", async () => {
    const user = userEvent.setup();
    render(<DaliurenBoard view={chart()} />);

    const upper = screen.getByRole("button", { name: "一课·日干 上神 巳" });
    await user.click(upper);
    expect(upper).toHaveAttribute("data-active", "true");
    expect(upper).toHaveFocus();

    const tx = screen.getByRole("button", { name: "末传 巳 白虎" });
    await user.click(tx);
    expect(tx).toHaveAttribute("data-active", "true");
    expect(screen.getByRole("button", { name: "一课·日干 上神 巳" })).toHaveAttribute("data-active", "false");
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

    await user.click(screen.getByRole("button", { name: "候选支 酉" }));
    expect(screen.getByRole("button", { name: "初传 酉 贵人" })).toHaveAttribute("data-active", "true");
    expect(screen.getByRole("button", { name: "末传 巳 白虎" })).toHaveAttribute("data-active", "false");
  });

  it("renders an unmatched candidate branch as text and marks its earth-plate anchor", async () => {
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
    expect(within(timingTable).getByText("未")).toBeVisible();
    expect(within(timingTable).queryByRole("button", { name: "候选支 未" })).not.toBeInTheDocument();
    expect(board().querySelector("[data-stage] [data-badge='timing']")).toBeNull();

    await user.click(screen.getByText("天地盘"));
    const earthTable = screen.getByRole("table", { name: "天地盘" });
    const anchor = earthTable.querySelector('[data-branch="未"]') as HTMLElement;
    expect(anchor).toHaveAttribute("data-timing", "true");
    expect(within(anchor).getByText("应期")).toBeVisible();
    expect(earthTable.querySelector('[data-branch="辰"]')).not.toHaveAttribute("data-timing");
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
    expect(within(table).getByRole("row", { name: /^子$/ })).toBeTruthy();
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
    expect(plateCss()).toMatch(
      /transform:\s*rotate\(calc\(var\(--spoke\) \* 30deg\)\) translateY\(-7\.2rem\)\s*rotate\(calc\(var\(--spoke\) \* -30deg\)\)/s,
    );
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
    expect(within(panel).getByText("三传")).toBeVisible();
    expect(within(panel).getByText("辰酉卯")).toBeVisible();
    expect(within(panel).queryByText("传法")).not.toBeInTheDocument();
    expect(screen.queryByText("display_text")).not.toBeInTheDocument();
    expect(screen.queryByText("lesson_method")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-DL/)).not.toBeInTheDocument();
  });

  it("does not invent a method sentence from lessons, transmissions, disallowed keys, or legacy aliases", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: {
            ...emptyFacts({
              lesson_method: lessonMethod({
                calculated_transmissions: "",
                primary: "",
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
    ruleKey: "state_general_landing_correspondence" | "wealth_void_miben",
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
      canonical_dimension: "correspondence",
      requested_dimension: "correspondence",
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

  it("renders the real Runtime relationship and timing observations through frozen field mappings", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: emptyFacts({ dimension_facts: goldenDimensionFacts() }),
        })}
      />,
    );

    const block = panel();
    const relationship = within(block).getByRole("group", { name: "relationship" });
    const timing = within(block).getByRole("group", { name: "timing" });
    expect(within(relationship).getByText("LR-17")).toBeVisible();
    expect(within(relationship).getByText("主客关系：客体克主体")).toBeVisible();
    expect(within(timing).getByText("LM-R21")).toBeVisible();
    expect(
      within(timing).getByText("规则候选支：未 · 候选日期：2026-07-20（乙未日） · 相对节奏：较快"),
    ).toBeVisible();
    expect(block).not.toHaveTextContent(/object_overcomes_subject|candidate_branch|candidate_date|relative_speed/);
    expect(block).not.toHaveTextContent(/hard_verdict|吉凶|成败|大吉|大凶/);
  });

  it("renders authoritative outcome, money, state and work observations through neutral frozen mappings", () => {
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
            work: dimension({
              canonical_dimension: "work",
              requested_dimension: "work",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LM-R07",
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
                        {
                          stage: "final",
                          branch: "亥",
                          six_relative: "官鬼",
                          season_strength: "unknown",
                          is_xunkong: true,
                        },
                      ],
                      target_general_modifier: [
                        { ...correspondence, stage: "middle", heavenly_general: "天后", landing_branch: "酉", six_relative: "官鬼" },
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

    const block = panel();
    expect(within(block).getByRole("group", { name: "outcome" })).toHaveTextContent("结构关系：主体克客体");
    expect(within(block).getByRole("group", { name: "outcome" })).toHaveTextContent(
      "三传与日干关系：三传支均生日干",
    );
    expect(within(block).getByRole("group", { name: "outcome" })).toHaveTextContent("中传旬空：午");
    expect(within(block).getByRole("group", { name: "money" })).toHaveTextContent("妻财入传：初传 辰（旺）");
    expect(within(block).getByRole("group", { name: "money" })).toHaveTextContent("妻财旬空：初传 辰");
    expect(within(block).getByRole("group", { name: "state" })).toHaveTextContent(
      "天将落地类象：初传 勾陈落辰 · 共 1 条",
    );
    expect(within(block).getByRole("group", { name: "work" })).toHaveTextContent(
      "工作所取六亲：官鬼 · 入传状态：中传 酉（囚，非旬空）、末传 亥（强弱未提供，旬空） · 天将落地类象：中传 天后落酉、末传 白虎落亥（无精确类象对应）",
    );
    expect(block).not.toHaveTextContent(
      /subject_overcomes_object|subject_generates_object|wealth_presence|matched_count|target_relative|source_correspondence_matched/,
    );
    expect(block).not.toHaveTextContent(/吉凶|成败|大吉|大凶|hard_verdict/);
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
            correspondence: dimension(),
            host_guest: dimension({
              canonical_dimension: "host_guest",
              requested_dimension: "host_guest",
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LR-17",
                    observation: { text: "日干生初传" },
                    polarity: "oppose",
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
    expect(within(block).getByRole("group", { name: "correspondence" })).toBeVisible();
    expect(within(block).getByRole("group", { name: "host_guest" })).toBeVisible();
    expect(within(block).getByText("LM-R01")).toBeVisible();
    expect(within(block).getByText("初传与日干同类")).toBeVisible();
    expect(within(block).getByText("LR-17")).toBeVisible();
    expect(within(block).getByText("日干生初传")).toBeVisible();
    expect(within(block).queryByText("忽略观察")).not.toBeInTheDocument();
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
              canonical_dimension: "correspondence",
              rule_evidence: evidence(),
            },
            keep: dimension({
              canonical_dimension: "host_guest",
              requested_dimension: "host_guest",
              rule_evidence: evidence({
                matched: [matchedEntry({ rule_id: "LR-17", observation: { note: "主客比和" } })],
              }),
            }),
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).queryByRole("group", { name: "timing" })).not.toBeInTheDocument();
    expect(within(block).queryByText("auspicious")).not.toBeInTheDocument();
    expect(within(block).getByRole("group", { name: "host_guest" })).toBeVisible();
    expect(within(block).getByText("主客比和")).toBeVisible();
  });

  it("drops matched rows without a rule id or observation text, and skips unknown observation keys", () => {
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            correspondence: dimension({
              rule_evidence: evidence({
                matched: [
                  matchedEntry({ rule_id: "", observation: { display_text: "空规则" } }),
                  matchedEntry({ rule_id: "LM-R01", observation: { primary: "发明事实" } }),
                  matchedEntry({
                    rule_id: "LM-R21",
                    observation: { display_text: "", fact_text: "  ", text: "应期在传支" },
                  }),
                ],
              }),
            }),
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).queryByText("空规则")).not.toBeInTheDocument();
    expect(within(block).queryByText("发明事实")).not.toBeInTheDocument();
    expect(within(block).getByText("LM-R21")).toBeVisible();
    expect(within(block).getByText("应期在传支")).toBeVisible();
  });

  it("preserves every Runtime source ref in order without claiming exact verification", async () => {
    const user = userEvent.setup();
    const stateSources = runtimeRuleSourceRefs("state_general_landing_correspondence");
    const moneySources = runtimeRuleSourceRefs("wealth_void_miben");
    render(
      <DaliurenBoard
        view={chart({
          core_facts: factsWithDimensions({
            correspondence: dimension({
              rule_evidence: evidence({
                matched: [
                  matchedEntry({
                    rule_id: "LM-R01",
                    observation: { label: "类象规则命中" },
                    source_refs: stateSources,
                  }),
                  matchedEntry({
                    rule_id: "LM-R20",
                    observation: { name: "求财规则命中" },
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
    const stateEntry = within(block).getByText("类象规则命中").closest("li");
    const moneyEntry = within(block).getByText("求财规则命中").closest("li");
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
            empty: dimension({ rule_evidence: evidence({ matched: [] }) }),
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(screen.queryByText("暂无证据")).not.toBeInTheDocument();
  });

  it("keeps loading and silhouette modes free of dimension evidence", () => {
    const view = chart({
      core_facts: factsWithDimensions({ correspondence: dimension() }),
    });
    const { rerender } = render(<DaliurenBoard view={view} mode="loading" />);
    expect(screen.queryByText("维度证据")).not.toBeInTheDocument();
    expect(screen.queryByText("LM-R01")).not.toBeInTheDocument();

    rerender(<DaliurenBoard view={view} mode="silhouette" />);
    expect(screen.queryByText("LM-R01")).not.toBeInTheDocument();
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
    expect(within(block).getByText("旬空：辰巳")).toBeVisible();
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
