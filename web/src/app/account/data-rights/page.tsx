import type { Metadata } from "next";

import { AccountDataRightsSurface } from "@/components/surfaces/account-data-rights-surface";

export const metadata: Metadata = { title: "数据权利", description: "导出资料，或申请注销账号。" };

export default function AccountDataRightsPage() {
  return <AccountDataRightsSurface title="数据权利" />;
}
