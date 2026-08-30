import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { RuntimeChart } from "@/components/readings/runtime-chart";
import type { CapabilityProjection } from "@/lib/api/contracts";
import type { MeihuaChartViewModel } from "@/view-models/registry";

const CAPABILITY_A: CapabilityProjection = {
  capability_id: "meihua",
  label: "梅花易数",
  tier: "A",
  source_system: "meihua",
  runtime_active_rule_count: 3,
  judgment_rule_count: 2,
  source_status: "available",
};

const CAPABILITY_B: CapabilityProjection = {
  ...CAPABILITY_A,
  tier: "B",
};

function meihuaView(
  castingMethod: MeihuaChartViewModel["casting_method"] = "time",
  overrides: Partial<MeihuaChartViewModel> = {},
): MeihuaChartViewModel {
  return {
    schema_version: "meihua-chart/v1",
    subject_ref: "meihua:fixture",
    question: "这件事如何推进？",
    casting_method: castingMethod,
    primary_hexagram: {
      name: "风雷益",
      upper_trigram: "巽",
      lower_trigram: "震",
    },
    mutual_hexagram: {
      name: "山地剥",
      upper_trigram: "艮",
      lower_trigram: "坤",
    },
    changed_hexagram: {
      name: "风泽中孚",
      upper_trigram: "巽",
      lower_trigram: "兑",
    },
    moving_lines: [2],
    body_use: {
      body: { position: "upper", trigram: "巽", element: "木" },
      use: { position: "lower", trigram: "震", element: "木" },
      relation: "比和",
      status: "calculated_relation_not_verdict",
    },
    core_facts: {
      body_relation_facts: [
        {
          position: "upper",
          trigram: "巽",
          element: "木",
          relation: "比和",
          status: "calculated_relation_not_verdict",
        },
      ],
      seasonal_strength: {
        autumn: {
          trigram: "兑",
          month_branch: "酉",
          season: "秋",
          state: "旺",
          status: "calculated_strength_not_verdict",
        },
      },
      interpretive_candidates: {
        schema_version: "mingli-meihua-interpretive-candidates-v1",
        status: "source_adjudicated_relations",
        hard_verdict: null,
        verification_status: "verified",
        relation_candidates: [
          {
            candidate_id: "primary-use",
            source_plate: "primary_use",
            position: "lower",
            relation: "比和",
            relation_key: "same_element",
            actor: { position: "lower", trigram: "震", element: "木" },
            body: { position: "upper", trigram: "巽", element: "木" },
            seasonal_state: "旺",
            rule_id: "MH-R01",
            status: "relation_adjudicated_not_event_verdict",
            hard_verdict: null,
            verification_status: "verified",
            source_pack: "meihua-yishu",
            source_anchor: "rules.md#MH-R01",
            source_dependency_id: "meihua.body-use",
            relation_adjudication: {
              status: "adjudicated_relation_polarity",
              decision_scope: "meihua_body_use_relation",
              relation_key: "same_element",
              source_polarity: "harmonious",
              hard_verdict: null,
              event_verdict: null,
              source_refs: [],
              unresolved_checks: ["具体问题", "事件应期"],
            },
          },
        ],
        requires_classical_adjudication: false,
        requires_synthesis_adjudication: true,
        boundary: "关系已核验，未形成事件断语。",
      },
      interpretation_status: "facts_only",
    },
    public_labels: [
      { key: "upper", label: "上卦" },
      { key: "autumn", label: "秋令" },
    ],
    ...overrides,
  };
}

describe("梅花易数 S3 玄序工作台", () => {
  it("keeps the narrative 本互变 sequence, body-use facts and dual-coded elements", () => {
    render(<RuntimeChart capability={CAPABILITY_A} viewModel={meihuaView()} />);

    const workspace = screen.getByRole("region", { name: "梅花易数排盘工作台" });
    const plates = within(workspace).getAllByRole("listitem");
    expect(plates).toHaveLength(3);
    expect(plates.map((plate) => plate.textContent)).toEqual([
      expect.stringContaining("本卦风雷益"),
      expect.stringContaining("互卦山地剥"),
      expect.stringContaining("变卦风泽中孚"),
    ]);
    expect(within(workspace).getByText("第2爻")).toBeVisible();
    expect(within(workspace).getAllByText("已计算关系")).toHaveLength(2);
    expect(within(workspace).getByText("本卦·用")).toBeVisible();
    expect(within(workspace).queryByText("primary_use")).not.toBeInTheDocument();
    expect(workspace.querySelectorAll('[data-element="wood"]')).not.toHaveLength(0);
    expect(within(workspace).getByText(/综合成败与应期仍待正式合成裁决/)).toBeVisible();
    expect((workspace.textContent?.match(/未裁定/g) ?? []).length).toBeLessThanOrEqual(1);
  });

  it("moves a single tab stop through 本互变 with arrow, Home and End keys", async () => {
    const user = userEvent.setup();
    render(<RuntimeChart capability={CAPABILITY_B} viewModel={meihuaView()} />);

    const workspace = screen.getByRole("region", { name: "梅花易数排盘工作台" });
    const plates = within(workspace).getAllByRole("listitem");
    expect(plates[0]).toHaveAttribute("tabindex", "0");
    expect(plates[1]).toHaveAttribute("tabindex", "-1");
    plates[0].focus();
    await user.keyboard("{ArrowRight}");
    expect(plates[1]).toHaveFocus();
    await user.keyboard("{End}");
    expect(plates[2]).toHaveFocus();
    await user.keyboard("{Home}");
    expect(plates[0]).toHaveFocus();
  });

  it("does not leak an unmapped internal status key", () => {
    const view = meihuaView();
    render(
      <RuntimeChart
        capability={CAPABILITY_B}
        viewModel={{
          ...view,
          public_labels: [],
          body_use: { ...view.body_use, status: "unexpected_internal_status" },
        }}
      />,
    );

    expect(screen.queryByText("unexpected_internal_status")).not.toBeInTheDocument();
    expect(screen.getByText("服务端未返回公开名称")).toBeVisible();
    expect(screen.queryByText("upper")).not.toBeInTheDocument();
  });

  it.each([
    ["time", "按时间起卦"],
    ["supplied_number", "按数字起卦"],
    ["sound_count", "按声数起卦"],
    ["observation", "观物起卦"],
    ["supplied_hexagram", "已知卦象起卦"],
  ] as const)("preserves the %s casting method without guessing", (method, label) => {
    render(<RuntimeChart capability={CAPABILITY_B} viewModel={meihuaView(method)} />);
    expect(screen.getByText(label)).toBeVisible();
  });

  it("keeps source-adjudicated candidates on tier A and hides them on tier B", () => {
    const { rerender } = render(
      <RuntimeChart capability={CAPABILITY_A} viewModel={meihuaView()} />,
    );
    expect(screen.getByRole("table", { name: /体用关系来源裁定/ })).toBeVisible();

    rerender(<RuntimeChart capability={CAPABILITY_B} viewModel={meihuaView()} />);
    expect(screen.queryByRole("table", { name: /体用关系来源裁定/ })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "梅花易数排盘工作台" })).toBeVisible();
  });

  it("fails closed for absent optional hexagram and fact layers", () => {
    render(
      <RuntimeChart
        capability={CAPABILITY_B}
        viewModel={meihuaView("observation", {
          mutual_hexagram: null,
          changed_hexagram: null,
          core_facts: null,
        })}
      />,
    );

    expect(screen.getAllByText("服务端未返回这一卦层，不补造卦象。")).toHaveLength(2);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByText("观物起卦")).toBeVisible();
  });
});
