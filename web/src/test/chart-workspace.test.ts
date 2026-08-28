import { describe, expect, it } from "vitest";

import {
  baziWorkspaceFactsFromChart,
  buildBaziWorkspaceView,
  parseTimeLayerEntitlement,
  resolveBaziFocusDetail,
  type TimeLayerEntitlement,
} from "@/lib/chart-workspace";
import type { BaziChartView } from "@/lib/reading-display";

const FOUR_PILLARS = {
  year: "甲子",
  month: "丙寅",
  day: "戊午",
  hour: "丁卯",
};

const GRANTED_ENTITLEMENT: TimeLayerEntitlement = {
  schemaVersion: "time-layer-entitlement/v1",
  capabilityId: "bazi",
  resolution: "granted",
  freeBoundaryLayerId: "year",
  paidLayerIds: ["month", "day", "hour"],
  freeYearSet: [2026],
  layers: [
    { layerId: "life", tier: "free", access: "readable", upgradeCta: null },
    { layerId: "luck_cycles", tier: "free", access: "readable", upgradeCta: null },
    { layerId: "year", tier: "free", access: "readable", upgradeCta: null },
    { layerId: "month", tier: "paid", access: "readable", upgradeCta: null },
    { layerId: "day", tier: "paid", access: "readable", upgradeCta: null },
    { layerId: "hour", tier: "paid", access: "unavailable", upgradeCta: null },
  ],
};

