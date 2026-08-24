import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { MeihuaS3Board } from "@/components/readings/meihua-chart";
import { RuntimeChart } from "@/components/readings/runtime-chart";
import type { MeihuaChartViewModel } from "@/view-models/registry";

afterEach(cleanup);

function chart(overrides: Partial<MeihuaChartViewModel> = {}): MeihuaChartViewModel {
  return {
    schema_version: "meihua-chart/v1",
    subject_ref: "meihua:fixture",
    question: "这件事后续如何",
    casting_method: "time",
    primary_hexagram: { name: "风雷益", upper_trigram: "巽", lower_trigram: "震" },
    mutual_hexagram: { name: "山地剥", upper_trigram: "艮", lower_trigram: "坤" },
    changed_hexagram: { name: "风泽中孚", upper_trigram: "巽", lower_trigram: "兑" },
    moving_lines: [2],
    body_use: {
      body: { position: "upper", trigram: "巽", element: "木" },
      use: { position: "lower", trigram: "震", element: "木" },
      relation: "比和",
      status: "calculated_relation_not_verdict",
    },
    core_facts: {
      body_relation_facts: [],
      seasonal_strength: {
        巽: {
          trigram: "巽",
          month_branch: "酉",
          season: "秋",
          state: "相",
          status: "calculated",
        },
        震: {
          trigram: "震",
          month_branch: "酉",
          season: "秋",
          state: "休",
          status: "calculated",
        },
      },
      interpretation_status: "source_adjudicated_relations",
      interpretive_candidates: {
        schema_version: "mingli-meihua-interpretive-candidates-v1",
        status: "source_adjudicated_relations",
        hard_verdict: null,
        verification_status: "verified",
        relation_candidates: [
          {
            candidate_id: "meihua.primary_use.upper.same_element",
            source_plate: "primary_use",
            position: "upper",
            relation: "比和",
            relation_key: "same_element",
            actor: { position: "upper", trigram: "巽", element: "木" },
            body: { position: "upper", trigram: "巽", element: "木" },
            seasonal_state: "旺",
            rule_id: "MR-04-02",
            status: "relation_adjudicated_not_event_verdict",
            hard_verdict: null,
            verification_status: "verified",
            source_pack: "divination/meihua-yishu",
            source_anchor: "references/books/divination/meihua-yishu/rules.md#MR-04-02",
            source_dependency_id: "meihua.classical-adjudication.body-use-candidates",
            relation_adjudication: {
              status: "adjudicated_relation_polarity",
              decision_scope: "meihua_body_use_relation",
              relation_key: "same_element",
              source_polarity: "harmonious",
              hard_verdict: null,
              event_verdict: null,
              source_refs: [
                {
                  pack: "divination/meihua-yishu",
                  rule_id: "MR-04-02",
                  source_anchor: "references/fulltext/divination/meihua-yishu/fulltext.md#L875",
                  verification_status: "verified",
                  binding_digest: "digest",
                },
              ],
              unresolved_checks: [],
            },
          },
        ],
        requires_classical_adjudication: false,
        requires_synthesis_adjudication: true,
        boundary: "关系极性已裁定，综合事件结论仍待裁决",
      },
    },
    ...overrides,
  };
}

describe("梅花 S4 深读选择入口", () => {
  it("restates on-screen facts in the free summary and omits missing clauses", () => {
    render(<RuntimeChart viewModel={chart()} />);

    const summary = screen.getByRole("region", { name: "基础摘要" });
    expect(summary).toHaveTextContent("本卦风雷益");
    expect(summary).toHaveTextContent("互卦山地剥");
    expect(summary).toHaveTextContent("变卦风泽中孚");
    expect(summary).toHaveTextContent("动爻：二爻");
    expect(summary).toHaveTextContent("体巽木、用震木，比和");
    expect(summary).toHaveTextContent("巽相、震休");
    expect(summary).not.toHaveTextContent("吉");
    expect(summary).not.toHaveTextContent("凶");
  });

  it("drops mutual, changed, moving-line and seasonal clauses when those fields are absent", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          mutual_hexagram: null,
          changed_hexagram: null,
          moving_lines: [],
          core_facts: null,
        })}
      />,
    );

    const summary = screen.getByRole("region", { name: "基础摘要" });
    expect(summary).toHaveTextContent("本卦风雷益");
    expect(summary).toHaveTextContent("体巽木、用震木，比和");
    expect(summary).not.toHaveTextContent("互卦");
    expect(summary).not.toHaveTextContent("变卦");
    expect(summary).not.toHaveTextContent("动爻");
    expect(summary).not.toHaveTextContent("巽相");
  });

  it("shows the no-offer S4 gate with 一事一问 copy and on-screen sample quotes, without prices", () => {
    render(<RuntimeChart viewModel={chart()} />);

    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
    expect(document.querySelector('nav a[href="#meihua-s4-deep"]')).toHaveTextContent("深读");
    expect(screen.getByText(/一事一问/)).toBeVisible();
    expect(screen.getByRole("status", { name: "测试期未开放" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
    const deep = screen.getByRole("heading", { name: "深读" }).closest("section");
    expect(deep).toHaveTextContent("比和");
    expect(deep).toHaveTextContent("本卦上卦 巽（木）→ 体 巽（木）");
    expect(screen.queryByText(/¥|￥|\d+\s*元/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买|支付/ })).not.toBeInTheDocument();
    expect(screen.queryByText("reading_version_id")).not.toBeInTheDocument();
    expect(screen.queryByText("offer_id")).not.toBeInTheDocument();
  });

  it("does not quote polarity samples when interpretive sections are hidden", () => {
    render(
      <RuntimeChart
        viewModel={chart()}
        capability={{
          capability_id: "meihua",
          label: "梅花易数",
          tier: "B",
          source_system: "divination",
          runtime_active_rule_count: 0,
          judgment_rule_count: 0,
          source_status: "available",
        }}
      />,
    );

    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "古籍极性" })).not.toBeInTheDocument();
    expect(screen.queryByText(/本卦上卦 巽（木）→ 体 巽（木）/)).not.toBeInTheDocument();
  });

  it("renders a server-owned offer card without inventing checkout, and confirming only says 确认中", () => {
    const { rerender } = render(
      <MeihuaS3Board
        view={chart()}
        showInterpretiveSections
        offer={{
          name: "梅花一事深读",
          coverage: "当前这件已起之卦的体用关系与极性证据",
          priceText: "由服务端标价",
          refundBoundary: "未交付可退",
        }}
      />,
    );

    expect(screen.getByText("梅花一事深读")).toBeVisible();
    expect(screen.getByText("当前这件已起之卦的体用关系与极性证据")).toBeVisible();
    expect(screen.getByText("由服务端标价")).toBeVisible();
    expect(screen.getByText("未交付可退")).toBeVisible();
    expect(screen.getByRole("link", { name: "登录后继续" })).toHaveAttribute("href", "/auth/login");
    expect(screen.queryByRole("status", { name: "测试期未开放" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买/ })).not.toBeInTheDocument();

    rerender(
      <MeihuaS3Board
        view={chart()}
        showInterpretiveSections
        offer={{
          name: "梅花一事深读",
          coverage: "当前这件已起之卦的体用关系与极性证据",
          priceText: "由服务端标价",
          refundBoundary: "未交付可退",
        }}
        s4Phase="confirming"
      />,
    );

    expect(screen.getByRole("status", { name: "确认中" })).toBeVisible();
    expect(screen.queryByText("由服务端标价")).not.toBeInTheDocument();
    expect(screen.queryByText(/订单号/)).not.toBeInTheDocument();
  });
});
