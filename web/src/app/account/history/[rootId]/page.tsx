import type { Metadata } from "next";

import { AccountHistorySurface } from "@/components/surfaces/account-history-surface";

export const metadata: Metadata = {
  title: "历史详情",
  description: "查看一份任务的版本与报告历史。",
};

export default async function AccountHistoryDetailPage({
  params,
}: {
  params: Promise<{ rootId: string }>;
}) {
  const { rootId } = await params;
  return <AccountHistorySurface readingId={rootId} />;
}
