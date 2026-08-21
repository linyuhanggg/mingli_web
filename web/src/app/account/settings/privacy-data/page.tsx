import type { Metadata } from "next";

import { AccountDataRightsSurface } from "@/components/surfaces/account-data-rights-surface";

export const metadata: Metadata = { title: "隐私与数据", description: "导出资料，或申请注销账号。" };

export default function AccountPrivacyDataPage() {
  return <AccountDataRightsSurface title="隐私与数据" />;
}
