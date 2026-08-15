import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const privateSecondaryRoots = ["auth", "checkout", "share", "invite"] as const;

describe("secondary private route metadata", () => {
  it.each(privateSecondaryRoots)("marks /%s as noindex and no-store", (route) => {
    const file = resolve(process.cwd(), `src/app/${route}/layout.tsx`);

    expect(existsSync(file), `missing private layout: /${route}`).toBe(true);
    const source = readFileSync(file, "utf8");
    expect(source).toContain("index: false");
    expect(source).toContain('dynamic = "force-dynamic"');
    expect(source).toContain('fetchCache = "force-no-store"');
  });
});
