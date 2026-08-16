import { AccountProfileDetailSurface } from "@/components/surfaces/account-profile-detail-surface";

export default async function AccountProfileDetailPage({
  params,
}: {
  params: Promise<{ profileId: string }>;
}) {
  const { profileId } = await params;
  return <AccountProfileDetailSurface profileId={profileId} />;
}
