import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { RuntimeChart } from "@/components/readings/runtime-chart";
import type {
  LiuyaoChartViewModel,
  LiuyaoNotRequestedRoleAdjudication,
  LiuyaoRoleAdjudication,
  LiuyaoSeasonalStrengthAdjudication,
  LiuyaoSpecificLineAdjudication,
  LiuyaoStrengthCandidate,
  LiuyaoStrengthEvidence,
  LiuyaoUsefulSpiritSelection,
} from "@/view-models/registry";

afterEach(cleanup);

type CoreFacts = NonNullable<LiuyaoChartViewModel["core_facts"]>;

function emptyFacts(overrides: Partial<CoreFacts> = {}): CoreFacts {
  return {
    calendar: null,
    casting: null,
    casting_method: null,
    changed_najia: null,
    changed_plate_lines: null,
    changed_six_relatives: null,
    hidden_lines: null,
    interpretation_status: null,
    line_facts: null,
    lines: null,
    month_day_strength: null,
    moving_lines: null,
    najia: null,
    relation_facts: null,
    returning_relations: null,
    requested_useful_spirit_candidates: null,
    shi_ying: null,
    shi_ying_moving_relations: null,
    six_relatives: null,
    six_spirit_profile: null,
    six_spirits: null,
    useful_spirit_candidates: null,
    useful_spirit_selection: null,
    xunkong: null,
    ...overrides,
  };
}

const NAJIA = [
  { stem: "丁", branch: "巳", ganzhi: "丁巳", element: "火", source_dependency_id: "liuyao.chart.najia" },
  { stem: "丁", branch: "卯", ganzhi: "丁卯", element: "木", source_dependency_id: "liuyao.chart.najia" },
  { stem: "丁", branch: "丑", ganzhi: "丁丑", element: "土", source_dependency_id: "liuyao.chart.najia" },
  { stem: "丙", branch: "申", ganzhi: "丙申", element: "金", source_dependency_id: "liuyao.chart.najia" },
  { stem: "丙", branch: "午", ganzhi: "丙午", element: "火", source_dependency_id: "liuyao.chart.najia" },
  { stem: "丙", branch: "辰", ganzhi: "丙辰", element: "土", source_dependency_id: "liuyao.chart.najia" },
] as const;

const RELATIVES = ["兄弟", "子孙", "妻财", "官鬼", "父母", "兄弟"] as const;
const CHANGED_NAJIA = [
  { stem: "辛", branch: "未", ganzhi: "辛未", element: "土", source_dependency_id: "liuyao.chart.najia" },
  { stem: "辛", branch: "巳", ganzhi: "辛巳", element: "火", source_dependency_id: "liuyao.chart.najia" },
  { stem: "辛", branch: "卯", ganzhi: "辛卯", element: "木", source_dependency_id: "liuyao.chart.najia" },
  { stem: "庚", branch: "午", ganzhi: "庚午", element: "火", source_dependency_id: "liuyao.chart.najia" },
  { stem: "庚", branch: "辰", ganzhi: "庚辰", element: "土", source_dependency_id: "liuyao.chart.najia" },
  { stem: "庚", branch: "寅", ganzhi: "庚寅", element: "木", source_dependency_id: "liuyao.chart.najia" },
] as const;
const CHANGED_RELATIVES = ["子孙", "妻财", "官鬼", "父母", "兄弟", "子孙"] as const;
const CHANGED_PLATE = [
  { line: 1, yin_yang: "阴" },
  { line: 2, yin_yang: "阳" },
  { line: 3, yin_yang: "阴" },
  { line: 4, yin_yang: "阳" },
  { line: 5, yin_yang: "阴" },
  { line: 6, yin_yang: "阳" },
] as const;
const SPIRITS = ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"] as const;
const HIDDEN = [
  {
    line: 3,
    najia: { stem: "己", branch: "亥", ganzhi: "己亥", element: "水", source_dependency_id: "liuyao.chart.najia" },
    six_relative: "官鬼",
    source_dependency_id: "liuyao.plate.najia-six-relatives-hidden-lines",
    source_plate: "离为火",
    status: "source_derived_hidden_line_candidate",
  },
] as const;

function chart(overrides: Partial<LiuyaoChartViewModel> = {}): LiuyaoChartViewModel {
  return {
    schema_version: "liuyao-chart/v1",
    subject_ref: "liuyao:s3-fixture",
    question: "这次求财如何？",
    primary_hexagram: {
      name: "山泽损",
      upper_trigram: "艮",
      lower_trigram: "兑",
    },
    changed_hexagram: {
      name: "风泽中孚",
      upper_trigram: "巽",
      lower_trigram: "兑",
    },
    lines: [
      { position: 1, value: 9, moving: true },
      { position: 2, value: 8, moving: false },
      { position: 3, value: 7, moving: false },
      { position: 4, value: 6, moving: true },
      { position: 5, value: 8, moving: false },
      { position: 6, value: 7, moving: false },
    ],
    core_facts: null,
    ...overrides,
  };
}

function tower() {
  return screen.getByRole("region", { name: "卦盘" });
}

function glyphTable() {
  return screen.getByRole("table", { name: "六爻爻塔" });
}

describe("/liuyao S3 爻塔骨架", () => {
  it("renders hexagram headers and bottom-up line glyphs from typed fields", () => {
    render(<RuntimeChart viewModel={chart()} />);

    const board = tower();
    expect(within(board).getByText("山泽损")).toBeVisible();
    expect(within(board).getByText("上艮下兑")).toBeVisible();
    expect(within(board).getByText("风泽中孚")).toBeVisible();
    expect(within(board).getByText("上巽下兑")).toBeVisible();
    expect(board.querySelector('[class*="trigramName"]')?.textContent).toBeTruthy();

    const rows = glyphTable().querySelectorAll("tbody tr");
    expect(rows).toHaveLength(6);
    expect(rows[5]?.textContent).toContain("初爻");
    expect(rows[0]?.textContent).toContain("上爻");
    expect(rows[5]?.querySelector("[data-kind='yang'][data-moving='true']")).toBeTruthy();
    expect(rows[4]?.querySelector("[data-kind='yin'][data-moving='false']")).toBeTruthy();
    expect(rows[3]?.querySelector("[data-kind='yang'][data-moving='false']")).toBeTruthy();
    expect(rows[2]?.querySelector("[data-kind='yin'][data-moving='true']")).toBeTruthy();
    expect(rows[5]?.querySelector("[class*='movingMark']")?.textContent).toContain("○");
    expect(rows[2]?.querySelector("[class*='movingMark']")?.textContent).toContain("×");

    expect(within(board).queryByText("无变卦")).not.toBeInTheDocument();
    expect(within(board).queryByText("六神")).not.toBeInTheDocument();
    expect(within(board).queryByText("纳甲")).not.toBeInTheDocument();
    expect(within(board).queryByText("六亲")).not.toBeInTheDocument();
    expect(within(board).queryByText("伏神")).not.toBeInTheDocument();
    expect(within(board).queryByText("世")).not.toBeInTheDocument();
    expect(within(board).queryByText("应")).not.toBeInTheDocument();
    expect(within(board).queryByText("卦宫")).not.toBeInTheDocument();
    expect(within(board).queryByText("问题类别")).not.toBeInTheDocument();
    expect(within(board).queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(within(board).queryByText(/大吉|大凶/)).not.toBeInTheDocument();
  });

  it("drops the changed column when changed_hexagram is null and never invents placeholders", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          changed_hexagram: null,
        })}
      />,
    );

    const board = tower();
    expect(within(board).getByText("山泽损")).toBeVisible();
    expect(within(board).queryByText("变卦")).not.toBeInTheDocument();
    expect(within(board).queryByText("风泽中孚")).not.toBeInTheDocument();
    expect(within(board).queryByText("无变卦")).not.toBeInTheDocument();
    expect(within(board).queryByText("无")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "查看变卦" })).not.toBeInTheDocument();
    expect(glyphTable().querySelectorAll("thead th")).toHaveLength(2);
  });

  it("keeps the changed glyphs behind a narrow-viewport toggle", async () => {
    const user = userEvent.setup();
    render(<RuntimeChart viewModel={chart()} />);

    const table = glyphTable();
    expect(table).toHaveAttribute("data-show-changed", "false");
    await user.click(screen.getByRole("button", { name: "查看变卦", hidden: true }));
    expect(table).toHaveAttribute("data-show-changed", "true");
    expect(table.querySelectorAll("thead th")).toHaveLength(3);
    expect(table.querySelector("tbody tr")?.querySelectorAll("[data-kind]").length).toBeGreaterThan(1);

    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/liuyao-line-tower.module.css"),
      "utf8",
    );
    expect(css).toMatch(
      /@media \(max-width: 47\.999rem\)[\s\S]*\[data-show-changed="false"\] \.changedCol\s*\{[^}]*display:\s*none/s,
    );
    expect(css).toMatch(/\.tower\s*\{[^}]*overflow-x:\s*clip/s);
  });
});

