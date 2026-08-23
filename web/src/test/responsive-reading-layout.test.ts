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

  it("lets the bazi workspace respond to its container rather than the viewport", () => {
    const css = read("src/components/readings/bazi-chart.module.css");

    expect(css).toMatch(/container-type:\s*inline-size/);
    // S3 双栏由容器宽度驱动：左盘 480–520px，右阅读区 ≥360px（DESIGN §5/§7.2）。
    expect(css).toMatch(
      /@container \(min-width: 62rem\)[\s\S]*?\.stage\s*\{[\s\S]*?grid-template-columns:\s*minmax\(30rem, 32\.5rem\)\s+minmax\(22\.5rem, 1fr\)/,
    );
  });

  it("opens the evidence column only on a roomy desktop and clears the sticky header", () => {
    const css = read("src/components/app-surface.module.css");

    expect(css).toMatch(
      /@media \(min-width: 80rem\)[\s\S]*?\.readingLayout\s*\{[\s\S]*?grid-template-columns/,
    );
    expect(css).toMatch(/\.evidenceRail\s*\{[\s\S]*?top:\s*6\.25rem/);
  });
});
