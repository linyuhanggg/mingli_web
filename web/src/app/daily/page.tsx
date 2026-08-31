import type { Metadata } from "next";

import { RetiredPublicSurface } from "@/components/retired-public-surface";

// Migration note: DailyPageView is intentionally replaced by the shared retired surface.
export const metadata: Metadata = {
  title: "每日已下线",
  description: "原每日公开入口已下线，请前往人生 K 线。",
  robots: { index: false, follow: true },
};

export default function DailyPage() {
  return <RetiredPublicSurface title="每日已下线" />;
}
