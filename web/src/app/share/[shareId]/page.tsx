import type { Metadata } from "next";

import { SharedReadingSurface } from "@/components/shared-reading-surface";

export const metadata: Metadata = { title: "分享报告", description: "查看受限时效的报告分享。" };

export default async function SharePage({
  params,
}: {
  params: Promise<{ shareId: string }>;
}) {
  const { shareId } = await params;
  return <SharedReadingSurface token={shareId} />;
}
