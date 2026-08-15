import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("private UI brand contract", () => {
  it("does not render the retired brand in user-facing private surfaces", () => {
    for (const file of [
      "src/components/account-center.tsx",
      "src/components/readings/bazi-chart.tsx",
    ]) {
      expect(readFileSync(resolve(process.cwd(), file), "utf8")).not.toContain("FateRadar");
    }
  });
});
