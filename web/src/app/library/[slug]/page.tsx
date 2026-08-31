import type { Metadata } from "next";

import { RetiredPublicSurface } from "@/components/retired-public-surface";

// Migration note: LibraryArticleView is intentionally replaced by the shared retired surface.
export const metadata: Metadata = {
  title: "知识内容已下线",
  description: "原知识内容公开深链已下线，请前往人生 K 线。",
  robots: { index: false, follow: true },
};

export default async function LibraryArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  await params;
  return <RetiredPublicSurface title="知识内容已下线" />;
}
