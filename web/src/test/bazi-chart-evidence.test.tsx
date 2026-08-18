import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { ReadingEvidence } from "@/lib/api/contracts";
import type { BaziChartView } from "@/lib/reading-display";
import type { BaziCoreFacts } from "@/view-models/registry";

import { BaziChart } from "@/components/readings/bazi-chart";

const candidates = {
  strength: {
    status: "evidence_only",
    hard_verdict: null,
    day_element: "fire",
    month_command_element: "wood",
    seasonal_state: "旺",
    seasonal_state_source_rule_id: "R-02-04",
    same_element_occurrences: 2,
    resource_element: "wood",
    resource_occurrences: 1,
    all_element_occurrences: [
      { element: "wood", value: 1 },
      { element: "fire", value: 2 },
    ],
    month_order_adjudication: {
      status: "adjudicated_month_order_state",
      decision_scope: "bazi_month_order_seasonal_state",
      day_master_element: "fire",
      month_command_element: "wood",
      seasonal_state: "旺",
      whole_chart_strength_verdict: null,
      useful_god_verdict: null,
      source_ref: {
        pack: "bazi/sanming-tonghui",
        rule_id: "R-02-04",
        source_anchor: "L10-L12",
        verification_status: "verified",
        binding_digest: "test",
      },
      unresolved_checks: [],
    },
    boundary: "全局身强身弱与唯一用神仍未裁定",
  },
  structure: {
    status: "candidate_only",
    hard_verdict: null,
    month_main_qi: "甲",
    month_main_qi_ten_god: "比肩",
    main_qi_visible: true,
    visible_positions: ["month"],
    boundary: "结构候选仍待裁定",
  },
  following_and_transformation: {
    status: "requires_classical_adjudication",
    hard_verdict: null,
    stem_combination_candidates: [],
    branch_formation_candidates: [],
    boundary: "合化与从格仍待经典裁决",
  },
  salience_signals: [],
  reasoning_tools: {
    unknown_tool: {
      output: {
        status: "candidate_only",
        custom_key: "raw-enum-value",
        custom_count: 7,
        nested_payload: { nested_key: "nested-raw-value" },
        raw_values: ["raw-one", "raw-two"],
      },
    },
  },
} as NonNullable<BaziCoreFacts["interpretive_candidates"]>;

const calendarNormalizationWithoutG3 = {
  status: "calculated",
  algorithm_version: "calendar-v53",
  time_basis: {
    policy: "longitude_mean_solar-v1",
    standard_meridian_degrees: 120,
    longitude_correction_seconds: 480,
    equation_of_time_seconds: -120,
    total_correction_seconds: 360,
    algorithm: {
      id: "equation-of-time-v1",
      version: "1",
      source: "Runtime",
      uncertainty_seconds: 2,
    },
    boundary: {
      distance_seconds: 120,
      correction_changes_hour_branch: false,
      within_uncertainty: false,
    },
  },
  true_solar_time: {
    status: "apparent_solar_applied",
    policy: "apparent_solar-v1",
    longitude_correction_seconds: 480,
    equation_of_time_seconds: -120,
    total_correction_seconds: 360,
  },
  calendar_convention: {
    id: "bazi-calendar-v1",
    version: "1",
    year_boundary: "立春",
    month_boundary: "节气",
    day_rollover: "子初",
    hour_basis: "true_solar",
    zi_hour_policy: "晚子时按当日",
  },
} as NonNullable<BaziCoreFacts["calendar_normalization"]>;

const calendarNormalization = {
  ...calendarNormalizationWithoutG3,
  effective_datetime: "2000-10-18T07:01:00+08:00",
  day_boundary: {
    correction_crossed_date: true,
    zi_policy_advanced_day_pillar: false,
  },
  changed_pillars: ["day", "hour"],
  solar_terms: {
    previous: {
      name: "寒露",
      index: 18,
      is_month_boundary_jie: true,
      datetime: "2000-10-08T07:38:00+08:00",
      instant_utc: "2000-10-07T23:38:00Z",
    },
    next: {
      name: "霜降",
      index: 19,
      is_month_boundary_jie: false,
      datetime: "2000-10-23T10:47:00+08:00",
      instant_utc: "2000-10-23T02:47:00Z",
    },
    month_switch_policy: "month-switch-at-jie-v1",
  },
} as unknown as NonNullable<BaziCoreFacts["calendar_normalization"]>;

