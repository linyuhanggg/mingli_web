import type { StaffRole } from "@/lib/api";
import type { AdminCapabilityState } from "@/lib/admin-catalog";
import type { AdminRouteDefinition } from "@/lib/admin-route-catalog";

export const ADMIN_PERMISSION_AREAS = [
  "业务资料与报告",
  "账务与退款",
  "CMS 与运营",
  "能力发布",
  "员工与系统",
] as const;

export type AdminPermissionArea = (typeof ADMIN_PERMISSION_AREAS)[number];
export type AdminPermissionLevel = "允许" | "只读" | "提交申请" | "禁止";

export const ADMIN_ROLE_MATRIX: readonly {
  role: StaffRole;
  label: string;
  permissions: Record<AdminPermissionArea, AdminPermissionLevel>;
}[] = [
  {
    role: "support",
    label: "客服",
    permissions: {
      "业务资料与报告": "允许",
      "账务与退款": "提交申请",
      "CMS 与运营": "禁止",
      "能力发布": "只读",
      "员工与系统": "禁止",
    },
  },
  {
    role: "finance",
    label: "财务",
    permissions: {
      "业务资料与报告": "只读",
      "账务与退款": "允许",
      "CMS 与运营": "禁止",
      "能力发布": "只读",
      "员工与系统": "禁止",
    },
  },
  {
    role: "ops",
    label: "运营",
    permissions: {
      "业务资料与报告": "只读",
      "账务与退款": "只读",
      "CMS 与运营": "允许",
      "能力发布": "只读",
      "员工与系统": "禁止",
    },
  },
  {
    role: "superadmin",
    label: "超级管理员",
    permissions: {
      "业务资料与报告": "允许",
      "账务与退款": "允许",
      "CMS 与运营": "允许",
      "能力发布": "允许",
      "员工与系统": "允许",
    },
  },
];

export const ADMIN_ROUTE_PERMISSION_AREAS: Readonly<
  Record<string, AdminPermissionArea>
> = {
  "/": "员工与系统",
  "/login": "员工与系统",
  "/dashboard": "员工与系统",
  "/users": "业务资料与报告",
  "/users/[id]": "业务资料与报告",
  "/subjects": "业务资料与报告",
  "/subjects/[id]": "业务资料与报告",
  "/data-rights": "业务资料与报告",
  "/support-cases": "业务资料与报告",
  "/products": "CMS 与运营",
  "/products/[id]/versions": "CMS 与运营",
  "/capabilities": "能力发布",
  "/cms/pages": "CMS 与运营",
  "/cms/daily": "CMS 与运营",
  "/cms/tools": "CMS 与运营",
  "/cms/library": "CMS 与运营",
  "/cms/help": "CMS 与运营",
  "/cms/policies": "CMS 与运营",
  "/charts": "业务资料与报告",
  "/readings": "业务资料与报告",
  "/readings/[id]": "业务资料与报告",
  "/reading-jobs": "业务资料与报告",
  "/verifications": "业务资料与报告",
  "/observations": "业务资料与报告",
  "/runtime": "能力发布",
  "/model-profiles": "能力发布",
  "/orders": "账务与退款",
  "/payments": "账务与退款",
  "/refunds": "账务与退款",
  "/reconciliation": "账务与退款",
  "/entitlements": "账务与退款",
  "/referrals": "CMS 与运营",
  "/referrals/[id]": "CMS 与运营",
  "/appeals": "账务与退款",
  "/staff": "员工与系统",
  "/sessions": "员工与系统",
  "/notifications": "员工与系统",
  "/audit": "员工与系统",
  "/settings": "员工与系统",
  "/health": "员工与系统",
};

export function getAdminPermissionArea(
  route: AdminRouteDefinition,
): AdminPermissionArea {
  return ADMIN_ROUTE_PERMISSION_AREAS[route.path] ?? "员工与系统";
}

export function getAdminRoutePermission(
  role: StaffRole,
  route: AdminRouteDefinition,
): AdminPermissionLevel {
  const definition = ADMIN_ROLE_MATRIX.find((candidate) => candidate.role === role);
  return definition?.permissions[getAdminPermissionArea(route)] ?? "禁止";
}

const SUPPORT_APPLICATION_ROUTES = new Set(["/support-cases", "/appeals"]);
const FINANCE_WRITE_ROUTES = new Set([
  "/orders",
  "/payments",
  "/refunds",
  "/reconciliation",
  "/appeals",
]);
const OPS_WRITE_ROUTES = new Set([
  "/products",
  "/products/[id]/versions",
  "/cms/pages",
  "/cms/daily",
  "/cms/tools",
  "/cms/library",
  "/cms/help",
  "/cms/policies",
  "/reading-jobs",
  "/entitlements",
  "/referrals",
  "/referrals/[id]",
]);

export function getAdminRouteWritePermission(
  role: StaffRole,
  route: AdminRouteDefinition,
  capabilityState: AdminCapabilityState = "INTERNAL_TEST",
): AdminPermissionLevel {
  if (role === "superadmin") return "允许";
  if (role === "support") {
    return SUPPORT_APPLICATION_ROUTES.has(route.path) ? "提交申请" : "只读";
  }
  if (role === "finance") {
    return FINANCE_WRITE_ROUTES.has(route.path) ? "允许" : "只读";
  }
  if (role === "ops") {
    if (route.path === "/capabilities") {
      return ["UI_PREBUILT", "ADAPTING", "INTERNAL_TEST"].includes(capabilityState)
        ? "允许"
        : "只读";
    }
    return OPS_WRITE_ROUTES.has(route.path) ? "允许" : "只读";
  }
  return "禁止";
}

export type AdminRouteAccess = {
  area: AdminPermissionArea;
  read: AdminPermissionLevel;
  write: AdminPermissionLevel;
};

export function getAdminRouteAccess(
  role: StaffRole,
  route: AdminRouteDefinition,
  capabilityState: AdminCapabilityState = "INTERNAL_TEST",
): AdminRouteAccess {
  return {
    area: getAdminPermissionArea(route),
    read: getAdminRoutePermission(role, route),
    write: getAdminRouteWritePermission(role, route, capabilityState),
  };
}

export function canWriteAdminRoute(
  role: StaffRole | undefined,
  route: AdminRouteDefinition,
  capabilityState: AdminCapabilityState = "INTERNAL_TEST",
): boolean {
  if (!role) return false;
  const permission = getAdminRouteWritePermission(role, route, capabilityState);
  return permission === "允许" || permission === "提交申请";
}