describe("buildBaziWorkspaceView", () => {
  it("returns an honest empty workspace when no public facts exist", () => {
    const view = buildBaziWorkspaceView({});
    expect(view.title).toBe("八字命盘");
    expect(view.cells).toEqual([]);
    expect(view.highlights).toEqual([]);
    expect(view.basis).toEqual([]);
    expect(view.layers.find((layer) => layer.id === "natal")?.status).toBe(
      "empty",
    );
    expect(view.layers.find((layer) => layer.id === "decadal")?.status).toBe(
      "locked-unavailable",
    );
    expect(view.layers.find((layer) => layer.id === "yearly")?.status).toBe(
      "locked-unavailable",
    );
    expect(view.layers.find((layer) => layer.id === "monthly")?.status).toBe(
      "locked-unavailable",
    );
    expect(view.layers.find((layer) => layer.id === "daily")?.status).toBe(
      "locked-unavailable",
    );
    expect(view.layers.find((layer) => layer.id === "hourly")?.status).toBe(
      "locked-unavailable",
    );
  });

  it("maps bazi pillars into focusable cells with stable ids", () => {
    const view = buildBaziWorkspaceView({ pillars: FOUR_PILLARS });
    expect(view.cells.map((cell) => cell.id)).toEqual([
      "year",
      "month",
      "day",
      "hour",
    ]);
    expect(view.cells.map((cell) => cell.label)).toEqual([
      "年柱",
      "月柱",
      "日柱",
      "时柱",
    ]);
    expect(view.cells.map((cell) => cell.value)).toEqual([
      "甲子",
      "丙寅",
      "戊午",
      "丁卯",
    ]);
    expect(view.cells.every((cell) => cell.kind === "pillar")).toBe(true);
    expect(view.layers.find((layer) => layer.id === "natal")?.status).toBe(
      "ready",
    );
  });

  it("marks missing layers unavailable instead of inventing them", () => {
    const view = buildBaziWorkspaceView({
      pillars: { year: "甲子", month: "丙寅", day: "戊午", hour: null },
      activeLuck: null,
      highlights: [],
    });
    expect(view.layers.find((layer) => layer.id === "decadal")?.status).toBe(
      "locked-unavailable",
    );
    expect(view.layers.find((layer) => layer.id === "yearly")?.status).toBe(
      "locked-unavailable",
    );
    expect(view.layers.find((layer) => layer.id === "monthly")?.status).toBe(
      "locked-unavailable",
    );
    expect(view.layers.find((layer) => layer.id === "daily")?.status).toBe(
      "locked-unavailable",
    );
    expect(view.layers.find((layer) => layer.id === "hourly")?.status).toBe(
      "locked-unavailable",
    );
    expect(view.cells.find((cell) => cell.id === "hour")?.value).toBeNull();
    expect(view.cells.find((cell) => cell.id === "hour")?.badges).toContain(
      "时辰未知",
    );
  });

  it("marks the decadal layer ready only when active luck is provided", () => {
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      activeLuck: "丙午大运",
    });
    expect(view.layers.find((layer) => layer.id === "decadal")?.status).toBe(
      "ready",
    );
    expect(view.layers.find((layer) => layer.id === "decadal")?.summary).toContain(
      "丙午大运",
    );
  });

  it("keeps free layers readable but fail-closes paid facts without explicit entitlement", () => {
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      decadalReady: true,
      decadalSummary: "状态：not_calculated_missing_gender",
      yearlyReady: true,
      yearlySummary: "2026 丙午（2 个节气分段）",
      monthlyReady: true,
      monthlySummary: "2026-08（2 个节气分段）",
      dailyReady: true,
      dailySummary: "2026-08-15（1 个日界分段）",
    });
    expect(view.layers.map((layer) => layer.status)).toEqual([
      "ready",
      "ready",
      "ready",
      "fail-closed-unknown",
      "fail-closed-unknown",
      "locked-unavailable",
    ]);
    expect(view.layers.find((layer) => layer.id === "decadal")?.summary).toContain(
      "not_calculated_missing_gender",
    );
    expect(view.layers.find((layer) => layer.id === "daily")?.summary).toBe(
      "权益状态未确认",
    );
  });

  it("reveals paid facts only when the backend entitlement grants the same layer", () => {
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      decadalReady: true,
      yearlyReady: true,
      monthlyReady: true,
      monthlySummary: "2026-08（2 个节气分段）",
      dailyReady: true,
      dailySummary: "2026-08-15（1 个日界分段）",
      entitlement: GRANTED_ENTITLEMENT,
    });

    expect(view.layers.map((layer) => layer.status)).toEqual([
      "ready",
      "ready",
      "ready",
      "ready",
      "ready",
      "locked-unavailable",
    ]);
    expect(view.layers.find((layer) => layer.id === "daily")?.summary).toContain(
      "2026-08-15",
    );
  });

  it("never lets denied, guest, or failed entitlement lock the free boundary", () => {
    for (const resolution of ["denied", "unauthenticated", "request_failed"] as const) {
      const entitlement: TimeLayerEntitlement = {
        ...GRANTED_ENTITLEMENT,
        resolution,
        layers: GRANTED_ENTITLEMENT.layers.map((layer) => (
          layer.tier === "paid"
            ? {
                ...layer,
                access: resolution === "denied" ? "locked_paywall" : "fail_closed_unknown",
                upgradeCta: layer.layerId === "hour" ? null : "professional_info",
              }
            : layer
        )),
      };
      const view = buildBaziWorkspaceView({
        pillars: FOUR_PILLARS,
        decadalReady: true,
        yearlyReady: true,
        monthlyReady: true,
        entitlement,
      });
      expect(view.layers.slice(0, 3).map((layer) => layer.status)).toEqual([
        "ready",
        "ready",
        "ready",
      ]);
      expect(view.layers.find((layer) => layer.id === "monthly")?.status).toBe(
        resolution === "denied" ? "locked-paywall" : "fail-closed-unknown",
      );
    }
  });

  it("localizes the server luck status before it reaches the tabs", () => {
    const chart = {
      pillars: FOUR_PILLARS,
      coreFacts: {
        luck_cycles: { status: "calculated" },
      },
      highlights: [],
    } as unknown as BaziChartView;

    const facts = baziWorkspaceFactsFromChart(chart);
    expect(facts.decadalSummary).toBe("状态：已计算");
    expect(facts.decadalSummary).not.toContain("calculated");
  });

  it("builds the basis only from provided public facts", () => {
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      birthTime: "1994-04-30T05:55:00+08:00",
      timezone: "Asia/Shanghai",
      timeBasis: "民用时",
      ziHour: "按午夜换日",
      calendarSummary: "sxtwl 2.0.7",
    });
    expect(view.basis?.map((row) => row.label)).toEqual([
      "出生时间",
      "时区",
      "时间口径",
      "子时策略",
      "历法口径",
    ]);
    expect(view.basis?.find((row) => row.label === "时区")?.text).toBe(
      "Asia/Shanghai",
    );
  });

  it("never fabricates a board when no pillars are present", () => {
    const view = buildBaziWorkspaceView({
      pillars: { year: "", month: "", day: "", hour: "" },
      timeBasis: "民用时",
    });
    expect(view.layers.find((layer) => layer.id === "natal")?.status).toBe(
      "empty",
    );
    expect(view.cells).toEqual([]);
    expect(view.basis?.map((row) => row.label)).toEqual(["时间口径"]);
  });

  it("keeps the view model free of any algorithm vocabulary", () => {
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      activeLuck: "丙午大运",
      highlights: [{ label: "日主强", text: "服务端已确认" }],
    });
    expect(JSON.stringify(view)).not.toMatch(
      /iztro|lunar-javascript|ziwei-doushu|generateChart|astro\.bySolar/,
    );
    expect(view.highlights[0]).toEqual({
      id: "highlight-0",
      title: "日主强",
      body: "服务端已确认",
      tone: "neutral",
    });
  });
});

