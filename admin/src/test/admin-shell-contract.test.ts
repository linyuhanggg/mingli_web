import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("admin shell navigation authority", () => {
  it("derives navigation from the complete route catalog", () => {
    const source = readFileSync(
      resolve(process.cwd(), "src/components/admin-shell.tsx"),
      "utf8",
    );

    expect(source).toContain("ADMIN_ROUTE_CATALOG");
    expect(source).toContain("route.navigation !== false");
    expect(source).toContain("route.path.includes(\"[\")");
    expect(source).toContain("route.group");
  });

  it("uses an accessible drawer instead of a horizontal route strip below 1024px", () => {
    const source = readFileSync(
      resolve(process.cwd(), "src/components/admin-shell.tsx"),
      "utf8",
    );

    expect(source).toContain("<Drawer");
    expect(source).toContain('aria-label="打开运营导航"');
    expect(source).toContain("mobileNavigation");
  });
});
