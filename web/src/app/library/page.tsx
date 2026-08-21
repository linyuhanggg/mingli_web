import type { Metadata } from "next";

import { LibraryIndexView } from "@/components/library-page";

export const metadata: Metadata = { title: "知识内容", description: "只展示已发布的文章。" };

export default function LibraryPage() {
  return <LibraryIndexView />;
}
