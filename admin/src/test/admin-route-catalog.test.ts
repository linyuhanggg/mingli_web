import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { ADMIN_ROUTE_CATALOG, resolveAdminRoute } from "@/lib/admin-route-catalog";

describe("admin route catalog", () => {
  it("covers every P3 route family from the authoritative checklist", () => {
    const paths = ADMIN_ROUTE_CATALOG.map((route) => route.path);

    expect(paths).toEqual(
      expect.arrayContaining([
        "/login",
        "/",
        "/dashboard",
        "/users",
        "/users/[id]",
        "/subjects",
        "/subjects/[id]",
        "/data-rights",
        "/support-cases",
        "/products",
        "/products/[id]/versions",
        "/capabilities",
        "/cms/pages",
        "/cms/daily",
        "/cms/tools",
        "/cms/library",
        "/cms/help",
        "/cms/policies",
        "/charts",
        "/readings",
        "/readings/[id]",
        "/reading-jobs",
        "/verifications",
        "/observations",
        "/runtime",
        "/model-profiles",
        "/orders",
        "/payments",
        "/refunds",
        "/reconciliation",
        "/entitlements",
        "/referrals",
        "/referrals/[id]",
        "/appeals",
        "/staff",
        "/sessions",
        "/notifications",
        "/audit",
        "/settings",
        "/health",
      ]),
    );
  });

  it("returns a connected operations state for registered runtime releases", () => {
    expect(resolveAdminRoute("/runtime")).toMatchObject({
      path: "/runtime",
      state: "prebuilt",
      surface: "operations",
    });
  });

  it("does not label connected Admin surfaces as not yet integrated", () => {
    const connectedRoutes = [
      "/users",
      "/users/[id]",
      "/subjects",
      "/subjects/[id]",
      "/products",
      "/products/[id]/versions",
      "/data-rights",
      "/support-cases",
      "/appeals",
      "/capabilities",
      "/orders",
      "/payments",
      "/refunds",
      "/reconciliation",
      "/entitlements",
      "/referrals",
      "/referrals/[id]",
      "/notifications",
      "/audit",
      "/sessions",
      "/staff",
      "/settings",
      "/health",
      "/reading-jobs",
      "/charts",
      "/readings",
      "/readings/[id]",
      "/verifications",
      "/runtime",
      "/model-profiles",
      "/cms/pages",
      "/cms/daily",
      "/cms/tools",
      "/cms/library",
      "/cms/help",
      "/cms/policies",
    ];

    for (const path of connectedRoutes) {
      expect(resolveAdminRoute(path)?.duty, path).not.toMatch(/尚未接入/);
    }
  });

  it("assigns different surface contracts to lists, details, health, and settings", () => {
    expect(resolveAdminRoute("/users")?.surface).toBe("list");
    expect(resolveAdminRoute("/users/demo-user")?.surface).toBe("detail");
    expect(resolveAdminRoute("/runtime")?.surface).toBe("operations");
    expect(resolveAdminRoute("/health")?.surface).toBe("health");
    expect(resolveAdminRoute("/settings")?.surface).toBe("settings");
  });

  it("does not turn an unknown pathname into a catalog page", () => {
    expect(resolveAdminRoute("/this-route-does-not-exist")).toBeNull();
  });

  it("keeps the checklist dashboard as the canonical overview route", () => {
    const dashboard = resolve(process.cwd(), "src/app/dashboard/page.tsx");
    expect(existsSync(dashboard)).toBe(true);
    expect(readFileSync(dashboard, "utf8")).toContain("AdminOverviewPage");
  });

  it("gives every catalog route an explicit App Router page", () => {
    for (const route of ADMIN_ROUTE_CATALOG) {
      const relative = route.path === "/" ? "page.tsx" : `${route.path.slice(1)}/page.tsx`;
      expect(existsSync(resolve(process.cwd(), "src/app", relative)), route.path).toBe(true);
    }
  });

  it("wraps long route contract tokens on narrow viewports", () => {
    const css = readFileSync(resolve(process.cwd(), "src/components/ui.module.css"), "utf8");
    expect(css).toMatch(/\.definitionList dd[\s\S]*overflow-wrap:\s*anywhere/);
  });
});