describe("/liuyao S3 爻塔纳甲/六亲/世应列", () => {
  it("renders nailed najia, six_relatives and shi_ying columns aligned bottom-up", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            najia: [...NAJIA],
            six_relatives: [...RELATIVES],
            shi_ying: { shi: 3, ying: 6 },
            hidden_lines: [{ line: 4 }],
          }),
        })}
      />,
    );

    const board = tower();
    const table = glyphTable();
    const rows = table.querySelectorAll("tbody tr");
    expect(within(table).getByText("纳甲")).toBeVisible();
    expect(within(table).getByText("六亲")).toBeVisible();
    expect(within(table).getByText("世应")).toBeVisible();
    expect(rows[5]?.textContent).toContain("丁巳");
    expect(rows[5]?.textContent).toContain("兄弟");
    expect(rows[3]?.textContent).toContain("丁丑");
    expect(rows[3]?.textContent).toContain("妻财");
    expect(rows[3]?.querySelector("[data-mark='shi']")?.textContent).toBe("世");
    expect(rows[0]?.textContent).toContain("丙辰");
    expect(rows[0]?.querySelector("[data-mark='ying']")?.textContent).toBe("应");
    expect(rows[3]).toHaveAttribute("data-role", "shi");
    expect(rows[5]?.querySelector("[data-element='fire']")?.textContent).toContain("丁巳");
    expect(within(board).queryByText("六神")).not.toBeInTheDocument();
    expect(within(board).queryByText("伏神")).not.toBeInTheDocument();
    expect(within(board).queryByText(/GAP-LY/)).not.toBeInTheDocument();

    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/liuyao-line-tower.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.najia\s*\{[^}]*font-size:\s*var\(--font-size-body\)/s);
    expect(css).toMatch(/\.najia\[data-element="wood"\]\s*\{[^}]*var\(--element-wood\)/s);
    expect(css).toMatch(/\.relative\s*\{[^}]*font-size:\s*var\(--font-size-aux\)/s);
    expect(css).toMatch(/\.seal\s*\{[^}]*font-size:\s*var\(--font-size-body\)/s);
    expect(css).toMatch(/tr\[data-role="shi"\]\s*\{[^}]*1px/s);
  });

  it("drops each column independently when its nailed field is missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            six_relatives: [...RELATIVES],
            shi_ying: { shi: 3, ying: 6 },
          }),
        })}
      />,
    );

    let table = glyphTable();
    expect(within(table).queryByText("纳甲")).not.toBeInTheDocument();
    expect(within(table).getByText("六亲")).toBeVisible();
    expect(within(table).getByText("世应")).toBeVisible();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            najia: NAJIA.slice(0, 5),
            six_relatives: ["兄弟", "子孙"],
            shi_ying: { shi_line: 3, ying_line: 6 },
          }),
        })}
      />,
    );
    table = glyphTable();
    expect(within(table).queryByText("纳甲")).not.toBeInTheDocument();
    expect(within(table).queryByText("六亲")).not.toBeInTheDocument();
    expect(within(table).queryByText("世应")).not.toBeInTheDocument();
    expect(within(table).queryByText("世", { exact: true })).not.toBeInTheDocument();
    expect(within(table).queryByText("应", { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });
});

describe("/liuyao S3 爻塔六神列", () => {
  it("renders nailed six_spirits as a bottom-up neutral chip column", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            six_spirits: [...SPIRITS],
            hidden_lines: [{ line: 4 }],
          }),
        })}
      />,
    );

    const board = tower();
    const table = glyphTable();
    const rows = table.querySelectorAll("tbody tr");
    const headers = [...table.querySelectorAll("thead th")].map((node) => node.textContent);
    expect(headers.indexOf("六神")).toBeGreaterThan(-1);
    expect(headers.indexOf("六神")).toBeLessThan(headers.indexOf("本卦"));
    expect(rows[5]?.textContent).toContain("青龙");
    expect(rows[4]?.textContent).toContain("朱雀");
    expect(rows[3]?.textContent).toContain("勾陈");
    expect(rows[2]?.textContent).toContain("螣蛇");
    expect(rows[1]?.textContent).toContain("白虎");
    expect(rows[0]?.textContent).toContain("玄武");
    expect(rows[5]?.querySelector("[class*='spirit']")?.textContent).toBe("青龙");
    expect(within(board).queryByText("伏神")).not.toBeInTheDocument();
    expect(within(board).queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(within(board).queryByText(/大吉|大凶/)).not.toBeInTheDocument();

    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/liuyao-line-tower.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.spirit\s*\{[^}]*font-size:\s*var\(--font-size-aux\)/s);
    expect(css).toMatch(/\.spirit\s*\{[^}]*var\(--color-text-secondary\)/s);
    expect(css).not.toMatch(/\.spirit\[[^\]]*\]\s*\{[^}]*--element-/s);
  });

  it("drops the whole six_spirits column when missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            six_relatives: [...RELATIVES],
          }),
        })}
      />,
    );

    let table = glyphTable();
    expect(within(table).queryByText("六神")).not.toBeInTheDocument();
    expect(within(table).getByText("六亲")).toBeVisible();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            six_spirits: ["青龙", "朱雀", "勾陈", "白虎", "玄武"],
          }),
        })}
      />,
    );
    table = glyphTable();
    expect(within(table).queryByText("六神")).not.toBeInTheDocument();
    expect(within(table).queryByText("青龙")).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            six_spirits: ["青龙", "朱雀", "勾陈", "未知", "白虎", "玄武"],
          }),
        })}
      />,
    );
    table = glyphTable();
    expect(within(table).queryByText("六神")).not.toBeInTheDocument();
    expect(within(table).queryByText("青龙")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });
});

describe("/liuyao S3 爻塔伏神列", () => {
  it("renders nailed hidden_lines only on matching positions", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            hidden_lines: [...HIDDEN],
            six_spirits: [...SPIRITS],
          }),
        })}
      />,
    );

    const board = tower();
    const table = glyphTable();
    const rows = table.querySelectorAll("tbody tr");
    const headers = [...table.querySelectorAll("thead th")].map((node) => node.textContent);
    expect(headers.indexOf("伏神")).toBeGreaterThan(headers.indexOf("六神"));
    expect(headers.indexOf("伏神")).toBeLessThan(headers.indexOf("本卦"));
    expect(rows[3]?.querySelector("[class*='hidden']")?.textContent).toBe("伏：官鬼亥水");
    expect(rows[5]?.textContent).not.toContain("伏：");
    expect(rows[0]?.textContent).not.toContain("伏：");
    expect(within(board).queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(within(board).queryByText(/大吉|大凶/)).not.toBeInTheDocument();

    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/liuyao-line-tower.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.hidden\s*\{[^}]*font-size:\s*var\(--font-size-aux\)/s);
    expect(css).toMatch(/\.hidden\s*\{[^}]*var\(--color-text-secondary\)/s);
  });

  it("drops the whole hidden_lines column when missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            six_spirits: [...SPIRITS],
          }),
        })}
      />,
    );

    let table = glyphTable();
    expect(within(table).queryByText("伏神")).not.toBeInTheDocument();
    expect(within(table).getByText("六神")).toBeVisible();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            hidden_lines: [{ line: 4 }],
          }),
        })}
      />,
    );
    table = glyphTable();
    expect(within(table).queryByText("伏神")).not.toBeInTheDocument();
    expect(within(table).queryByText(/伏：/)).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            hidden_lines: [
              {
                position: 3,
                relative: "官鬼",
                stem: "己",
                branch: "亥",
                element: "水",
              },
            ],
          }),
        })}
      />,
    );
    table = glyphTable();
    expect(within(table).queryByText("伏神")).not.toBeInTheDocument();
    expect(within(table).queryByText(/伏：/)).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });
});

