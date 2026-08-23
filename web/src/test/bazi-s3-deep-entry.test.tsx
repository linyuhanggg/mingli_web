import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { BaziChart } from "@/components/readings/bazi-chart";
import type { BaziChartView } from "@/lib/reading-display";
import type { BaziCoreFacts } from "@/view-models/registry";

afterEach(cleanup);

const OFFER = {
  name: "八字命盘深读",
  coverage: "当前这张已排出命盘的四柱与月令",
  priceText: "由服务端标价",
  refundBoundary: "未交付可退",
};

function chart(overrides: Partial<BaziChartView> = {}): BaziChartView {
  return {
    pillars: { year: "甲子", month: "乙丑", day: "丙寅", hour: "丁卯" },
    coreFacts: {
      day_master: { stem: "丙", element: "fire", polarity: "阳" },
      month_command: {
        branch: "丑",
        label: "丑月",
        main_qi: "己",
        main_qi_element: "earth",
      },
      luck_cycles: {
        status: "calculated",
        direction: "forward",
        unavailable: [],
        cycles: [
          { sequence: 1, pillar: "戊辰", start_age_years: 8, end_age_years: 17 },
          { sequence: 2, pillar: "己巳", start_age_years: 18, end_age_years: 27 },
        ],
      },
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
    ...overrides,
  };
}

function deep() {
  return screen.getByRole("heading", { name: "深读" }).closest("section");
}

describe("八字 S3 M13 深读入口", () => {
  it("shows the no-offer gate with on-screen quotes and no checkout", () => {
    render(<BaziChart chart={chart()} />);

    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
    expect(screen.getByRole("status", { name: "测试期未开放" })).toHaveAttribute("data-state", "unavailable");
    expect(deep()).toHaveTextContent("日主丙火（阳）");
    expect(deep()).toHaveTextContent("丑月");
    expect(deep()).toHaveTextContent("大运 2 步已列");
    expect(deep()).not.toHaveTextContent(/强弱|喜忌|吉凶|大吉|大凶|旺衰/);
    expect(deep()).not.toHaveTextContent(/GAP-BZ/);
    expect(screen.queryByText(/¥|￥|\d+\s*元/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买|支付/ })).not.toBeInTheDocument();
    expect(screen.queryByText("reading_version_id")).not.toBeInTheDocument();
    expect(screen.queryByText("offer_id")).not.toBeInTheDocument();
  });

  it("does not invent quotes from hidden luck steps or strength verdicts", () => {
    render(
      <BaziChart
        chart={chart({
          coreFacts: {
            day_master: { stem: "丙", element: "fire", polarity: "阳" },
            luck_cycles: null,
          } as unknown as BaziCoreFacts,
        })}
      />,
    );

    expect(deep()).toHaveTextContent("日主丙火（阳）");
    expect(deep()).not.toHaveTextContent("大运");
    expect(deep()).not.toHaveTextContent("身强");
    expect(deep()).not.toHaveTextContent("用神火");
    expect(deep()).not.toHaveTextContent("旺");
  });

  it("renders a passed offer card without inventing checkout, and confirming only says 确认中", () => {
    const { rerender } = render(<BaziChart chart={chart()} offer={OFFER} />);

    expect(screen.getByText("八字命盘深读")).toBeVisible();
    expect(screen.getByText("当前这张已排出命盘的四柱与月令")).toBeVisible();
    expect(screen.getByText("由服务端标价")).toBeVisible();
    expect(screen.getByText("未交付可退")).toBeVisible();
    expect(screen.getByText("绑定当前这张已排出的命盘")).toBeVisible();
    expect(screen.getByRole("link", { name: "登录后继续" })).toHaveAttribute("href", "/auth/login");
    expect(screen.queryByRole("status", { name: "测试期未开放" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买/ })).not.toBeInTheDocument();

    rerender(<BaziChart chart={chart()} offer={OFFER} s4Phase="confirming" />);
    expect(screen.getByRole("status", { name: "确认中" })).toBeVisible();
    expect(screen.queryByText("由服务端标价")).not.toBeInTheDocument();
    expect(screen.queryByText(/订单号/)).not.toBeInTheDocument();
  });

  it("uses locked and fake-gateway copy without treating them as paid", () => {
    const { rerender } = render(<BaziChart chart={chart()} s4Phase="locked" />);
    expect(screen.getByRole("status", { name: "已锁定" })).toHaveAttribute("data-state", "locked");
    expect(screen.queryByRole("status", { name: "测试期未开放" })).not.toBeInTheDocument();

    rerender(<BaziChart chart={chart()} offer={OFFER} s4Phase="gateway_unavailable" />);
    expect(screen.getByRole("status", { name: "支付暂时不可用" })).toHaveAttribute("data-state", "unavailable");
    expect(screen.queryByText("由服务端标价")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /结账|购买|支付/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "登录后继续" })).not.toBeInTheDocument();
  });

  it("keeps the deep-entry module off shared pages and off other arts", () => {
    const boardSource = readFileSync(resolve(process.cwd(), "src/components/readings/bazi-chart.tsx"), "utf8");
    const entrySource = readFileSync(
      resolve(process.cwd(), "src/components/readings/bazi-deep-entry.tsx"),
      "utf8",
    );
    const css = readFileSync(
      resolve(process.cwd(), "src/components/readings/bazi-deep-entry.module.css"),
      "utf8",
    );
    const runtime = readFileSync(resolve(process.cwd(), "src/components/readings/runtime-chart.tsx"), "utf8");
    const experience = readFileSync(resolve(process.cwd(), "src/components/task/product-task-experience.tsx"), "utf8");
    const readingResult = readFileSync(resolve(process.cwd(), "src/components/readings/reading-result.tsx"), "utf8");
    expect(boardSource).toContain("bazi-deep-entry");
    expect(entrySource).not.toMatch(/ziwei-free-summary|daliuren-free-summary|liuyao-line-tower|meihua-chart|runtime-chart|product-task-experience|reading-result|GAP-BZ/);
    expect(css).toMatch(/--color-text/);
    expect(css).toMatch(/min-height:\s*var\(--target-min\)/);
    expect(css).not.toMatch(/color-success|color-danger|surface-success|surface-danger/);
    expect(css).not.toMatch(/linear-gradient|radial-gradient|box-shadow:\s*0 0/);
    expect(runtime).not.toContain("bazi-deep-entry");
    expect(experience).not.toContain("bazi-deep-entry");
    expect(readingResult).not.toContain("bazi-deep-entry");
  });
});