const chart = {
  pillars: { year: "甲子", month: "乙丑", day: "丙寅", hour: "丁卯" },
  coreFacts: {
    day_master: { stem: "丙", element: "fire", polarity: "阳" },
    hidden_stems: [
      { position: "year", branch: "子", stems: ["癸"] },
      { position: "day", branch: "寅", stems: ["甲", "丙", "戊"] },
    ],
    ten_gods: {
      heavenly_stems: [
        { position: "year", layer: "heavenly_stem", stem: "甲", ten_god: "偏印" },
        { position: "day", layer: "heavenly_stem", stem: "丙", ten_god: "日主" },
      ],
      hidden_stems: [
        { position: "day", layer: "hidden_stem", stem: "甲", ten_god: "偏印" },
      ],
    },
    element_inventory: {
      visible_stem_branch_counts: [{ element: "fire", value: 2 }],
      hidden_stem_occurrence_counts: [{ element: "wood", value: 1 }],
      scope: "natal",
    },
    branch_relations: [
      { relation_type: "六合", positions: ["year", "day"], branches: ["子", "丑"] },
    ],
    month_command: {
      branch: "丑",
      label: "丑月",
      main_qi: "己",
      main_qi_element: "earth",
    },
    source_conditioned_patterns: [
      {
        rule_id: "R-TEST-1",
        local_rule_id: "bazi.test.one",
        title: "测试古法命中",
        source_pack: "bazi/test-book",
        source_anchor: "L10-L12",
        status: "predicate_matched_not_verdict",
        fact_paths: ["/day_master/stem"],
        predicate_audit: ["/day_master/stem:eq:丙", "/unknown/path:exists:()"],
        evidence_ref: "evidence:resolved",
      },
      {
        rule_id: "R-TEST-2",
        local_rule_id: "bazi.test.unresolved",
        title: "未解析引用不应显示",
        source_pack: "bazi/test-book",
        source_anchor: "L20-L21",
        status: "predicate_matched_not_verdict",
        fact_paths: ["/month_command/branch"],
        predicate_audit: ["/month_command/branch:eq:丑"],
        evidence_ref: "evidence:missing",
      },
    ],
    interpretive_candidates: candidates,
    calendar_normalization: calendarNormalization,
  } as unknown as BaziCoreFacts,
  timeLayers: [],
  dayMaster: "丙（火·阳）",
  monthCommand: "丑月",
  activeLuck: null,
  birthTime: "2000-01-01T00:00:00+08:00",
  gender: null,
  location: "北京",
  timeBasis: "longitude_mean_solar-v1",
  ziHour: "晚子时按当日",
  timezone: "Asia/Shanghai",
  targetDay: null,
  targetPeriod: null,
  calendarSummary: null,
  highlights: [],
  secondary: [],
} as BaziChartView;

const evidence: ReadingEvidence[] = [
  {
    ref: "evidence:resolved",
    evidence_ref: "evidence:resolved",
    rule_id: "R-TEST-1",
    source_title: "测试古籍",
    locator: "L10-L12",
    excerpt: "第一段逐字原文。",
    verification_status: "verified_exact",
    verbatim_excerpt: "第一段逐字原文。",
    verbatim_citations: [
      {
        source_title: "测试古籍",
        locator: "L10-L12",
        verbatim_excerpt: "第一段逐字原文。",
        verification_status: "verified_exact",
      },
      {
        source_title: "测试古籍",
        locator: "L20-L21",
        verbatim_excerpt: "第二段逐字原文。",
        verification_status: "verified_exact",
      },
    ],
    supports_fact_refs: [],
  },
];

const legacySummaryEvidence: ReadingEvidence[] = [
  {
    ref: "evidence:resolved",
    source_title: "测试古籍",
    locator: "rules.md#R-TEST-1",
    excerpt: "这是规则摘要，不是古籍逐字原文。",
    supports_fact_refs: [],
  },
];

