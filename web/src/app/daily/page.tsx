import type { Metadata } from "next";

import { DailyPageView } from "@/components/daily-page";

export const metadata: Metadata = { title: "每日", description: "只展示当天已发布的内容" };

export default function DailyPage() {
  return <DailyPageView />;
}
