import type { Metadata } from "next";

import { AuthShell } from "@/components/auth-shell";
import { SharedReadingSurface } from "@/components/shared-reading-surface";

export const metadata: Metadata = { title: "分享", description: "查看这份已确认的分享。" };

export default async function SharePage({
  params,
}: {
  params: Promise<{ shareId: string }>;
}) {
  const { shareId } = await params;
  return (
    <AuthShell intro="查看这份已确认的分享。" links={[]} title="分享">
      <SharedReadingSurface token={shareId} />
    </AuthShell>
  );
}
