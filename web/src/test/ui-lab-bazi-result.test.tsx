import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { UiLab } from "@/components/ui-lab/ui-lab";
import { UI_LAB_FIXTURES } from "@/fixtures/ui-lab";

afterEach(cleanup);

describe("UI Lab bazi result evidence fixture", () => {
  it("registers a versioned complete chart fixture with G1 and G3 facts", () => {
    const fixture = UI_LAB_FIXTURES.find((item) => item.id === "bazi-result-evidence");

    expect(fixture).toMatchObject({
      previewKind: "bazi-result",
      routePattern: "/_ui-lab/bazi-result",
      schemaVersion: "bazi-chart/v1",
      schemaSource: "view-model-registry",
    });

    if (!fixture || fixture.previewKind !== "bazi-result") {
      throw new Error("bazi-result-evidence fixture is not registered");
    }

    expect(fixture.viewModel.schema_version).toBe("bazi-chart/v1");
    expect(fixture.viewModel.pillars).toHaveLength(4);
    expect(fixture.viewModel.core_facts?.calendar_normalization).toMatchObject({
      effective_datetime: expect.any(String),
      day_boundary: {
        correction_crossed_date: expect.any(Boolean),
        zi_policy_advanced_day_pillar: expect.any(Boolean),
      },
      changed_pillars: expect.any(Array),
      solar_terms: {
        previous: expect.any(Object),
        next: expect.any(Object),
        month_switch_policy: expect.any(String),
      },
    });
    expect(fixture.evidence).toHaveLength(1);
    expect(fixture.evidence[0]).toMatchObject({
      verification_status: "verified_exact",
      evidence_ref: fixture.evidence[0].ref,
      verbatim_citations: [
        { verification_status: "verified_exact" },
        { verification_status: "verified_exact" },
      ],
    });
  });

  it("selects the fixture and mounts the production BaziChart with exact evidence", async () => {
    const user = userEvent.setup();
    render(<UiLab demoLabel="UI 演示数据" />);

    await user.selectOptions(
      screen.getByRole("combobox", { name: "页面与场景" }),
      "bazi-result-evidence",
    );
    await user.selectOptions(screen.getByRole("combobox", { name: "状态" }), "free-summary");

    const preview = within(screen.getByTestId("ui-lab-preview"));
    expect(preview.getByRole("heading", { name: "预览：八字结果页（G1/G3 可核验证据切片）" })).toBeVisible();
    expect(preview.getByRole("heading", { name: "八字结果页验收切片" })).toBeVisible();
    expect(preview.getByText("有效时刻")).toBeVisible();
    expect(preview.getByText("该修正改变了时柱")).toBeVisible();
    expect(preview.getByText(/芒种/)).toBeVisible();

    const evidenceSummary = preview.getByText("命中古法 1 条 · 可核验");
    await user.click(evidenceSummary);

    expect(preview.getByText("木得春令，气势自舒。原文第一条。")).toBeVisible();
    expect(preview.getByText("丙火得木相生，先看月令而后论全局。原文第二条。")).toBeVisible();
    expect(preview.getAllByText("《三命通会》")).toHaveLength(2);
    expect(preview.getByText("卷二·L12-L15")).toBeVisible();
    expect(preview.getByText("卷二·L31-L34")).toBeVisible();
  });
});
