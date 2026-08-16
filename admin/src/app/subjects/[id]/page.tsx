import { AdminCatalogPage } from "@/components/admin-catalog-page";

export default async function SubjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AdminCatalogPage pathname={`/subjects/${id}`} />;
}
