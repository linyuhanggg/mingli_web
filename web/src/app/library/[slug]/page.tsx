import { PublicContentSurface } from "@/components/surfaces";
import { publicContentSurfaces } from "@/lib/secondary-surfaces";

export default async function LibraryArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return (
    <PublicContentSurface
      contentSource={{ kind: "item", contentKey: `library.${slug}` }}
      surface={publicContentSurfaces.article}
    />
  );
}
