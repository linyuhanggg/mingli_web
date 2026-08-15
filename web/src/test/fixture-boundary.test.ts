import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

function pageFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) return pageFiles(path);
    return entry.name === "page.tsx" ? [path] : [];
  });
}

describe("UI fixture boundary", () => {
  it("keeps demo data out of every normal route source", () => {
    for (const file of pageFiles(resolve(process.cwd(), "src/app"))) {
      const normalizedPath = decodeURIComponent(file).replaceAll("\\", "/");
      if (normalizedPath.includes("/_ui-lab/")) continue;
      const source = readFileSync(file, "utf8");
      expect(source, file).not.toMatch(/@\/fixtures|UI_LAB_FIXTURES|UI 演示数据/);
    }
  });
});
