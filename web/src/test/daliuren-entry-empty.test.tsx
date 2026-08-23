import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import {
  DALIUREN_ENTRY_SILHOUETTE_CAPTION,
  DALIUREN_ENTRY_SUITABILITY,
} from "@/components/task/daliuren-entry-copy";
import { DaliurenEntrySilhouette } from "@/components/task/daliuren-entry-silhouette";

afterEach(cleanup);

function entrySource() {
  return readFileSync(resolve(process.cwd(), "src/components/task/daliuren-entry-silhouette.tsx"), "utf8");
}

const SAMPLE_STEMS_BRANCHES = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"];
const SAMPLE_GENERALS = ["贵人", "螣蛇", "朱雀", "六合", "勾陈", "青龙", "天空", "白虎", "太常", "玄武", "太阴", "天后"];

describe("大六壬 S0 空盘剪影", () => {
  it("exports the accepted suitability line within twenty characters", () => {
    expect(DALIUREN_ENTRY_SUITABILITY).toBe("以起课时刻立四课三传，逐课核验");
    expect(DALIUREN_ENTRY_SUITABILITY.length).toBeGreaterThan(0);
    expect(DALIUREN_ENTRY_SUITABILITY.length).toBeLessThanOrEqual(20);
    expect(DALIUREN_ENTRY_SILHOUETTE_CAPTION).toBe("提交后由服务端生成，可核验");
  });

  it("renders empty four-lesson columns and three-transmission stairs without sample ganzhi or generals", () => {
    expect(entrySource()).toMatch(/mode=["']silhouette["']/);
    expect(entrySource()).not.toMatch(/甲子|乙丑|丙寅|丁卯|白虎|朱雀|贵人/);

    render(<DaliurenEntrySilhouette />);

    const figure = screen.getByRole("figure", { name: "大六壬空盘剪影" });
    expect(figure).toBeVisible();
    expect(screen.getByText(DALIUREN_ENTRY_SILHOUETTE_CAPTION)).toBeVisible();
    expect(figure.querySelector("[data-mode='silhouette']")).toBeTruthy();
    expect(figure.querySelectorAll("[data-lesson]")).toHaveLength(4);
    expect(figure.querySelectorAll("[data-stage]")).toHaveLength(3);
    expect(figure.textContent).toContain("初传");
    expect(figure.textContent).toContain("中传");
    expect(figure.textContent).toContain("末传");

    for (const token of [...SAMPLE_STEMS_BRANCHES, ...SAMPLE_GENERALS]) {
      expect(screen.queryByText(token)).not.toBeInTheDocument();
    }
    expect(screen.queryByText("一课·日干")).not.toBeInTheDocument();
    expect(screen.queryByText("待计算")).not.toBeInTheDocument();
    expect(screen.queryByText("天地盘")).not.toBeInTheDocument();
    expect(screen.queryByText("silhouette")).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/—|–/);
  });
});