describe("/liuyao S3 爻塔变卦列事实", () => {
  it("renders nailed changed plate/najia/relative sub-items and mutes static rows", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            changed_plate_lines: [...CHANGED_PLATE],
            changed_najia: [...CHANGED_NAJIA],
            changed_six_relatives: [...CHANGED_RELATIVES],
            najia: [...NAJIA],
            six_relatives: [...RELATIVES],
          }),
        })}
      />,
    );

    const board = tower();
    const table = glyphTable();
    const rows = table.querySelectorAll("tbody tr");
    const first = rows[5]?.querySelector("[class*='changedCol']");
    const fourth = rows[2]?.querySelector("[class*='changedCol']");
    const second = rows[4]?.querySelector("[class*='changedCol']");
    expect(first?.querySelector("[data-kind='yin'][data-moving='false']")).toBeTruthy();
    expect(first?.textContent).toContain("辛未");
    expect(first?.textContent).toContain("子孙");
    expect(first?.querySelector("[data-element='earth']")?.textContent).toContain("辛未");
    expect(fourth?.querySelector("[data-kind='yang'][data-moving='false']")).toBeTruthy();
    expect(fourth?.textContent).toContain("庚午");
    expect(fourth?.textContent).toContain("父母");
    expect(second?.textContent).toContain("辛巳");
    expect(second?.textContent).toContain("妻财");
    expect(first?.querySelector("[data-tone='focus']")).toBeTruthy();
    expect(fourth?.querySelector("[data-tone='focus']")).toBeTruthy();
    expect(second?.querySelector("[data-tone='muted']")).toBeTruthy();
    expect(rows[5]?.textContent).toContain("丁巳");
    expect(within(board).queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(within(board).queryByText(/大吉|大凶/)).not.toBeInTheDocument();

    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/liuyao-line-tower.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.changedFact\[data-tone="muted"\]\s*\{[^}]*opacity:/s);
  });

  it("drops each changed sub-item independently when its nailed field is missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            changed_najia: [...CHANGED_NAJIA],
            changed_six_relatives: [...CHANGED_RELATIVES],
          }),
        })}
      />,
    );

    let table = glyphTable();
    let first = table.querySelectorAll("tbody tr")[5]?.querySelector("[class*='changedCol']");
    expect(first?.querySelector("[data-kind='yang'][data-moving='false']")).toBeTruthy();
    expect(first?.textContent).toContain("辛未");
    expect(first?.textContent).toContain("子孙");
    expect(within(table).getByText("变卦")).toBeVisible();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            changed_plate_lines: CHANGED_PLATE.slice(0, 5),
            changed_najia: CHANGED_NAJIA.slice(0, 5),
            changed_six_relatives: ["子孙", "妻财"],
          }),
        })}
      />,
    );
    table = glyphTable();
    first = table.querySelectorAll("tbody tr")[5]?.querySelector("[class*='changedCol']");
    expect(first?.querySelector("[data-kind='yang'][data-moving='false']")).toBeTruthy();
    expect(first?.querySelector("[data-kind='yin']")).toBeFalsy();
    expect(first?.textContent).not.toContain("辛未");
    expect(first?.textContent).not.toContain("子孙");
    expect(within(table).getByText("变卦")).toBeVisible();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            changed_plate_lines: [
              { position: 1, yin_yang: "阴" },
              { line: 2, yin_yang: "阳" },
              { line: 3, yin_yang: "阴" },
              { line: 4, yin_yang: "阳" },
              { line: 5, yin_yang: "阴" },
              { line: 6, yin_yang: "阳" },
            ],
            changed_najia: [{ ganzhi: "辛未", element: "土" }],
            changed_six_relatives: ["未知", "妻财", "官鬼", "父母", "兄弟", "子孙"],
          }),
        })}
      />,
    );
    table = glyphTable();
    first = table.querySelectorAll("tbody tr")[5]?.querySelector("[class*='changedCol']");
    expect(first?.querySelector("[data-kind='yang'][data-moving='false']")).toBeTruthy();
    expect(first?.querySelector("[data-kind='yin']")).toBeFalsy();
    expect(first?.textContent).not.toContain("辛未");
    expect(first?.textContent).not.toContain("子孙");
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });
});

describe("/liuyao S3 求测信息条", () => {
  function inquiry() {
    return screen.getByRole("region", { name: "求测信息" });
  }

  it("renders question, casting method, calendar and xunkong from nailed fields", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            casting_method: "supplied_complete_cast",
            calendar: {
              month_ganzhi: "辛酉",
              month_branch: "酉",
              day_ganzhi: "丙午",
              day_stem: "丙",
              day_branch: "午",
            },
            xunkong: {
              day_ganzhi: "丙午",
              void_branches: ["辰", "巳"],
              source_dependency_id: "liuyao.calendar.xunkong-month-day-relations",
            },
          }),
        })}
      />,
    );

    const bar = inquiry();
    expect(within(bar).getByText("这次求财如何？")).toBeVisible();
    expect(within(bar).getByText("提供完整卦象")).toBeVisible();
    expect(within(bar).getByText("月建酉 · 日辰丙午")).toBeVisible();
    expect(within(bar).getByText("旬空：辰巳")).toBeVisible();
    expect(within(bar).queryByText(/2026-08-21/)).not.toBeInTheDocument();
    expect(within(bar).queryByText(/supplied_complete_cast/)).not.toBeInTheDocument();
    expect(within(bar).queryByText("问题类别")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(screen.queryByText(/大吉|大凶/)).not.toBeInTheDocument();
  });

  it("maps known casting_method labels and drops unknown or missing methods", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({ casting_method: "digital_coin" }),
        })}
      />,
    );
    expect(within(inquiry()).getByText("三枚硬币记录")).toBeVisible();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({ casting_method: "manual" }),
        })}
      />,
    );
    expect(within(inquiry()).getByText("手动记录")).toBeVisible();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({ casting_method: "time" }),
        })}
      />,
    );
    expect(within(inquiry()).queryByText("time")).not.toBeInTheDocument();
    expect(within(inquiry()).queryByText("按时间起卦")).not.toBeInTheDocument();
    expect(within(inquiry()).getByText("这次求财如何？")).toBeVisible();
  });

  it("drops calendar/xunkong independently when missing or unparseable and keeps question without core_facts", () => {
    const { rerender } = render(<RuntimeChart viewModel={chart()} />);
    const bar = inquiry();
    expect(within(bar).getByText("这次求财如何？")).toBeVisible();
    expect(within(bar).queryByText(/月建/)).not.toBeInTheDocument();
    expect(within(bar).queryByText(/日辰/)).not.toBeInTheDocument();
    expect(within(bar).queryByText(/旬空/)).not.toBeInTheDocument();
    expect(within(bar).queryByText("三枚硬币记录")).not.toBeInTheDocument();
    expect(within(bar).queryByText("手动记录")).not.toBeInTheDocument();
    expect(within(bar).queryByText("提供完整卦象")).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            casting_method: "digital_coin",
            calendar: {
              casting_datetime: "2026-08-21 22:10",
              month_branch: "酉",
              day_stem_branch: "丙午",
            },
            xunkong: { xun: "甲子", branches: ["辰", "巳"] },
          }),
        })}
      />,
    );
    expect(within(inquiry()).getByText("三枚硬币记录")).toBeVisible();
    expect(within(inquiry()).queryByText(/月建/)).not.toBeInTheDocument();
    expect(within(inquiry()).queryByText(/日辰/)).not.toBeInTheDocument();
    expect(within(inquiry()).queryByText(/旬空/)).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });

  it("folds a long question behind 展开", () => {
    const question = "这次求财如何，是否适合在本月推进这笔合作并签约？还要不要加码投入、调整节奏，以及把账期一起核清楚。";
    expect(question.length).toBeGreaterThan(48);
    render(
      <RuntimeChart
        viewModel={chart({
          question,
          core_facts: emptyFacts({ casting_method: "manual" }),
        })}
      />,
    );
    const bar = inquiry();
    expect(within(bar).getByText("展开")).toBeVisible();
    expect(within(bar).getByText(question)).toBeInTheDocument();
    expect(within(bar).getByText("手动记录")).toBeVisible();
  });
});

