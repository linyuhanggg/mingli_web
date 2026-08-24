import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import {
  ZIWEI_ENTRY_SILHOUETTE_CAPTION,
  ZIWEI_ENTRY_SUITABILITY,
} from "@/components/task/ziwei-entry-copy";
import { ZiweiEntrySilhouette } from "@/components/task/ziwei-entry-silhouette";

afterEach(cleanup);

function entrySource() {
  return readFileSync(resolve(process.cwd(), "src/components/task/ziwei-entry-silhouette.tsx"), "utf8");
}

describe("紫微 S0 空盘剪影", () => {
  it("keeps the accepted suitability line within twenty characters", () => {
    expect(ZIWEI_ENTRY_SUITABILITY).toBe("从出生时刻安十二宫星曜，逐宫核验");
    expect(ZIWEI_ENTRY_SUITABILITY.length).toBeGreaterThan(0);
    expect(ZIWEI_ENTRY_SUITABILITY.length).toBeLessThanOrEqual(20);
    expect(ZIWEI_ENTRY_SILHOUETTE_CAPTION).toBe("提交后由服务端生成，可核验");
  });

  it("renders the empty ring silhouette without sample stars or stems", () => {
    expect(entrySource()).toMatch(/mode=["']silhouette["']/);

    render(<ZiweiEntrySilhouette />);

    const figure = screen.getByRole("figure", { name: "紫微空盘剪影" });
    expect(figure).toBeVisible();
    expect(screen.getByText(ZIWEI_ENTRY_SILHOUETTE_CAPTION)).toBeVisible();
    expect(figure.querySelectorAll("[data-branch]")).toHaveLength(12);
    expect(figure.querySelector("[data-slot='center']")).toBeTruthy();
    expect(screen.queryByText("天机")).not.toBeInTheDocument();
    expect(screen.queryByText("天府")).not.toBeInTheDocument();
    expect(screen.queryByText("甲子")).not.toBeInTheDocument();
    expect(screen.queryByText("壬寅")).not.toBeInTheDocument();
    expect(screen.queryByText("水二局")).not.toBeInTheDocument();
    expect(screen.queryByText("庙")).not.toBeInTheDocument();
    expect(screen.queryByText("化禄")).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-ZW/)).not.toBeInTheDocument();
    expect(screen.queryByText(/大吉|大凶/)).not.toBeInTheDocument();
  });
});
