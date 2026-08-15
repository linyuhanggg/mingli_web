import { AdminCatalogPage } from "@/components/admin-catalog-page";

export default async function ReferralDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AdminCatalogPage pathname={`/referrals/${id}`} />;
}