describe("/liuyao S3 M1 口径条", () => {
  function inquiry() {
    return screen.getByRole("region", { name: "求测信息" });
  }

  const calendar = {
    month_ganzhi: "辛酉",
    month_branch: "酉",
    day_ganzhi: "丙午",
    day_stem: "丙",
    day_branch: "午",
  } as const;

  const xunkong = {
    day_ganzhi: "丙午",
    void_branches: ["辰", "巳"],
    source_dependency_id: "liuyao.calendar.xunkong-month-day-relations",
  } as const;

  it("marks void najia cells from nailed xunkong and does not invent cast time", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            casting_method: "digital_coin",
            calendar: { ...calendar },
            xunkong: { ...xunkong },
            najia: [...NAJIA],
            casting: {
              cast_digest: "9e2182933ab47ecb1f7b537449d2f48b14d48f18c88532f88a08fd0e50408359",
              method: "digital_coin",
              provenance: { kind: "user_supplied_cast" },
              source_dependency_id: "liuyao.cast.six-tosses-and-hexagrams",
              tosses: [9, 8, 7, 6, 8, 7],
            },
          }),
        })}
      />,
    );

    const bar = inquiry();
    expect(within(bar).getByText("三枚硬币记录")).toBeVisible();
    expect(within(bar).getByText("月建酉 · 日辰丙午")).toBeVisible();
    expect(within(bar).getByText("旬空：辰巳")).toBeVisible();
    expect(within(bar).queryByText(/起卦/)).not.toBeInTheDocument();
    expect(within(bar).queryByText(/2026-08-21/)).not.toBeInTheDocument();
    expect(within(bar).queryByText(/cast_digest|user_supplied_cast|tosses/)).not.toBeInTheDocument();

    const rows = glyphTable().querySelectorAll("tbody tr");
    expect(rows[5]?.querySelector("[class*='voidMark']")?.textContent).toBe("空");
    expect(rows[0]?.querySelector("[class*='voidMark']")?.textContent).toBe("空");
    expect(rows[4]?.querySelector("[class*='voidMark']")).toBeNull();
    expect(rows[3]?.querySelector("[class*='voidMark']")).toBeNull();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(screen.queryByText(/大吉|大凶/)).not.toBeInTheDocument();
  });

  it("drops void marks and calendar when nailed fields are missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            najia: [...NAJIA],
            xunkong: { ...xunkong },
          }),
        })}
      />,
    );
    expect(glyphTable().querySelector("[class*='voidMark']")).toBeTruthy();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            najia: [...NAJIA],
            calendar: { month_branch: "酉", day_ganzhi: "丙午" },
            xunkong: { void_branches: ["辰", "巳"] },
          }),
        })}
      />,
    );
    expect(within(inquiry()).queryByText(/月建/)).not.toBeInTheDocument();
    expect(within(inquiry()).queryByText(/旬空/)).not.toBeInTheDocument();
    expect(glyphTable().querySelector("[class*='voidMark']")).toBeNull();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            calendar: { ...calendar },
            xunkong: { ...xunkong },
          }),
        })}
      />,
    );
    expect(within(inquiry()).getByText("月建酉 · 日辰丙午")).toBeVisible();
    expect(within(inquiry()).getByText("旬空：辰巳")).toBeVisible();
    expect(glyphTable().querySelector("[class*='voidMark']")).toBeNull();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });
});

const RELATION_FACTS = [
  {
    changed: CHANGED_NAJIA[0],
    original: NAJIA[0],
    relations: ["回头生"],
    fact_status: "calculated_relation_not_verdict",
    source_dependency_id: "liuyao.relations.returning-and-useful-spirit-candidates",
  },
  {
    changed: CHANGED_NAJIA[3],
    original: NAJIA[3],
    relations: ["回头克"],
    fact_status: "calculated_relation_not_verdict",
    source_dependency_id: "liuyao.relations.returning-and-useful-spirit-candidates",
  },
] as const;

describe("/liuyao S3 M4 关系事实", () => {
  function relations() {
    return screen.getByRole("region", { name: "关系事实" });
  }

  it("renders nailed relation_facts as clickable line sentences and ignores sibling M4 fields", async () => {
    const user = userEvent.setup();
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            najia: [...NAJIA],
            relation_facts: [...RELATION_FACTS],
            returning_relations: [...RELATION_FACTS],
            month_day_strength: [{ seasonal_state: "旺" }],
            six_spirit_profile: { day_stem: "丙" },
            shi_ying_moving_relations: { fact_status: "calculated_relation_not_verdict" },
          }),
        })}
      />,
    );

    const panel = relations();
    expect(within(panel).getByText("初爻动化回头生")).toBeVisible();
    expect(within(panel).getByText("四爻动化回头克")).toBeVisible();
    expect(within(panel).queryByText("回头生克")).not.toBeInTheDocument();
    expect(within(panel).queryByText("月日对爻强弱")).not.toBeInTheDocument();
    expect(within(panel).queryByText("六神档案")).not.toBeInTheDocument();
    expect(within(panel).queryByText("世应动爻关系")).not.toBeInTheDocument();
    expect(within(panel).queryByText("丙日起腾蛇")).not.toBeInTheDocument();
    expect(within(panel).queryByText(/relation_facts|source_dependency_id|calculated_relation/)).not.toBeInTheDocument();
    expect(within(panel).queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(within(panel).queryByText(/大吉|大凶/)).not.toBeInTheDocument();

    const rows = glyphTable().querySelectorAll("tbody tr");
    await user.click(within(panel).getByRole("button", { name: "四爻动化回头克" }));
    expect(rows[2]).toHaveAttribute("data-focus", "true");
    expect(rows[5]).not.toHaveAttribute("data-focus", "true");

    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/liuyao-line-tower.module.css"),
      "utf8",
    );
    expect(css).toMatch(/tr\[data-focus="true"\]\s*\{[^}]*1px/s);
    expect(css).toMatch(/\.relationFact\s*\{[^}]*min-height:\s*var\(--target-min\)/s);
  });

  it("drops the whole M4 block when relation_facts is missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            returning_relations: [...RELATION_FACTS],
            month_day_strength: [{ seasonal_state: "旺" }],
            six_spirit_profile: { day_stem: "丙" },
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "关系事实" })).not.toBeInTheDocument();
    expect(screen.queryByText("日辰冲二爻")).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            relation_facts: [],
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "关系事实" })).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            najia: [...NAJIA],
            relation_facts: [
              {
                from: "日辰",
                to: 2,
                relation: "冲",
              },
            ],
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "关系事实" })).not.toBeInTheDocument();
    expect(screen.queryByText("日辰冲二爻")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });

  it("keeps the fact sentence when najia is absent and does not invent a line click", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            relation_facts: [...RELATION_FACTS],
          }),
        })}
      />,
    );

    const panel = relations();
    expect(within(panel).getByText("丁巳化辛未 · 回头生")).toBeVisible();
    expect(within(panel).getByText("丙申化庚午 · 回头克")).toBeVisible();
    expect(within(panel).queryByText("初爻动化回头生")).not.toBeInTheDocument();
    expect(within(panel).queryByRole("button")).not.toBeInTheDocument();
    expect(glyphTable().querySelector("[data-focus]")).toBeNull();
  });
});

