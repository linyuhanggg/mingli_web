import type { Metadata } from "next";

import { AccountSettingsSurface } from "@/components/surfaces/account-settings-surface";

export const metadata: Metadata = { title: "设置", description: "管理账号和隐私设置。" };

export default function AccountSettingsPage() {
  return <AccountSettingsSurface />;
}
