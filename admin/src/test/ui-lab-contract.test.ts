import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";
import nextConfig from "../../next.config";
import { STATUS_STATES } from "@/components/ui/status";
import {
  ADMIN_ROLE_MATRIX,
  ADMIN_WRITE_OPERATION_STATES,
  buildAdminUiLabCatalogViewModel,
} from "@/lib/admin-ui-lab";
import { resolveAdminRoute } from "@/lib/admin-route-catalog";

const EXPECTED_STATUS_STATES = [
  "loading",
  "empty",
  "error",
  "processing",
  "success",
  "unavailable",
  "unauthorized",
  "locked",
] as const;

describe("admin UI Lab boundary", () => {
  it("allows local browser hosts to hydrate the development UI Lab", () => {
    expect(nextConfig.allowedDevOrigins).toEqual(["127.0.0.1", "localhost"]);
  });

  it("is not reachable from production output", () => {
    const source = readFileSync(resolve(process.cwd(), "src/app/%5Fui-lab/page.tsx"), "utf8");
    expect(source).toContain('process.env.NODE_ENV === "production"');
    expect(source).toContain("notFound()");
    expect(source).toContain("AdminUiLabWorkbench");
    expect(source).toContain('demoRole="support"');
  });

  it("keeps the catch-all route as an unconditional not-found boundary", () => {
    const source = readFileSync(resolve(process.cwd(), "src/app/[...segments]/page.tsx"), "utf8");
    expect(source).toContain("notFound()");
    expect(source).not.toContain("AdminCatalogPage");
    expect(source).not.toContain("AdminUiLabPage");
  });

  it("publishes the complete shared status state set", () => {
    expect(STATUS_STATES).toEqual(EXPECTED_STATUS_STATES);
  });

  it("publishes the four-role permission and write-operation matrices", () => {
    expect(ADMIN_ROLE_MATRIX.map((role) => role.role)).toEqual([
      "support",
      "finance",
      "ops",
      "superadmin",
    ]);
    expect(
      ADMIN_ROLE_MATRIX.every((role) => Object.keys(role.permissions).length > 0),
    ).toBe(true);
    expect(ADMIN_WRITE_OPERATION_STATES).toEqual([
      "无权限",
      "只读",
      "确认",
      "原因",
      "保存中",
      "成功",
      "验证失败",
      "版本冲突",
      "对象已变化",
      "审计完成",
    ]);
  });

  it("keeps fixture records in the UI Lab adapter and out of normal pages", () => {
    const route = resolveAdminRoute("/orders");
    expect(route).not.toBeNull();

    const model = buildAdminUiLabCatalogViewModel(route!, {
      state: "ready",
      role: "finance",
      capabilityState: "INTERNAL_TEST",
      writeState: "确认",
    });

    expect(model.source).toBe("fixture");
    expect(model.records.length).toBeGreaterThan(0);
    expect(model.notice).toContain("UI 演示数据");

    const normalPage = readFileSync(
      resolve(process.cwd(), "src/components/admin-catalog-page.tsx"),
      "utf8",
    );
    expect(normalPage).not.toContain("admin-ui-lab");
  });

  it("uses a real preview container so selected widths trigger inner responsive rules", () => {
    const labCss = readFileSync(
      resolve(process.cwd(), "src/components/admin-ui-lab-workbench.module.css"),
      "utf8",
    );
    const surfaceCss = readFileSync(
      resolve(process.cwd(), "src/components/admin-catalog-surface.module.css"),
      "utf8",
    );
    const tableCss = readFileSync(
      resolve(process.cwd(), "src/components/ui/table.module.css"),
      "utf8",
    );

    expect(labCss).toMatch(/\.workbench\s*\{[^}]*contain:\s*layout;/s);
    expect(labCss).toMatch(/\.preview\s*\{[^}]*container(?:-type)?:\s*inline-size;/s);
    expect(labCss).toMatch(/\.preview\s*\{[^}]*container-name:\s*admin-preview;/s);
    expect(surfaceCss).toContain("@container admin-preview");
    expect(tableCss).toContain("@container admin-preview");
  });

  it("turns narrow tables into summary rows instead of horizontal page-like scrolling", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/ui/table.module.css"),
      "utf8",
    );

    expect(css).toContain('@media (max-width: 47.99rem)');
    expect(css).toMatch(/\.scroller\s*\{[^}]*overflow-x:\s*visible;/s);
    expect(css).toMatch(/\.td\[data-label\]::before/);
  });

  it("allows the React debugger only outside production", async () => {
    const rules = await nextConfig.headers!();
    const globalRule = rules.find((rule) => rule.source === "/:path*");
    const csp = globalRule?.headers.find(
      (header) => header.key === "Content-Security-Policy",
    )?.value;

    expect(csp).toContain("'unsafe-eval'");
  });
});