const SHI_YING_MOVING = {
  fact_status: "calculated_relation_not_verdict",
  source_dependency_id: "liuyao.relations.returning-and-useful-spirit-candidates",
  moving_to_candidates: [
    {
      branch_relation: "无直接冲合",
      element_relation: "动爻生候选",
      fact_status: "calculated_relation_not_verdict",
      shared_trines: [] as const,
      source_dependency_id: "liuyao.relations.returning-and-useful-spirit-candidates",
      source_line: 1,
      source_najia: NAJIA[0],
      source_role_label: "动爻",
      source_roles: [] as const,
      target_line: 1,
      target_najia: CHANGED_NAJIA[0],
      target_relative: "子孙",
      target_role_label: "候选",
      target_roles: [] as const,
      target_source: "changed_line",
    },
  ],
  shi_ying: {
    branch_relation: "无直接冲合",
    element_relation: "比和",
    fact_status: "calculated_relation_not_verdict",
    shared_trines: [] as const,
    source_dependency_id: "liuyao.relations.returning-and-useful-spirit-candidates",
    source_line: 3,
    source_najia: NAJIA[2],
    source_role_label: "世",
    source_roles: ["世"] as const,
    target_line: 6,
    target_najia: NAJIA[5],
    target_relative: "父母",
    target_role_label: "应",
    target_roles: ["应"] as const,
    target_source: "visible_line",
    shi_line: 3,
    ying_line: 6,
  },
} as const;

describe("/liuyao S3 M4 世应动爻关系", () => {
  function panel() {
    return screen.getByRole("region", { name: "世应动爻关系" });
  }

  it("renders nailed shi_ying_moving_relations and ignores sibling M4 fields", async () => {
    const user = userEvent.setup();
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            shi_ying_moving_relations: { ...SHI_YING_MOVING },
            returning_relations: [...RELATION_FACTS],
            month_day_strength: [{ seasonal_state: "旺" }],
            six_spirit_profile: { day_stem: "丙" },
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByText("三爻世与上爻应 · 比和")).toBeVisible();
    expect(within(block).getByText("初爻动爻与初爻子孙（变卦） · 动爻生候选")).toBeVisible();
    expect(screen.queryByRole("region", { name: "关系事实" })).not.toBeInTheDocument();
    expect(within(block).queryByText("回头生克")).not.toBeInTheDocument();
    expect(within(block).queryByText("月日对爻强弱")).not.toBeInTheDocument();
    expect(within(block).queryByText("六神档案")).not.toBeInTheDocument();
    expect(within(block).queryByText("丙日起腾蛇")).not.toBeInTheDocument();
    expect(within(block).queryByText(/source_dependency_id|calculated_relation|visible_line/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/大吉|大凶/)).not.toBeInTheDocument();

    const rows = glyphTable().querySelectorAll("tbody tr");
    await user.click(within(block).getByRole("button", { name: "三爻世与上爻应 · 比和" }));
    expect(rows[3]).toHaveAttribute("data-focus", "true");
    expect(rows[5]).not.toHaveAttribute("data-focus", "true");

    await user.click(within(block).getByRole("button", { name: "初爻动爻与初爻子孙（变卦） · 动爻生候选" }));
    expect(rows[5]).toHaveAttribute("data-focus", "true");
    expect(rows[3]).not.toHaveAttribute("data-focus", "true");
  });

  it("drops the whole block when shi_ying_moving_relations is missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            returning_relations: [...RELATION_FACTS],
            month_day_strength: [{ seasonal_state: "旺" }],
            six_spirit_profile: { day_stem: "丙" },
            shi_ying_moving_relations: { fact_status: "calculated_relation_not_verdict" },
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "世应动爻关系" })).not.toBeInTheDocument();
    expect(screen.queryByText("世爻临动爻")).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            shi_ying_moving_relations: {
              ...SHI_YING_MOVING,
              moving_to_candidates: [
                {
                  from: "世",
                  to: "动爻",
                  relation: "临",
                },
              ],
            },
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "世应动爻关系" })).not.toBeInTheDocument();
    expect(screen.queryByText("世爻临动爻")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });

  it("keeps the shi/ying sentence when moving_to_candidates is empty", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            shi_ying_moving_relations: {
              ...SHI_YING_MOVING,
              moving_to_candidates: [],
            },
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByText("三爻世与上爻应 · 比和")).toBeVisible();
    expect(within(block).queryByText("动爻生候选")).not.toBeInTheDocument();
    expect(within(block).getByRole("button", { name: "三爻世与上爻应 · 比和" })).toBeVisible();
  });
});

const SEASONAL = ["休", "相", "旺", "囚", "死", "休"] as const;
const DAY_RELATIONS = ["日克爻", "日生爻", "比和", "爻克日", "爻生日", "日克爻"] as const;

function monthDayStrength(index: number) {
  return {
    day: {
      branch: "午",
      branch_relation: "无直接冲合",
      clash: false,
      element: "火",
      element_relation: DAY_RELATIONS[index],
      shared_trines: [] as const,
    },
    month: {
      branch: "酉",
      branch_relation: "无直接冲合",
      break: false,
      element: "金",
      element_relation: "月克爻",
      shared_trines: [] as const,
    },
    fact_status: "calculated_relation_not_verdict",
    seasonal_state: SEASONAL[index],
    source_dependency_id: "liuyao.calendar.xunkong-month-day-relations",
  };
}

const MONTH_DAY_STRENGTH = [
  monthDayStrength(0),
  monthDayStrength(1),
  monthDayStrength(2),
  monthDayStrength(3),
  monthDayStrength(4),
  monthDayStrength(5),
] as const;

describe("/liuyao S3 M4 月日对爻强弱", () => {
  function panel() {
    return screen.getByRole("region", { name: "月日对爻强弱" });
  }

  it("renders nailed month_day_strength as the full six-line list and ignores sibling M4 fields", async () => {
    const user = userEvent.setup();
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            najia: [...NAJIA],
            month_day_strength: [...MONTH_DAY_STRENGTH],
            returning_relations: [...RELATION_FACTS],
            six_spirit_profile: { day_stem: "丙" },
            shi_ying_moving_relations: { fact_status: "calculated_relation_not_verdict" },
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByText("初爻巳火：月休 · 日克爻")).toBeVisible();
    expect(within(block).getByText("四爻申金：月囚 · 爻克日")).toBeVisible();
    expect(within(block).getByText("上爻辰土：月休 · 日克爻")).toBeVisible();
    expect(screen.queryByRole("region", { name: "关系事实" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "世应动爻关系" })).not.toBeInTheDocument();
    expect(within(block).queryByText("回头生克")).not.toBeInTheDocument();
    expect(within(block).queryByText("六神档案")).not.toBeInTheDocument();
    expect(within(block).queryByText("丙日起腾蛇")).not.toBeInTheDocument();
    expect(within(block).queryByText(/source_dependency_id|calculated_relation|seasonal_state/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/大吉|大凶/)).not.toBeInTheDocument();

    const rows = glyphTable().querySelectorAll("tbody tr");
    await user.click(within(block).getByRole("button", { name: "四爻申金：月囚 · 爻克日" }));
    expect(rows[2]).toHaveAttribute("data-focus", "true");
    expect(rows[5]).not.toHaveAttribute("data-focus", "true");

    await user.click(within(block).getByRole("button", { name: "初爻巳火：月休 · 日克爻" }));
    expect(rows[5]).toHaveAttribute("data-focus", "true");
    expect(rows[2]).not.toHaveAttribute("data-focus", "true");
  });

  it("drops the whole block when month_day_strength is missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            najia: [...NAJIA],
            returning_relations: [...RELATION_FACTS],
            six_spirit_profile: { day_stem: "丙" },
            month_day_strength: [{ seasonal_state: "旺" }],
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "月日对爻强弱" })).not.toBeInTheDocument();
    expect(screen.queryByText("初爻子水：月休 · 日克")).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            month_day_strength: MONTH_DAY_STRENGTH.slice(0, 5),
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "月日对爻强弱" })).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            month_day_strength: [
              { line: 1, month: "休", day: "克" },
              monthDayStrength(1),
              monthDayStrength(2),
              monthDayStrength(3),
              monthDayStrength(4),
              monthDayStrength(5),
            ],
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "月日对爻强弱" })).not.toBeInTheDocument();
    expect(screen.queryByText("初爻：月休")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });

  it("keeps the six-line list when najia is absent and still focuses by index", async () => {
    const user = userEvent.setup();
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            month_day_strength: [...MONTH_DAY_STRENGTH],
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByText("初爻：月休 · 日克爻")).toBeVisible();
    expect(within(block).getByText("四爻：月囚 · 爻克日")).toBeVisible();
    expect(within(block).queryByText("巳火")).not.toBeInTheDocument();
    expect(within(block).queryByText("申金")).not.toBeInTheDocument();

    const rows = glyphTable().querySelectorAll("tbody tr");
    await user.click(within(block).getByRole("button", { name: "四爻：月囚 · 爻克日" }));
    expect(rows[2]).toHaveAttribute("data-focus", "true");
  });
});