describe("BaziChart evidence-first slice", () => {
  it("renders every verified exact citation without rewriting it", async () => {
    const user = userEvent.setup();
    render(<BaziChart chart={chart} evidence={evidence} />);

    const summary = screen.getByText("命中古法 1 条 · 可核验");
    const drawer = summary.closest("details");
    expect(drawer).not.toHaveAttribute("open");
    expect(screen.queryByText("未解析引用不应显示")).not.toBeInTheDocument();

    await user.click(summary);

    expect(drawer).toHaveAttribute("open");
    expect(screen.getByText("第一段逐字原文。")).toBeVisible();
    expect(screen.getByText("第二段逐字原文。")).toBeVisible();
    expect(screen.getByText("原文")).toBeVisible();
    expect(screen.getByText("可回溯出处")).toBeVisible();
    expect(screen.getAllByText("测试古籍")).toHaveLength(2);
    expect(screen.getAllByText(/L10-L12|L20-L21/)).toHaveLength(2);
    expect(screen.getByText("日主天干为丙")).toBeVisible();
    expect(screen.getByText("/unknown/path:exists:()")).toBeVisible();
    expect(screen.queryByText("/day_master/stem")).not.toBeInTheDocument();
  });

  it("does not expose a legacy rule summary as an ancient citation", () => {
    render(<BaziChart chart={chart} evidence={legacySummaryEvidence} />);

    expect(screen.queryByText(/命中古法|规则条件命中/)).not.toBeInTheDocument();
    expect(
      screen.queryByText("这是规则摘要，不是古籍逐字原文。"),
    ).not.toBeInTheDocument();
  });

  it("projects only public candidate facts, boundaries, and pending language", () => {
    render(<BaziChart chart={chart} evidence={[]} />);

    expect(screen.queryByText(/偏强|偏弱|总分|吉|凶/)).not.toBeInTheDocument();
    expect(screen.queryByText("evidence_only")).not.toBeInTheDocument();
    expect(screen.queryByText("candidate_only")).not.toBeInTheDocument();
    expect(screen.queryByText("unknown_tool")).not.toBeInTheDocument();
    expect(screen.queryByText("custom_key")).not.toBeInTheDocument();
    expect(screen.queryByText("raw-enum-value")).not.toBeInTheDocument();
    expect(screen.queryByText("nested_key")).not.toBeInTheDocument();
    expect(screen.queryByText("nested-raw-value")).not.toBeInTheDocument();
    expect(screen.queryByText("raw-one")).not.toBeInTheDocument();
    expect(screen.queryByText("raw-two")).not.toBeInTheDocument();
    expect(screen.queryByText("custom_count")).not.toBeInTheDocument();
    expect(screen.queryByText("7")).not.toBeInTheDocument();
    expect(screen.queryByText("R-02-04")).not.toBeInTheDocument();
    expect(screen.getByText("候选事实")).toBeVisible();
    expect(screen.getByText("支持性事实")).toBeVisible();
    expect(screen.getByText("中性盘面事实")).toBeVisible();
    expect(screen.getByText(/全局身强身弱与唯一用神仍未裁定/)).toBeVisible();
    expect(screen.getByText("全局强弱证据（未裁定）")).toBeVisible();
    expect(screen.getByText("证据边界")).toBeVisible();
    expect(
      screen.getByText(
        /结构候选：月令主气 甲 · 比肩；主气可见：是；可见位置：月柱；结构候选仍待裁定；候选，待裁定/,
      ),
    ).toBeVisible();
    expect(screen.queryByText(/结构候选：月令主气 木/)).not.toBeInTheDocument();
    expect(screen.getByText(/合化与从格.*待.*裁定/)).toBeVisible();
  });

  it("shows the exact G3 time facts returned by Runtime", () => {
    render(<BaziChart chart={chart} evidence={[]} />);

    expect(screen.getByText("longitude_mean_solar-v1")).toBeVisible();
    expect(screen.getByText("120°")).toBeVisible();
    expect(screen.getByText("+480 秒")).toBeVisible();
    expect(screen.getByText("-120 秒")).toBeVisible();
    expect(screen.getByText("+360 秒")).toBeVisible();
    expect(screen.getByText("未跨时辰边界")).toBeVisible();
    expect(screen.getByText("晚子时按当日")).toBeVisible();
    expect(screen.queryByText("Runtime 未返回，页面不自行推算")).not.toBeInTheDocument();
    expect(screen.getByText("有效时刻").parentElement).toHaveTextContent(
      "2000-10-18T07:01:00+08:00",
    );
    expect(screen.getByText("日界状态").parentElement).toHaveTextContent(
      "修正跨越日界",
    );
    expect(screen.getByText("变柱").parentElement).toHaveTextContent(
      "该修正改变了日柱、时柱",
    );
    expect(screen.getByText("前一节气").parentElement).toHaveTextContent(
      "寒露 · 2000-10-08T07:38:00+08:00 · 月界节",
    );
    expect(screen.getByText("后一节气").parentElement).toHaveTextContent(
      "霜降 · 2000-10-23T10:47:00+08:00",
    );
    expect(screen.getByText("换月口径").parentElement).toHaveTextContent(
      "month-switch-at-jie-v1",
    );
  });

  it("does not derive or placeholder G3 facts when Runtime omits them", () => {
    const chartWithoutG3 = {
      ...chart,
      coreFacts: {
        ...chart.coreFacts,
        calendar_normalization: calendarNormalizationWithoutG3,
      },
    } as BaziChartView;

    render(<BaziChart chart={chartWithoutG3} evidence={[]} />);

    expect(screen.getByText("longitude_mean_solar-v1")).toBeVisible();
    expect(screen.queryByText("有效时刻")).not.toBeInTheDocument();
    expect(screen.queryByText("日界状态")).not.toBeInTheDocument();
    expect(screen.queryByText("变柱")).not.toBeInTheDocument();
    expect(screen.queryByText("前一节气")).not.toBeInTheDocument();
    expect(screen.queryByText("换月口径")).not.toBeInTheDocument();
    expect(screen.queryByText(/Runtime 未返回|页面不自行推算/)).not.toBeInTheDocument();
  });

  it("uses transient hover/focus facts until a locked pillar takes priority", async () => {
    const user = userEvent.setup();
    render(<BaziChart chart={chart} evidence={[]} />);
    const pillarGroup = screen.getByRole("group", { name: "四柱" });
    const buttons = within(pillarGroup).getAllByRole("button");
    const highlightedValues = () =>
      Array.from(
        document.querySelectorAll<HTMLElement>('[data-fact-highlight="true"]'),
      ).map((element) => element.textContent);

    await act(async () => {
      buttons[0].focus();
    });
    expect(highlightedValues()).toContain("甲");
    expect(highlightedValues()).toContain("子");

    await user.click(buttons[0]);
    await act(async () => {
      buttons[0].focus();
    });
    await user.keyboard("{ArrowRight}");
    expect(buttons[1]).toHaveFocus();
    expect(highlightedValues()).toContain("甲");
    expect(highlightedValues()).not.toContain("乙");

    await user.keyboard("{Escape}");
    expect(buttons[0]).toHaveAttribute("aria-pressed", "false");

    await act(async () => {
      buttons[0].blur();
    });
    expect(highlightedValues()).toHaveLength(0);
    await user.hover(buttons[2]);
    expect(highlightedValues()).toContain("丙");
    await user.unhover(buttons[2]);
    expect(highlightedValues()).toHaveLength(0);
  });

  it("uses roving tabindex, supports navigation, and clears the lock with Escape", async () => {
    const user = userEvent.setup();
    render(<BaziChart chart={chart} evidence={[]} />);
    const pillarGroup = screen.getByRole("group", { name: "四柱" });
    const buttons = within(pillarGroup).getAllByRole("button");

    expect(buttons[0]).toHaveAttribute("tabindex", "0");
    expect(buttons[1]).toHaveAttribute("tabindex", "-1");

    await user.click(buttons[0]);
    expect(buttons[0]).toHaveAttribute("aria-pressed", "true");
    await user.click(buttons[0]);
    expect(buttons[0]).toHaveAttribute("aria-pressed", "false");
    await user.click(buttons[0]);
    expect(buttons[0]).toHaveAttribute("aria-pressed", "true");
    await act(async () => {
      buttons[0].focus();
    });
    await user.keyboard("{ArrowRight}");
    expect(buttons[1]).toHaveFocus();
    expect(buttons[1]).toHaveAttribute("tabindex", "0");
    await user.keyboard("{End}");
    expect(buttons[3]).toHaveFocus();
    await user.keyboard("{Home}");
    expect(buttons[0]).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(buttons[0]).toHaveAttribute("aria-pressed", "false");
  });

  it("does not use pillar hover transforms and keeps long facts inside the board", async () => {
    const { readFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const css = readFileSync(
      join(process.cwd(), "src/components/readings/bazi-chart.module.css"),
      "utf8",
    );

    expect(css).not.toMatch(/\.pillarCard:hover[\s\S]{0,260}transform\s*:/);
    expect(css).not.toMatch(/\.pillarCard:active[\s\S]{0,260}transform\s*:/);
    expect(css).toMatch(/\.board\s*\{[\s\S]*?min-width:\s*0/);
    expect(css).toMatch(/overflow-wrap:\s*anywhere/);
  });
});
