import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { LiuyaoLineTower } from "@/components/readings/liuyao-line-tower";
import { RuntimeChart } from "@/components/readings/runtime-chart";
import type {
  LiuyaoChartViewModel,
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

function usefulSpirit(): LiuyaoUsefulSpiritSelection {
  return {
    status: "evidence_bound",
    reason: "角色与强弱是古籍规则与盘面事实的对齐，不是结论",
    query_word_matching: false,
    source_dependency_id: "liuyao.relations.returning-and-useful-spirit-candidates",
    chain_candidates: { status: "candidate_only" },
    strength_evidence: {
      status: "candidate_only",
      by_relative: {},
      source_rules: [{ ...SOURCE_ZR_STRENGTH, role: "useful_spirit_month_order_strength_band" }],
      fact_status: "calculated_relation_not_verdict",
      hard_verdict: null,
      requires_school_adjudication: true,
      source_dependency_id: "liuyao.interpretation.useful-spirit-strength-evidence",
    },
    role_adjudication: {
      status: "adjudicated_question_role_set",
      decision_scope: "finance_useful_spirit_role_set",
      question_class: "finance",
      primary_relative: "妻财",
      supporting_relatives: ["子孙"],
      obstacle_attention_relatives: ["兄弟", "官鬼", "父母"],
      specific_line_selection: 4,
      specific_line_adjudication: {
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
      },
      hard_verdict: null,
      source_ref: SOURCE_HJC,
      unresolved_checks: ["月日旺衰与空破冲合"],
    },
    question_context: {
      question_class: "finance",
      classification_source: "explicit_structured_input",
    },
  };
}

function chart(overrides: Partial<LiuyaoChartViewModel> = {}): LiuyaoChartViewModel {
  return {
    schema_version: "liuyao-chart/v1",
    subject_ref: "liuyao:s4-fixture",
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

const OFFER = {
  name: "六爻一事深读",
  coverage: "当前这件已起之卦的用神与世应证据",
  priceText: "由服务端标价",
  refundBoundary: "未交付可退",
};

describe("六爻 S4 深读选择入口", () => {
  it("shows the no-offer S4 gate with 问事 copy and on-screen 用神/世应 quotes, without 命局 or prices", () => {
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

    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
    expect(document.querySelector('nav a[href="#liuyao-s4-deep"]')).toHaveTextContent("深读");
    expect(screen.getByText(/一事一问/)).toBeVisible();
    expect(screen.getByText(/已起之卦/)).toBeVisible();
    expect(screen.queryByText(/命局/)).not.toBeInTheDocument();
    expect(screen.getByRole("status", { name: "测试期未开放" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
    const deep = screen.getByRole("heading", { name: "深读" }).closest("section");
    expect(deep).toHaveTextContent("用神妻财");
    expect(deep).toHaveTextContent("三爻世、上爻应");
    expect(deep).not.toHaveTextContent("吉");
    expect(deep).not.toHaveTextContent("凶");
    expect(screen.queryByText(/¥|￥|\d+\s*元/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买|支付/ })).not.toBeInTheDocument();
    expect(screen.queryByText("reading_version_id")).not.toBeInTheDocument();
    expect(screen.queryByText("offer_id")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
  });

  it("does not quote useful-spirit or shi-ying samples when those blocks are not on screen", () => {
    render(<RuntimeChart viewModel={chart({ core_facts: null })} />);

    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
    const deep = screen.getByRole("heading", { name: "深读" }).closest("section");
    expect(deep).not.toHaveTextContent("用神妻财");
    expect(deep).not.toHaveTextContent("三爻世");
    expect(screen.queryByRole("region", { name: "用神证据" })).not.toBeInTheDocument();
  });

  it("uses the locked copy baseline when the deep entry is locked", () => {
    render(<LiuyaoLineTower view={chart()} s4Phase="locked" />);

    expect(screen.getByRole("status", { name: "已锁定" })).toHaveAttribute("data-state", "locked");
    expect(screen.queryByRole("status", { name: "测试期未开放" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买/ })).not.toBeInTheDocument();
  });

  it("renders a server-owned offer card without inventing checkout, and confirming only says 确认中", () => {
    const { rerender } = render(<LiuyaoLineTower view={chart()} offer={OFFER} />);

    expect(screen.getByText("六爻一事深读")).toBeVisible();
    expect(screen.getByText("当前这件已起之卦的用神与世应证据")).toBeVisible();
    expect(screen.getByText("由服务端标价")).toBeVisible();
    expect(screen.getByText("未交付可退")).toBeVisible();
    expect(screen.getByRole("link", { name: "登录后继续" })).toHaveAttribute("href", "/auth/login");
    expect(screen.queryByRole("status", { name: "测试期未开放" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买/ })).not.toBeInTheDocument();

    rerender(<LiuyaoLineTower view={chart()} offer={OFFER} s4Phase="confirming" />);

    expect(screen.getByRole("status", { name: "确认中" })).toBeVisible();
    expect(screen.queryByText("由服务端标价")).not.toBeInTheDocument();
    expect(screen.queryByText(/订单号/)).not.toBeInTheDocument();
  });

  it("shows Fake gateway as unavailable and never treats it as paid", () => {
    render(<LiuyaoLineTower view={chart()} offer={OFFER} s4Phase="gateway_unavailable" />);

    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
    expect(screen.getByRole("status", { name: "支付暂时不可用" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
    expect(screen.getByText(/Fake/)).toBeVisible();
    expect(screen.queryByText("由服务端标价")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买|支付/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/订单号/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "登录后继续" })).not.toBeInTheDocument();
  });
});
