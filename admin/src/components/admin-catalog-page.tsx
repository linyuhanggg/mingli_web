import { notFound } from "next/navigation";

import { AdminCatalogSurface } from "@/components/admin-catalog-surface";
import { AdminCommerceSurface } from "@/components/admin-commerce-surface";
import { AdminCmsSurface } from "@/components/admin-cms-surface";
import { AdminDataRightsSurface } from "@/components/admin-data-rights-surface";
import { AdminReconciliationSurface } from "@/components/admin-reconciliation-surface";
import { AdminNotificationsSurface } from "@/components/admin-notifications-surface";
import { AdminReadingJobsSurface } from "@/components/admin-reading-jobs-surface";
import { AdminReadingDetailSurface } from "@/components/admin-reading-detail-surface";
import { AdminReadingsSurface } from "@/components/admin-readings-surface";
import { AdminRuntimeSurface } from "@/components/admin-runtime-surface";
import { AdminModelProfilesSurface } from "@/components/admin-model-profiles-surface";
import { AdminCapabilitiesSurface } from "@/components/admin-capabilities-surface";
import { AdminVerificationsSurface } from "@/components/admin-verifications-surface";
import { AdminAuditSurface } from "@/components/admin-audit-surface";
import { AdminHealthSurface } from "@/components/admin-health-surface";
import { AdminIdentitySurface } from "@/components/admin-identity-surface";
import { AdminEntitlementsSurface } from "@/components/admin-entitlements-surface";
import { AdminReferralsSurface } from "@/components/admin-referrals-surface";
import { AdminSessionsSurface } from "@/components/admin-sessions-surface";
import { AdminStaffSurface } from "@/components/admin-staff-surface";
import { AdminSettingsSurface } from "@/components/admin-settings-surface";
import { AdminSupportCasesSurface } from "@/components/admin-support-cases-surface";
import { AdminAppealsSurface } from "@/components/admin-appeals-surface";
import { AdminShell } from "@/components/admin-shell";
import { buildLiveAdminCatalogViewModel } from "@/lib/admin-catalog";
import { resolveAdminRoute } from "@/lib/admin-route-catalog";

export function AdminCatalogPage({ pathname }: { pathname: string }) {
  const route = resolveAdminRoute(pathname);
  if (!route) notFound();
  const detailId = pathname.split("?", 1)[0].split("/").filter(Boolean).at(-1);

  return (
    <AdminShell title={route.label} duty={route.duty}>
      {route.path === "/reconciliation" ? (
        <AdminReconciliationSurface />
      ) : route.path === "/orders" ? (
        <AdminCommerceSurface kind="orders" />
      ) : route.path === "/payments" ? (
        <AdminCommerceSurface kind="payments" />
      ) : route.path === "/refunds" ? (
        <AdminCommerceSurface kind="refunds" />
      ) : route.path === "/data-rights" ? (
        <AdminDataRightsSurface />
      ) : route.path === "/support-cases" ? (
        <AdminSupportCasesSurface />
      ) : route.path === "/appeals" ? (
        <AdminAppealsSurface />
      ) : route.path === "/cms/pages" ? (
        <AdminCmsSurface
          title="CMS 页面"
          prefixes={["home.", "page.", "notice", "seo."]}
        />
      ) : route.path === "/cms/daily" ? (
        <AdminCmsSurface title="CMS 每日" prefix="daily" />
      ) : route.path === "/cms/tools" ? (
        <AdminCmsSurface title="CMS 工具" prefix="tools" />
      ) : route.path === "/cms/library" ? (
        <AdminCmsSurface title="CMS 知识" prefix="library" />
      ) : route.path === "/cms/help" ? (
        <AdminCmsSurface title="CMS 帮助" prefix="faq" />
      ) : route.path === "/cms/policies" ? (
        <AdminCmsSurface title="CMS 政策" prefix="policy" />
      ) : route.path === "/reading-jobs" ? (
        <AdminReadingJobsSurface />
      ) : route.path === "/charts" ? (
        <AdminReadingsSurface title="盘面" />
      ) : route.path === "/readings" ? (
        <AdminReadingsSurface title="报告" />
      ) : route.path === "/readings/[id]" ? (
        <AdminReadingDetailSurface readingVersionId={detailId ?? ""} />
      ) : route.path === "/verifications" ? (
        <AdminVerificationsSurface />
      ) : route.path === "/runtime" ? (
        <AdminRuntimeSurface />
      ) : route.path === "/capabilities" ? (
        <AdminCapabilitiesSurface />
      ) : route.path === "/model-profiles" ? (
        <AdminModelProfilesSurface />
      ) : route.path === "/users" ? (
        <AdminIdentitySurface kind="users" />
      ) : route.path === "/users/[id]" ? (
        <AdminIdentitySurface kind="user-detail" id={detailId} />
      ) : route.path === "/subjects" ? (
        <AdminIdentitySurface kind="subjects" />
      ) : route.path === "/subjects/[id]" ? (
        <AdminIdentitySurface kind="subject-detail" id={detailId} />
      ) : route.path === "/entitlements" ? (
        <AdminEntitlementsSurface />
      ) : route.path === "/referrals" ? (
        <AdminReferralsSurface />
      ) : route.path === "/referrals/[id]" ? (
        <AdminReferralsSurface campaignId={detailId} />
      ) : route.path === "/notifications" ? (
        <AdminNotificationsSurface />
      ) : route.path === "/audit" ? (
        <AdminAuditSurface />
      ) : route.path === "/sessions" ? (
        <AdminSessionsSurface />
      ) : route.path === "/staff" ? (
        <AdminStaffSurface />
      ) : route.path === "/settings" ? (
        <AdminSettingsSurface />
      ) : route.path === "/health" ? (
        <AdminHealthSurface />
      ) : (
        <AdminCatalogSurface model={buildLiveAdminCatalogViewModel(route, pathname)} />
      )}
    </AdminShell>
  );
}
