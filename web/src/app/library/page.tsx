import type { Metadata } from "next";

import { PublicContentSurface } from "@/components/surfaces";
import { publicContentSurfaces } from "@/lib/secondary-surfaces";

export const metadata: Metadata = { title: "知识内容", description: "公开文章与古籍来源索引。" };

export default function LibraryPage() {
  return (
    <PublicContentSurface
      contentSource={{ kind: "index", prefix: "library.", hrefBase: "/library" }}
      surface={publicContentSurfaces.library}
    />
  );
}
