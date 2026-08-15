import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("repository check contract", () => {
  it("runs the independent Admin checks from the primary make check", () => {
    const source = readFileSync(resolve(process.cwd(), "../Makefile"), "utf8");

    expect(source).toContain("admin-check:");
    expect(source).toContain("npm --prefix admin test");
    expect(source).toContain("npm --prefix admin run lint");
    expect(source).toContain("npm --prefix admin run typecheck");
    expect(source).toContain("npm --prefix admin run build");
    expect(source).toContain("check: backend-check web-check admin-check build");
  });
});
