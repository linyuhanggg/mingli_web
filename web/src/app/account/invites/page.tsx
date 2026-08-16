import type { Metadata } from "next";

import { AccountReferralsSurface } from "@/components/surfaces/account-referrals-surface";

export const metadata: Metadata = { title: "邀请", description: "查看你的邀请活动进度。" };

export default function AccountInvitesPage() {
  return <AccountReferralsSurface />;
}
