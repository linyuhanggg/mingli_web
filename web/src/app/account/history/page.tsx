import type { Metadata } from "next";

import { AccountHistorySurface } from "@/components/surfaces/account-history-surface";

export const metadata: Metadata = { title: "历史", description: "查看你的任务和报告历史。" };

export default function AccountHistoryPage() {
  return <AccountHistorySurface />;
}
