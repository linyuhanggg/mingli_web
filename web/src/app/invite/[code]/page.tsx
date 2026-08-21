import type { Metadata } from "next";

import { AuthShell } from "@/components/auth-shell";
import { InviteSurface } from "@/components/surfaces/invite-surface";

export const metadata: Metadata = { title: "邀请", description: "查看这次邀请活动的状态。" };

export default async function InvitePage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  return (
    <AuthShell intro="查看这次邀请活动的状态。" links={[]} title="邀请">
      <InviteSurface code={code} />
    </AuthShell>
  );
}
