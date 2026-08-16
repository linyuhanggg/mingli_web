import type { Metadata } from "next";

import { AccountDataRightsSurface } from "@/components/surfaces/account-data-rights-surface";

export const metadata: Metadata = { title: "数据权利", description: "管理资料导出、删除和账号权利。" };

export default function AccountDataRightsPage() {
  return <AccountDataRightsSurface />;
}
