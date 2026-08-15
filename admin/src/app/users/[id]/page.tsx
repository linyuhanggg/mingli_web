import { AdminCatalogPage } from "@/components/admin-catalog-page";

export default async function UserDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AdminCatalogPage pathname={`/users/${id}`} />;
}