describe("/liuyao S3 M4 回头生克", () => {
  function panel() {
    return screen.getByRole("region", { name: "回头生克" });
  }

  it("renders nailed returning_relations as clickable line sentences and ignores sibling M4 fields", async () => {
    const user = userEvent.setup();
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            najia: [...NAJIA],
            returning_relations: [...RELATION_FACTS],
            month_day_strength: [{ seasonal_state: "旺" }],
            six_spirit_profile: { day_stem: "丙" },
            shi_ying_moving_relations: { fact_status: "calculated_relation_not_verdict" },
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByText("初爻动化回头生")).toBeVisible();
    expect(within(block).getByText("四爻动化回头克")).toBeVisible();
    expect(screen.queryByRole("region", { name: "关系事实" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "世应动爻关系" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "月日对爻强弱" })).not.toBeInTheDocument();
    expect(within(block).queryByText("六神档案")).not.toBeInTheDocument();
    expect(within(block).queryByText("丙日起腾蛇")).not.toBeInTheDocument();
    expect(within(block).queryByText(/source_dependency_id|calculated_relation/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/大吉|大凶/)).not.toBeInTheDocument();

    const rows = glyphTable().querySelectorAll("tbody tr");
    await user.click(within(block).getByRole("button", { name: "四爻动化回头克" }));
    expect(rows[2]).toHaveAttribute("data-focus", "true");
    expect(rows[5]).not.toHaveAttribute("data-focus", "true");
  });

  it("drops the whole block when returning_relations is missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            najia: [...NAJIA],
            relation_facts: [...RELATION_FACTS],
            month_day_strength: [{ seasonal_state: "旺" }],
            six_spirit_profile: { day_stem: "丙" },
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "回头生克" })).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            returning_relations: [],
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "回头生克" })).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            najia: [...NAJIA],
            returning_relations: [
              {
                from: "日辰",
                to: 2,
                relation: "冲",
              },
            ],
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "回头生克" })).not.toBeInTheDocument();
    expect(screen.queryByText("日辰冲二爻")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });

  it("keeps the fact sentence when najia is absent and does not invent a line click", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            returning_relations: [...RELATION_FACTS],
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByText("丁巳化辛未 · 回头生")).toBeVisible();
    expect(within(block).getByText("丙申化庚午 · 回头克")).toBeVisible();
    expect(within(block).queryByText("初爻动化回头生")).not.toBeInTheDocument();
    expect(within(block).queryByRole("button")).not.toBeInTheDocument();
    expect(glyphTable().querySelector("[data-focus]")).toBeNull();
  });
});

describe("/liuyao S3 M4 六神档案", () => {
  function panel() {
    return screen.getByRole("region", { name: "六神档案" });
  }

  it("renders a fold card from nailed six_spirit_profile and ignores sibling M4 fields", async () => {
    const user = userEvent.setup();
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            six_spirit_profile: {
              day_stem: "丙",
              source_dependency_id: "liuyao.plate.six-spirits",
            },
            month_day_strength: [{ seasonal_state: "旺" }],
            shi_ying_moving_relations: { fact_status: "calculated_relation_not_verdict" },
            six_spirits: ["朱雀", "勾陈", "螣蛇", "白虎", "玄武", "青龙"],
          }),
        })}
      />,
    );

    const block = panel();
    const fold = block.querySelector("details");
    expect(fold).not.toBeNull();
    expect(fold).not.toHaveAttribute("open");
    expect(within(block).getByText("六神档案")).toBeVisible();
    expect(screen.queryByRole("region", { name: "关系事实" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "回头生克" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "世应动爻关系" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "月日对爻强弱" })).not.toBeInTheDocument();
    expect(within(block).queryByText("丙日起腾蛇")).not.toBeInTheDocument();
    expect(within(block).queryByText("丙日起朱雀")).not.toBeInTheDocument();
    expect(within(block).queryByText(/source_dependency_id|liuyao\.plate/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/大吉|大凶/)).not.toBeInTheDocument();
    expect(within(block).queryByRole("button")).not.toBeInTheDocument();

    await user.click(within(block).getByText("六神档案"));
    expect(fold).toHaveAttribute("open");
    expect(within(block).getByText("丙日起六神")).toBeVisible();
    expect(glyphTable().querySelector("[data-focus]")).toBeNull();
  });

  it("drops the whole block when six_spirit_profile is missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            relation_facts: [...RELATION_FACTS],
            six_spirit_profile: { day_stem: "丙" },
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "六神档案" })).not.toBeInTheDocument();
    expect(screen.queryByText("丙日起六神")).not.toBeInTheDocument();
    expect(screen.queryByText("丙日起腾蛇")).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            six_spirit_profile: {
              day_stem: "",
              source_dependency_id: "liuyao.plate.six-spirits",
            },
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "六神档案" })).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            six_spirit_profile: {
              day_stem: "寅",
              source_dependency_id: "liuyao.plate.six-spirits",
            },
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "六神档案" })).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });
});

const SOURCE_HJC = {
  pack: "divination/huangjin-ce",
  rule_id: "HJC-R009",
  source_anchor: "references/books/divination/huangjin-ce/rules.md#HJC-R009",
  verification_status: "verified",
  binding_digest: "test-binding-digest",
} as const;

const SOURCE_ZR_STRENGTH = {
  pack: "divination/zengshan-buyi",
  rule_id: "ZR-05-05",
  source_anchor: "references/books/divination/zengshan-buyi/rules.md#ZR-05-05",
  verification_status: "verified",
  binding_digest: "strength-binding-digest",
} as const;

function seasonalAdjudication(
  line: 1 | 2 | 3 | 4 | 5 | 6,
  source: "visible_line" | "changed_line" | "hidden_line",
): LiuyaoSeasonalStrengthAdjudication {
  return {
    status: "adjudicated_seasonal_strength_band",
    decision_scope: "liuyao_candidate_month_order_strength_band",
    candidate_source: source,
    line,
    line_element: "金",
    month_element: "金",
    seasonal_state: "旺",
    strength_band: "旺相",
    whole_candidate_strength_verdict: null,
    outcome_verdict: null,
    source_ref: SOURCE_ZR_STRENGTH,
    unresolved_checks: ["日辰与空破动变"],
  };
}

function strengthCandidate(
  line: 1 | 2 | 3 | 4 | 5 | 6,
  source: "visible_line" | "changed_line" | "hidden_line" = "visible_line",
): LiuyaoStrengthCandidate {
  return {
    source,
    line,
    moving: true,
    xunkong: false,
    najia: { ...NAJIA[line - 1] },
    month_day_strength: { seasonal_state: "旺" },
    seasonal_adjudication: seasonalAdjudication(line, source),
    signals: [
      { signal: "seasonal_support", value: "旺", status: "candidate_signal" },
      { signal: "moving_line", value: true, status: "candidate_signal" },
      { signal: "day_clash", value: false, status: "candidate_signal" },
    ],
    status: "candidate_only",
    hard_verdict: null,
  };
}

function strengthEvidence(
  byRelative: LiuyaoStrengthEvidence["by_relative"] = {},
  status: LiuyaoStrengthEvidence["status"] = "candidate_only",
): LiuyaoStrengthEvidence {
  return {
    status,
    by_relative: byRelative,
    source_rules: [{ ...SOURCE_ZR_STRENGTH, role: "useful_spirit_month_order_strength_band" }],
    fact_status: "calculated_relation_not_verdict",
    hard_verdict: null,
    requires_school_adjudication: true,
    source_dependency_id: "liuyao.interpretation.useful-spirit-strength-evidence",
  };
}

