import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BaziFactMatrix } from "@/components/bazi-fact-matrix";
import type { ReadingFact } from "@/lib/api";

const SUBJECT = "profile-version:22222222-2222-4222-8222-222222222222";

function fact(key: string, value: unknown): ReadingFact {
  return {
    ref: `fact:${SUBJECT}/calculated/bazi/${key}`,
    subject_ref: SUBJECT,
    kind_id: "kind.fact",
    value,
    display_text: `${key}：不应显示的原始文本`,
  };
}

const facts: ReadingFact[] = [
  fact("four_pillars", {
    year: "庚辰",
    month: "丙戌",
    day: "己酉",
    hour: "丁卯",
  }),
  fact("hidden_stems", {
    year: { branch: "辰", stems: ["戊", "乙", "癸"] },
    month: { branch: "戌", stems: ["戊", "辛", "丁"] },
    day: { branch: "酉", stems: ["辛"] },
    hour: { branch: "卯", stems: ["乙"] },
  }),
  fact("ten_gods", {
    heavenly_stems: {
      year: { stem: "庚", ten_god: "伤官" },
      month: { stem: "丙", ten_god: "正印" },
      day: { stem: "己", ten_god: "日主" },
      hour: { stem: "丁", ten_god: "偏印" },
    },
    hidden_stems: {
      year: [
        { stem: "戊", ten_god: "劫财" },
        { stem: "乙", ten_god: "七杀" },
        { stem: "癸", ten_god: "偏财" },
      ],
      month: [
        { stem: "戊", ten_god: "劫财" },
        { stem: "辛", ten_god: "食神" },
        { stem: "丁", ten_god: "偏印" },
      ],
      day: [{ stem: "辛", ten_god: "食神" }],
      hour: [{ stem: "乙", ten_god: "七杀" }],
    },
  }),
  fact("nayin", {
    year: "白蜡金",
    month: "屋上土",
    day: "大驿土",
    hour: "炉中火",
  }),
  fact("element_inventory", {
    visible_stem_branch_counts: { 木: 2, 火: 1, 土: 4, 金: 1 },
    hidden_stem_occurrence_counts: { 木: 2, 火: 2, 土: 3, 金: 2, 水: 1 },
  }),
  fact("shensha_auxiliary", {
    evaluated_rules: [{ name: "未命中的驿马", matched: false }],
    calculated_items: [
      {
        name: "桃花",
        target_branch: "卯",
        anchor_positions: ["year", "day"],
        matched_positions: ["hour"],
      },
    ],
  }),
];

describe("BaziFactMatrix", () => {
  it("renders only the public fact projection as an accessible chart detail matrix", () => {
    render(<BaziFactMatrix facts={facts} />);

    expect(
      screen.getByRole("region", { name: "八字细盘明细" }),
    ).toBeInTheDocument();

    const pillarTable = screen.getByRole("table", {
      name: "四柱藏干、十神与纳音",
    });
    expect(
      within(pillarTable).getByRole("columnheader", { name: "年柱 庚辰" }),
    ).toBeInTheDocument();
    expect(within(pillarTable).getAllByText("戊 · 劫财")).toHaveLength(2);
    expect(within(pillarTable).getByText("白蜡金")).toBeInTheDocument();

    const elementTable = screen.getByRole("table", {
      name: "五行盘面计数",
    });
    expect(
      within(elementTable).getByRole("row", {
        name: "显干支 2 1 4 1 0",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("盘面计数，不代表旺衰或用神。"),
    ).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "神煞辅助" })).toBeInTheDocument();
    expect(screen.getByText("桃花")).toBeInTheDocument();
    expect(screen.getByText("命中：时柱")).toBeInTheDocument();
    expect(screen.queryByText("未命中的驿马")).not.toBeInTheDocument();

    expect(screen.getByText("空亡")).toBeInTheDocument();
    expect(screen.getByText("地势")).toBeInTheDocument();
    expect(screen.getByText("自坐")).toBeInTheDocument();
    expect(screen.getByText("三宫")).toBeInTheDocument();
    expect(screen.getAllByText("5.1 未投影")).toHaveLength(4);
    expect(screen.queryByText(/不应显示的原始文本/)).not.toBeInTheDocument();
  });

  it("renders honest empty states when optional public facts are absent", () => {
    render(<BaziFactMatrix facts={[]} />);

    expect(screen.getByText("五行盘面计数暂缺。")).toBeInTheDocument();
    expect(screen.getByText("神煞辅助事实暂缺。")).toBeInTheDocument();
  });
});
