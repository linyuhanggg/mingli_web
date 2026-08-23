import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MeihuaS3Board } from "@/components/readings/meihua-chart";
import { RuntimeChart } from "@/components/readings/runtime-chart";
import { resolveMeihuaS5Anchors } from "@/components/readings/meihua-s5-anchors";
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

describe("梅花 S5 报告态锚点回跳 S3", () => {
  it("maps candidate and triad fact refs onto existing S3 targets", () => {
    const view = chart();
    expect(
      resolveMeihuaS5Anchors(
        ["fact:meihua:fixture/chart_facts/output/interpretive_candidates/relation_candidates/meihua.primary_use.upper.same_element"],
        view,
      ),
    ).toEqual([
      {
        unit: "primary-upper",
        slot: "primary",
        polarityId: "meihua.primary_use.upper.same_element",
        label: "极性证据",
      },
    ]);
    expect(
      resolveMeihuaS5Anchors(["fact:meihua:fixture/chart_facts/output/mutual_hexagram"], view),
    ).toEqual([
      { unit: "mutual-upper", slot: "mutual", polarityId: null, label: "互卦上卦" },
    ]);
    expect(resolveMeihuaS5Anchors(["fact:unrelated/other"], view)).toEqual([]);
  });

  it("does not invent a report when no deliverable claims are supplied", () => {
    render(<RuntimeChart viewModel={chart()} />);

    expect(screen.queryByRole("heading", { name: "报告" })).not.toBeInTheDocument();
    expect(document.querySelector('nav a[href="#meihua-s5-report"]')).toBeNull();
    expect(screen.queryByRole("button", { name: "极性证据" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "本卦上卦" })).not.toBeInTheDocument();
  });

  it("jumps a polarity claim back to the S3 triad unit and polarity row", async () => {
    const user = userEvent.setup();
    const scrollIntoView = vi.fn();
    HTMLElement.prototype.scrollIntoView = scrollIntoView;

    render(
      <MeihuaS3Board
        view={chart()}
        showInterpretiveSections
        reportClaims={[
          {
            claim_id: "claim-polarity-1",
            text: "本卦上卦巽与体同为木。",
            fact_refs: [
              "fact:meihua:fixture/chart_facts/output/interpretive_candidates/relation_candidates/meihua.primary_use.upper.same_element",
            ],
          },
        ]}
      />,
    );

    expect(screen.getByText("本卦上卦巽与体同为木。")).toBeVisible();
    expect(screen.queryByText("meihua.primary_use.upper.same_element")).not.toBeInTheDocument();
    expect(screen.queryByText(/fact:meihua/)).not.toBeInTheDocument();
    expect(document.querySelector('nav a[href="#meihua-s5-report"]')).toHaveTextContent("报告");

    await user.click(screen.getByRole("button", { name: "极性证据" }));

    expect(document.getElementById("meihua-unit-primary-upper")).toHaveAttribute("data-active", "true");
    expect(document.getElementById("meihua-polarity-meihua.primary_use.upper.same_element")).toHaveAttribute(
      "data-active",
      "true",
    );
    expect(scrollIntoView).toHaveBeenCalled();
  });

  it("jumps a triad claim back to the matching hexagram unit", async () => {
    const user = userEvent.setup();
    HTMLElement.prototype.scrollIntoView = vi.fn();

    render(
      <RuntimeChart
        viewModel={chart()}
        reportClaims={[
          {
            claim_id: "claim-triad-1",
            text: "变卦为风泽中孚。",
            fact_refs: ["fact:meihua:fixture/chart_facts/output/changed_hexagram"],
          },
        ]}
      />,
    );

    await user.click(screen.getByRole("button", { name: "变卦上卦" }));
    expect(document.getElementById("meihua-unit-changed-upper")).toHaveAttribute("data-active", "true");
  });
});