describe("parseTimeLayerEntitlement", () => {
  it("accepts only the explicit bazi v1 sibling contract", () => {
    expect(parseTimeLayerEntitlement({
      schema_version: "time-layer-entitlement/v1",
      capability_id: "bazi",
      resolution: "granted",
      free_boundary_layer_id: "year",
      paid_layer_ids: ["month", "day", "hour"],
      free_year_set: [2026],
      capability: { time_layers: [] },
      layers: GRANTED_ENTITLEMENT.layers.map((layer) => ({
        layer_id: layer.layerId,
        tier: layer.tier,
        access: layer.access,
        upgrade_cta: layer.upgradeCta,
      })),
    })).toEqual(GRANTED_ENTITLEMENT);
  });

  it("rejects missing, parallel-version, and contradictory paid grants", () => {
    expect(parseTimeLayerEntitlement(undefined)).toBeNull();
    expect(parseTimeLayerEntitlement({ schema_version: "time-layer-entitlement/v2" })).toBeNull();
    expect(parseTimeLayerEntitlement({
      schema_version: "time-layer-entitlement/v1",
      capability_id: "bazi",
      resolution: "denied",
      free_boundary_layer_id: "year",
      paid_layer_ids: ["month", "day", "hour"],
      free_year_set: [],
      capability: { time_layers: [] },
      layers: GRANTED_ENTITLEMENT.layers,
    })).toBeNull();
  });
});

describe("resolveBaziFocusDetail", () => {
  it("shows facts related to the selected pillar instead of repeating one global drawer", () => {
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      dayMaster: "戊土",
      monthCommand: "寅月",
      timezone: "Asia/Shanghai",
      timeBasis: "民用时",
      ziHour: "按午夜换日",
    });

    const month = resolveBaziFocusDetail(view, "month");
    const day = resolveBaziFocusDetail(view, "day");
    const hour = resolveBaziFocusDetail(view, "hour");

    expect(month?.facts).toContainEqual({ label: "月令", text: "寅月" });
    expect(month?.facts.some((fact) => fact.label === "日主")).toBe(false);
    expect(day?.facts).toContainEqual({ label: "日主", text: "戊土" });
    expect(day?.facts.some((fact) => fact.label === "月令")).toBe(false);
    expect(hour?.facts).toContainEqual({ label: "子时策略", text: "按午夜换日" });
    expect(hour?.title).toBe("时柱 · 丁卯");
    expect(hour?.facts.some((fact) => fact.label === "时柱")).toBe(false);
  });

  it("resolves label, facts, and limits from public facts without inventing stars", () => {
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      timezone: "Asia/Shanghai",
      timeBasis: "民用时",
    });
    const detail = resolveBaziFocusDetail(view, "year");
    expect(detail).not.toBeNull();
    expect(detail?.id).toBe("year");
    expect(detail?.title).toContain("年柱");
    expect(detail?.title).toContain("甲子");
    expect(detail?.facts.some((fact) => fact.label === "时间口径")).toBe(true);
    expect(detail?.facts.some((fact) => fact.text === "Asia/Shanghai")).toBe(
      true,
    );
    expect(detail?.sources).toEqual([]);
    expect(detail?.limits).toContain(
      "暂无与该柱直接关联的公开依据；请以下方依据卡标注的“支持事实”为准。",
    );
    expect(detail?.limits.length).toBeGreaterThan(0);
    expect(JSON.stringify(detail)).not.toMatch(
      /iztro|lunar-javascript|ziwei-doushu|generateChart|astro\.bySolar/,
    );
  });

  it("fills pillar sources from extras and drops the empty-basis disclaimer", () => {
    const view = buildBaziWorkspaceView({
      pillars: FOUR_PILLARS,
      timezone: "Asia/Shanghai",
    });
    const detail = resolveBaziFocusDetail(view, "day", {
      facts: [{ label: "藏干", text: "甲、丙、戊" }],
      sources: ["测试古法命中 · 测试古籍 L10-L12"],
    });
    expect(detail?.facts).toContainEqual({ label: "藏干", text: "甲、丙、戊" });
    expect(detail?.sources).toEqual(["测试古法命中 · 测试古籍 L10-L12"]);
    expect(detail?.limits.join("")).not.toContain("暂无与该柱直接关联的公开依据");
  });

  it("returns null for unknown cell ids", () => {
    const view = buildBaziWorkspaceView({ pillars: FOUR_PILLARS });
    expect(resolveBaziFocusDetail(view, "unknown-palace")).toBeNull();
  });
});

describe("baziWorkspaceFactsFromChart", () => {
  it("adapts BaziChartView without breaking its public shape", () => {
    const chart: BaziChartView = {
      pillars: { year: "甲子", month: "丙寅", day: "戊午", hour: "" },
      dayMaster: null,
      monthCommand: null,
      activeLuck: null,
      birthTime: null,
      gender: null,
      location: null,
      timeBasis: "民用时",
      ziHour: null,
      timezone: "Asia/Shanghai",
      targetDay: null,
      targetPeriod: null,
      calendarSummary: null,
      highlights: [],
      secondary: [],
    };
    const facts = baziWorkspaceFactsFromChart(chart);
    expect(facts.pillars?.hour).toBeNull();
    expect(facts.timeBasis).toBe("民用时");
    expect(facts.timezone).toBe("Asia/Shanghai");

    const view = buildBaziWorkspaceView(facts);
    expect(view.cells.find((cell) => cell.id === "hour")?.value).toBeNull();
    expect(view.cells.find((cell) => cell.id === "hour")?.badges).toContain(
      "时辰未知",
    );
  });
});
