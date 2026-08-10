import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const webRoot = path.resolve(import.meta.dirname, "../..");
const srcRoot = path.join(webRoot, "src");

function read(rel: string): string {
  return readFileSync(path.join(srcRoot, rel), "utf8");
}

/**
 * Algorithm entry points that must never appear in frontend chart code.
 * The frontend only renders public facts returned by the backend Runtime;
 * iztro / lunar-javascript / ziwei-doushu stay out of web/ entirely.
 */
const FORBIDDEN_ALGORITHM =
  /generateChart|astro\.bySolar|from ['"]iztro['"]|ziwei-doushu/;

const CHART_SOURCE_FILES = [
  "lib/chart-workspace.ts",
  "lib/reading-display.ts",
  "components/readings/bazi-chart.tsx",
  "components/readings/chart-workspace-shell.tsx",
  "components/birth-basis-summary.tsx",
  "components/profile-form.tsx",
];

describe("ziwei UI-only boundary", () => {
  it("does not depend on iztro, lunar-javascript, or ziwei-doushu", () => {
    const pkg = readFileSync(path.join(webRoot, "package.json"), "utf8");
    expect(pkg).not.toMatch(/"iztro"/);
    expect(pkg).not.toMatch(/"lunar-javascript"/);
    expect(pkg).not.toMatch(/"ziwei-doushu"/);

    const manifest = JSON.parse(pkg) as {
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
    };
    const deps = { ...manifest.dependencies, ...manifest.devDependencies };
    expect(deps).not.toHaveProperty("iztro");
    expect(deps).not.toHaveProperty("lunar-javascript");
    expect(deps).not.toHaveProperty("ziwei-doushu");
  });

  for (const file of CHART_SOURCE_FILES) {
    const fullPath = path.join(srcRoot, file);
    // Skip files that have not landed yet; the scan locks them once they exist.
    it.skipIf(!existsSync(fullPath))(
      `keeps ${file} free of chart algorithm entry points`,
      () => {
        const source = read(file);
        expect(source).not.toMatch(FORBIDDEN_ALGORITHM);
      },
    );
  }
});
