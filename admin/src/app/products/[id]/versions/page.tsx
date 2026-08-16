import { AdminCatalogPage } from "@/components/admin-catalog-page";

export default async function ProductVersionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AdminCatalogPage pathname={`/products/${id}/versions`} />;
}
