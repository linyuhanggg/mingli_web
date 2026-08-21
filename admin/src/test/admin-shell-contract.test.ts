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

describe("admin shell page header contract", () => {
  const shellSource = readFileSync(
    resolve(process.cwd(), "src/components/admin-shell.tsx"),
    "utf8",
  );
  const shellStyles = readFileSync(
    resolve(process.cwd(), "src/components/admin-shell.module.css"),
    "utf8",
  );

  it("provides an optional actions slot without duplicating the page heading", () => {
    expect(shellSource).toContain("actions?: ReactNode");
    expect(shellSource).toContain("{actions ?");
    expect(shellSource.match(/<h1/g)).toHaveLength(1);
    expect(shellSource).not.toContain("<h2");
  });

  it("keeps the duty on one titled ellipsis line and uses the 20px title token", () => {
    expect(shellSource).toContain("<p title={duty}>{duty}</p>");
    expect(shellStyles).toMatch(/\.pageHead h1\s*\{[^}]*font-size:\s*var\(--font-size-card\)/s);
    expect(shellStyles).toMatch(/\.pageHead p\s*\{[^}]*text-overflow:\s*ellipsis/s);
    expect(shellStyles).toMatch(/\.pageHead p\s*\{[^}]*white-space:\s*nowrap/s);
  });

  it("stacks page actions at full width with a 48px target on mobile", () => {
    expect(shellStyles).toMatch(/\.pageActions\s*\{[^}]*width:\s*100%/s);
    expect(shellStyles).toMatch(/\.pageActions > \*\s*\{[^}]*width:\s*100%/s);
    expect(shellStyles).toMatch(/\.pageActions > \*\s*\{[^}]*min-height:\s*3rem/s);
    expect(shellStyles).toMatch(/@media \(min-width:\s*48rem\)/);
  });
});

describe("admin shell load error contract", () => {
  const shellSource = readFileSync(
    resolve(process.cwd(), "src/components/admin-shell.tsx"),
    "utf8",
  );
  const shellStyles = readFileSync(
    resolve(process.cwd(), "src/components/admin-shell.module.css"),
    "utf8",
  );

  it("redirects only an unauthenticated shell request before recording a load error", () => {
    expect(shellSource).toMatch(
      /if \(result\.status === 401\) \{\s*router\.replace\("\/login"\);\s*return;\s*\}\s*setLoadError\(result\.title\)/s,
    );
    expect(shellSource).not.toMatch(/result\.status === 403[\s\S]*router\.replace/);
  });

  it("replaces the business surface with one shell alert when staff loading fails", () => {
    expect(shellSource).toContain('className={styles.loadError}');
    expect(shellSource).toMatch(
      /\{loadError \? \([\s\S]*role="alert"[\s\S]*\) : \(\s*children\s*\)\}/,
    );
    expect(shellSource.match(/role="alert"/g)).toHaveLength(1);
  });

  it("keeps the shell error readable without adding motion or viewport-specific state", () => {
    expect(shellStyles).toMatch(/\.loadError\s*\{[^}]*max-width:\s*48rem/s);
    expect(shellStyles).not.toMatch(/\.loadError[^}]*animation:/s);
    expect(shellStyles).not.toMatch(/\.loadError[^}]*transition:/s);
  });
});