function uniqueLineAdjudication(): LiuyaoSpecificLineAdjudication {
  return {
    status: "adjudicated_unique_visible_line",
    decision_scope: "finance_primary_relative_line_identity",
    primary_relative: "妻财",
    visible_candidate_count: 1,
    visible_candidate_lines: [4],
    moving_visible_candidate_count: 1,
    moving_visible_candidate_lines: [4],
    specific_line_selection: 4,
    derivation_basis: "verified_role_plus_runtime_unique_visible_candidate",
    selection_source_ref: SOURCE_HJC,
    hard_verdict: null,
  };
}

function multipleLineAdjudication(): LiuyaoSpecificLineAdjudication {
  return {
    status: "unresolved_multiple_visible_lines",
    decision_scope: "finance_primary_relative_line_identity",
    primary_relative: "妻财",
    visible_candidate_count: 2,
    visible_candidate_lines: [2, 4],
    moving_visible_candidate_count: 0,
    moving_visible_candidate_lines: [],
    specific_line_selection: null,
    derivation_basis: "verified_role_plus_runtime_multiple_visible_candidates",
    selection_source_ref: null,
    hard_verdict: null,
  };
}

function absentLineAdjudication(): LiuyaoSpecificLineAdjudication {
  return {
    status: "unresolved_no_visible_line",
    decision_scope: "finance_primary_relative_line_identity",
    primary_relative: "妻财",
    visible_candidate_count: 0,
    visible_candidate_lines: [],
    moving_visible_candidate_count: 0,
    moving_visible_candidate_lines: [],
    specific_line_selection: null,
    derivation_basis: "verified_role_plus_runtime_no_visible_candidate",
    selection_source_ref: null,
    hard_verdict: null,
  };
}

function financeRole(
  line: LiuyaoSpecificLineAdjudication = uniqueLineAdjudication(),
): LiuyaoRoleAdjudication {
  return {
    status: "adjudicated_question_role_set",
    decision_scope: "finance_useful_spirit_role_set",
    question_class: "finance",
    primary_relative: "妻财",
    supporting_relatives: ["子孙"],
    obstacle_attention_relatives: ["兄弟", "官鬼", "父母"],
    specific_line_selection: line.specific_line_selection,
    specific_line_adjudication: line,
    hard_verdict: null,
    source_ref: SOURCE_HJC,
    unresolved_checks: ["月日旺衰与空破冲合", "成败、应期与事件结果"],
  };
}

function notRequestedRole(): LiuyaoNotRequestedRoleAdjudication {
  return {
    status: "not_requested",
    decision_scope: null,
    question_class: null,
    primary_relative: null,
    supporting_relatives: [],
    obstacle_attention_relatives: [],
    specific_line_selection: null,
    hard_verdict: null,
    source_ref: null,
    unresolved_checks: ["问题类别尚未给出"],
  };
}

function usefulSpirit(
  overrides: {
    readonly role_adjudication?: LiuyaoUsefulSpiritSelection["role_adjudication"];
    readonly strength_evidence?: LiuyaoStrengthEvidence;
  } = {},
): LiuyaoUsefulSpiritSelection {
  return {
    status: "evidence_bound",
    reason: "角色与强弱是古籍规则与盘面事实的对齐，不是结论",
    query_word_matching: false,
    source_dependency_id: "liuyao.relations.returning-and-useful-spirit-candidates",
    chain_candidates: { status: "candidate_only" },
    strength_evidence: strengthEvidence({
      妻财: {
        status: "candidate_only",
        candidates: [strengthCandidate(4)],
        hard_verdict: null,
      },
      子孙: {
        status: "not_available",
        candidates: [],
        hard_verdict: null,
      },
    }),
    role_adjudication: financeRole(),
    question_context: {
      question_class: "finance",
      classification_source: "explicit_structured_input",
    },
    ...overrides,
  };
}

describe("/liuyao S3 M3 用神证据", () => {
  function panel() {
    return screen.getByRole("region", { name: "用神证据" });
  }

  it("renders nailed useful_spirit_selection as role, line, and strength evidence", async () => {
    const user = userEvent.setup();
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            useful_spirit_selection: usefulSpirit(),
            six_spirit_profile: { day_stem: "丙" },
            month_day_strength: [{ seasonal_state: "旺" }],
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByText("求财类问题")).toBeVisible();
    expect(within(block).getAllByText("妻财")[0]).toBeVisible();
    expect(within(block).getByText("子孙")).toBeVisible();
    expect(within(block).getByText("传统上需留意的角色")).toBeVisible();
    expect(within(block).getByText("兄弟")).toBeVisible();
    expect(within(block).getByText("官鬼")).toBeVisible();
    expect(within(block).getByText("父母")).toBeVisible();
    expect(within(block).getByText("角色与强弱是古籍规则与盘面事实的对齐，不是结论")).toBeVisible();
    expect(within(block).getByText("唯一可见候选已定位")).toBeVisible();
    expect(within(block).getByText("按已裁定角色与盘内唯一可见候选")).toBeVisible();
    expect(within(block).getByText("四爻（本卦）")).toBeVisible();
    expect(within(block).getByText("丙申金")).toBeVisible();
    expect(within(block).getByText("旺")).toBeVisible();
    expect(within(block).getByText("旺相")).toBeVisible();
    expect(within(block).getByText("得令")).toBeVisible();
    expect(within(block).getByText("动爻")).toBeVisible();
    expect(within(block).queryByText("日冲")).not.toBeInTheDocument();
    expect(within(block).queryByText("子孙（")).not.toBeInTheDocument();
    expect(within(block).getByText("以上为月令强弱证据，取用与断事属流派裁定，本页不代作结论")).toBeVisible();
    expect(screen.queryByRole("region", { name: "六神档案" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "月日对爻强弱" })).not.toBeInTheDocument();
    expect(within(block).queryByText(/source_dependency_id|visible_line|question_class/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/大吉|大凶|忌仇/)).not.toBeInTheDocument();

    const rows = glyphTable().querySelectorAll("tbody tr");
    expect(rows[2]).toHaveAttribute("data-useful", "true");
    expect(within(rows[2] as HTMLElement).getByText("用神")).toBeVisible();
    expect(rows[5]).not.toHaveAttribute("data-useful", "true");

    await user.click(within(block).getByRole("button", { name: "四爻（本卦）" }));
    expect(rows[2]).toHaveAttribute("data-focus", "true");

    await user.click(within(block).getAllByRole("button", { name: "HJC-R009" })[0]!);
    expect(screen.getByRole("dialog")).toHaveTextContent("references/books/divination/huangjin-ce/rules.md#HJC-R009");
    await user.click(screen.getByRole("button", { name: "关闭" }));

    await user.click(within(block).getByText("尚未裁定的检查 2 项"));
    expect(within(block).getByText("月日旺衰与空破冲合")).toBeVisible();
    expect(within(block).getByText("成败、应期与事件结果")).toBeVisible();
  });

  it("shrinks the role card when role_adjudication is not_requested", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            useful_spirit_selection: usefulSpirit({
              role_adjudication: notRequestedRole(),
              strength_evidence: strengthEvidence({}, "not_requested"),
            }),
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByText("选择问题类别后可查看用神角色与古籍出处")).toBeVisible();
    expect(within(block).getByText("返回修改")).toBeVisible();
    expect(within(block).queryByText("求财类问题")).not.toBeInTheDocument();
    expect(within(block).queryByText("妻财")).not.toBeInTheDocument();
    expect(within(block).queryByRole("table")).not.toBeInTheDocument();
    expect(glyphTable().querySelector("[data-useful]")).toBeNull();
    expect(within(block).queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });

  it("drops the whole block when useful_spirit_selection is missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            six_spirit_profile: {
              day_stem: "丙",
              source_dependency_id: "liuyao.plate.six-spirits",
            },
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "用神证据" })).not.toBeInTheDocument();
    expect(screen.queryByText("求财类问题")).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            useful_spirit_selection: {
              status: "guessed",
              role_adjudication: { status: "adjudicated_question_role_set" },
            } as unknown as CoreFacts["useful_spirit_selection"],
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "用神证据" })).not.toBeInTheDocument();
    expect(screen.queryByText("求财类问题")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });

  it("lists multiple visible candidates without picking and keeps no-visible as 伏神提示", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            useful_spirit_selection: usefulSpirit({
              strength_evidence: strengthEvidence({}, "not_requested"),
              role_adjudication: financeRole(multipleLineAdjudication()),
            }),
          }),
        })}
      />,
    );

    const block = panel();
    expect(within(block).getByText("多个候选并存")).toBeVisible();
    expect(within(block).getByText("二爻")).toBeVisible();
    expect(within(block).getByText("四爻")).toBeVisible();
    expect(glyphTable().querySelector("[data-useful]")).toBeNull();
    expect(within(glyphTable()).queryByText("用神")).not.toBeInTheDocument();

    await user.click(within(block).getByRole("button", { name: "四爻" }));
    expect(glyphTable().querySelectorAll("tbody tr")[2]).toHaveAttribute("data-focus", "true");

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            useful_spirit_selection: usefulSpirit({
              strength_evidence: strengthEvidence({}, "not_requested"),
              role_adjudication: financeRole(absentLineAdjudication()),
            }),
          }),
        })}
      />,
    );
    expect(within(panel()).getByText("卦中不现")).toBeVisible();
    expect(within(panel()).getByText("提示看伏神")).toBeVisible();
    expect(glyphTable().querySelector("[data-useful]")).toBeNull();
  });
});

