import { describe, expect, it } from "vitest";

import {
  baziWorkspaceFactsFromChart,
  buildBaziWorkspaceView,
  resolveBaziFocusDetail,
} from "@/lib/chart-workspace";
import type { BaziChartView } from "@/lib/reading-display";

const FOUR_PILLARS = {
  year: "甲子",
  month: "丙寅",
  day: "戊午",
  hour: "丁卯",
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
      "unavailable",
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
      "unavailable",
    );
    expect(view.layers.find((layer) => layer.id === "yearly")?.status).toBe(
      "unavailable",
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

describe("resolveBaziFocusDetail", () => {
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
    expect(detail?.sources).toContain("服务端公开事实");
    expect(detail?.limits.length).toBeGreaterThan(0);
    expect(JSON.stringify(detail)).not.toMatch(
      /iztro|lunar-javascript|ziwei-doushu|generateChart|astro\.bySolar/,
    );
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
