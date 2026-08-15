import { describe, expect, it } from "vitest";

import {
  ADMIN_ROLE_MATRIX,
  canWriteAdminRoute,
  getAdminRouteAccess,
  getAdminRoutePermission,
} from "@/lib/admin-permissions";
import { resolveAdminRoute } from "@/lib/admin-route-catalog";

function route(pathname: string) {
  const definition = resolveAdminRoute(pathname);
  expect(definition).not.toBeNull();
  return definition!;
}

describe("Admin role permissions", () => {
  it("keeps read access separate from route-specific write commands", () => {
    expect(getAdminRoutePermission("support", route("/users"))).toBe("允许");
    expect(getAdminRouteAccess("support", route("/users"))).toMatchObject({
      read: "允许",
      write: "只读",
    });
    expect(canWriteAdminRoute("support", route("/users"))).toBe(false);
    expect(getAdminRouteAccess("support", route("/support-cases"))).toMatchObject({
      read: "允许",
      write: "提交申请",
    });
    expect(canWriteAdminRoute("support", route("/support-cases"))).toBe(true);

    expect(getAdminRoutePermission("finance", route("/refunds"))).toBe("允许");
    expect(canWriteAdminRoute("finance", route("/refunds"))).toBe(true);
    expect(getAdminRoutePermission("finance", route("/users"))).toBe("只读");
    expect(canWriteAdminRoute("finance", route("/users"))).toBe(false);

    expect(getAdminRoutePermission("ops", route("/products"))).toBe("允许");
    expect(canWriteAdminRoute("ops", route("/products"))).toBe(true);
    expect(canWriteAdminRoute("ops", route("/readings"))).toBe(false);
    expect(canWriteAdminRoute("ops", route("/cms/pages"))).toBe(true);
    expect(getAdminRoutePermission("ops", route("/capabilities"))).toBe("只读");
    expect(canWriteAdminRoute("ops", route("/capabilities"), "INTERNAL_TEST")).toBe(true);
    expect(canWriteAdminRoute("ops", route("/capabilities"), "PUBLIC")).toBe(false);
    expect(canWriteAdminRoute("ops", route("/capabilities"), "PAUSED")).toBe(false);

    expect(getAdminRoutePermission("superadmin", route("/staff"))).toBe("允许");
    expect(canWriteAdminRoute("superadmin", route("/staff"))).toBe(true);
  });

  it("publishes exactly one definition for every staff role", () => {
    expect(ADMIN_ROLE_MATRIX.map((definition) => definition.role)).toEqual([
      "support",
      "finance",
      "ops",
      "superadmin",
    ]);
  });
});
