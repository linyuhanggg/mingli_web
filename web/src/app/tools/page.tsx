import type { Metadata } from "next";

import { PublicContentSurface } from "@/components/surfaces";
import { publicContentSurfaces } from "@/lib/secondary-surfaces";

export const metadata: Metadata = { title: "工具", description: "命理辅助工具总览。" };

export default function ToolsPage() {
  return (
    <PublicContentSurface
      contentSource={{ kind: "index", prefix: "tools.", hrefBase: "/tools" }}
      surface={publicContentSurfaces.tools}
    />
  );
}
