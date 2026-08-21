import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("authentication short routes", () => {
  it.each([
    ["/login", "/auth/login"],
    ["/register", "/auth/register"],
  ])("redirects %s to %s", (route, destination) => {
    const source = readFileSync(
      resolve(process.cwd(), `src/app${route}/page.tsx`),
      "utf8",
    );

    expect(source).toContain(`redirect("${destination}")`);
  });
});
