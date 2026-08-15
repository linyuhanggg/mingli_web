import type { Metadata } from "next";

import { InviteSurface } from "@/components/surfaces/invite-surface";

export const metadata: Metadata = { title: "邀请链接", description: "查看邀请活动规则和状态。" };

export default async function InvitePage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  return <InviteSurface code={code} />;
}
