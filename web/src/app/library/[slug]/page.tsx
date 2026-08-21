import type { Metadata } from "next";

import { LibraryArticleView } from "@/components/library-page";

export const metadata: Metadata = { title: "知识内容", description: "只展示已发布的文章。" };

export default async function LibraryArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <LibraryArticleView slug={slug} />;
}