const SOURCE_PATTERNS = [
  {
    rule_id: "divination/huangjin-ce#HJC-M001",
    local_rule_id: "HJC-M001",
    title: "求财先看妻财",
    source_pack: "divination/huangjin-ce",
    source_anchor: "references/books/divination/huangjin-ce/rules.md#HJC-M001",
    status: "predicate_matched_not_verdict" as const,
    fact_paths: ["fact:/chart_facts/output/line_facts/3/six_relative"],
    predicate_audit: ["四爻妻财可见"],
  },
  {
    rule_id: "divination/huozhu-lin#HZL-M001",
    local_rule_id: "HZL-M001",
    title: "先看世应",
    source_pack: "divination/huozhu-lin",
    source_anchor: "divination/huozhu-lin rules.md#L5-L22",
    status: "predicate_matched_not_verdict" as const,
    fact_paths: ["/chart_facts/output/shi_ying"],
    predicate_audit: ["世应位置已返回"],
  },
] as const;

describe("/liuyao S3 M5 古法命中", () => {
  function panel() {
    return screen.getByRole("region", { name: "古法命中" });
  }

  it("renders nailed source_conditioned_patterns as a collapsed verifiable drawer", async () => {
    const user = userEvent.setup();
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            source_conditioned_patterns: [...SOURCE_PATTERNS],
            six_spirit_profile: { day_stem: "丙" },
            month_day_strength: [{ seasonal_state: "旺" }],
          }),
        })}
      />,
    );

    const block = panel();
    const fold = block.querySelector("details");
    expect(fold).not.toBeNull();
    expect(fold).not.toHaveAttribute("open");
    expect(within(block).getByText("命中古法 2 条 · 可核验")).toBeVisible();
    expect(within(block).queryByText("求财先看妻财")).not.toBeVisible();
    expect(screen.queryByRole("region", { name: "六神档案" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "月日对爻强弱" })).not.toBeInTheDocument();
    expect(screen.queryByText("source_conditioned_patterns")).not.toBeInTheDocument();
    expect(within(block).queryByText(/fact_paths|line_facts|predicate_matched/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(within(block).queryByText(/大吉|大凶/)).not.toBeInTheDocument();

    await user.click(within(block).getByText("命中古法 2 条 · 可核验"));
    expect(fold).toHaveAttribute("open");
    expect(within(block).getByText("求财先看妻财")).toBeVisible();
    expect(within(block).getByText("黄金策")).toBeVisible();
    expect(within(block).getByText("先看世应")).toBeVisible();
    expect(within(block).getByText("火珠林")).toBeVisible();
    expect(within(block).getAllByText("条件命中，非断语")).toHaveLength(2);
    expect(within(block).getByText("references/books/divination/huangjin-ce/rules.md#HJC-M001")).toBeVisible();
    expect(within(block).getByText("divination/huozhu-lin rules.md#L5-L22")).toBeVisible();
    expect(within(block).getByText("四爻妻财可见")).toBeVisible();
    expect(within(block).getByText("世应位置已返回")).toBeVisible();
    expect(within(block).queryByText(/chart_facts|line_facts\/3/)).not.toBeInTheDocument();

    const rows = glyphTable().querySelectorAll("tbody tr");
    await user.click(within(block).getByRole("button", { name: "求财先看妻财" }));
    expect(rows[2]).toHaveAttribute("data-focus", "true");
    expect(rows[5]).not.toHaveAttribute("data-focus", "true");

    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/liuyao-line-tower.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.evidenceSummary\s*\{[^}]*min-height:\s*var\(--target-min\)/s);
    expect(css).toMatch(/\.evidenceDrawer\s*\{[^}]*--color-evidence-line/s);
  });

  it("drops the whole block when source_conditioned_patterns is missing or unparseable", () => {
    const { rerender } = render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            six_spirit_profile: {
              day_stem: "丙",
              source_dependency_id: "liuyao.plate.six-spirits",
            },
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "古法命中" })).not.toBeInTheDocument();
    expect(screen.queryByText("命中古法")).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            source_conditioned_patterns: [],
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "古法命中" })).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            source_conditioned_patterns: [
              {
                title: "求财先看妻财",
                source_pack: "divination/huangjin-ce",
              },
            ] as unknown as CoreFacts["source_conditioned_patterns"],
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "古法命中" })).not.toBeInTheDocument();
    expect(screen.queryByText("求财先看妻财")).not.toBeInTheDocument();

    rerender(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            source_conditioned_patterns: [
              {
                ...SOURCE_PATTERNS[0],
                status: "candidate_only",
              },
            ] as unknown as CoreFacts["source_conditioned_patterns"],
          }),
        })}
      />,
    );
    expect(screen.queryByRole("region", { name: "古法命中" })).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });

  it("does not invent a line click when fact_paths do not map to a line", async () => {
    const user = userEvent.setup();
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            source_conditioned_patterns: [SOURCE_PATTERNS[1]],
          }),
        })}
      />,
    );

    const block = panel();
    await user.click(within(block).getByText("命中古法 1 条 · 可核验"));
    expect(within(block).getByText("先看世应")).toBeVisible();
    expect(within(block).queryByRole("button", { name: "先看世应" })).not.toBeInTheDocument();
    expect(glyphTable().querySelector("[data-focus]")).toBeNull();
  });
});

describe("/liuyao S3 M6 免费基础摘要", () => {
  function summary() {
    return screen.getByRole("region", { name: "基础摘要" });
  }

  it("restates on-screen hexagram, moving count, shi-ying and useful-spirit role", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: emptyFacts({
            shi_ying: { shi: 3, ying: 6 },
            useful_spirit_selection: usefulSpirit(),
          }),
        })}
      />,
    );

    const block = summary();
    expect(block).toHaveTextContent("本卦山泽损");
    expect(block).toHaveTextContent("变卦风泽中孚");
    expect(block).toHaveTextContent("动爻 2 爻");
    expect(block).toHaveTextContent("三爻世、上爻应");
    expect(block).toHaveTextContent("用神妻财");
    expect(block).not.toHaveTextContent("吉");
    expect(block).not.toHaveTextContent("凶");
    expect(block).not.toHaveTextContent(/GAP-LY/);
  });

  it("drops changed, moving, shi-ying and useful-spirit clauses when those facts are absent", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          changed_hexagram: null,
          lines: [
            { position: 1, value: 7, moving: false },
            { position: 2, value: 8, moving: false },
            { position: 3, value: 7, moving: false },
            { position: 4, value: 8, moving: false },
            { position: 5, value: 7, moving: false },
            { position: 6, value: 8, moving: false },
          ],
          core_facts: null,
        })}
      />,
    );

    const block = summary();
    expect(block).toHaveTextContent("本卦山泽损");
    expect(block).not.toHaveTextContent("变卦");
    expect(block).not.toHaveTextContent("动爻");
    expect(block).not.toHaveTextContent("世");
    expect(block).not.toHaveTextContent("用神");
  });

});