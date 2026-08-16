import type { Metadata } from "next";

import { AccountNotificationsSurface } from "@/components/surfaces/account-notifications-surface";

export const metadata: Metadata = { title: "通知", description: "查看任务、账号和订单通知。" };

export default function AccountNotificationsPage() {
  return <AccountNotificationsSurface />;
}
