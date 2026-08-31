import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

function read(relativePath: string) {
  return readFileSync(join(process.cwd(), relativePath), "utf8");
}

describe("responsive reading layout", () => {
  it("keeps the chart detail inline instead of creating a third desktop column", () => {
    const css = read("src/components/readings/chart-workspace-shell.module.css");

    expect(css).not.toMatch(
      /@media \(min-width: 68rem\)[\s\S]*?\.body\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0, 1fr\)\s+minmax\(15rem, 19rem\)/,
    );
  });

  it("lets the four pillars respond to their container rather than the viewport", () => {
    const css = read("src/components/readings/bazi-chart.module.css");

    expect(css).toMatch(/container-type:\s*inline-size/);
    expect(css).toMatch(/@container \(min-width: 34rem\)/);
  });

  it("uses the full result width until a real focus detail exists", () => {
    const shellCss = read("src/components/readings/chart-workspace-shell.module.css");
    const resultCss = read("src/components/readings/reading-result.module.css");

    expect(shellCss).toMatch(
      /@media \(min-width: 80rem\)[\s\S]*?\.body\[data-has-detail="true"\]\s*\{[\s\S]*?grid-template-columns/,
    );
    expect(shellCss).not.toMatch(/@media \(min-width: 1024px\)[\s\S]*?grid-template-columns/);
    expect(resultCss).toMatch(
      /@media \(min-width: 80rem\)[\s\S]*?\.chartFirstLayout\.chartFirstLayout\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0,\s*1fr\)/,
    );
  });

  it("keeps the chart-first rail and task controls responsive without visual-order hacks", () => {
    const resultCss = read("src/components/readings/reading-result.module.css");
    const taskCss = read("src/components/task/bazi-deep-task-flow.module.css");

    expect(resultCss).toMatch(/\.chartFirstRail/);
    expect(taskCss).toMatch(/\.backButton\s*\{[\s\S]*?min-height:\s*var\(--target-min\)/);
    expect(taskCss).not.toMatch(/\.result\s+:global\(\[data-bazi-chart-host="true"\]\)\s*\{[\s\S]*?margin-inline:\s*-/);
    expect(taskCss).not.toMatch(/order:\s*-1/);
  });
});
