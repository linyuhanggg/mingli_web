import type { Metadata } from "next";

import { PublicContentSurface } from "@/components/surfaces";
import { publicContentSurfaces } from "@/lib/secondary-surfaces";

export const metadata: Metadata = { title: "每日", description: "每日确定性信息与内容入口。" };

export default function DailyPage() {
  return (
    <PublicContentSurface
      contentSource={{ kind: "item", contentKey: "daily" }}
      surface={publicContentSurfaces.daily}
    />
  );
}
