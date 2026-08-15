export type AdminReferralCampaign = {
  id: string;
  campaign_key: string;
  version: string;
  state: string;
  starts_at: string;
  ends_at: string | null;
  total_limit: number | null;
  per_inviter_limit: number;
  reward_quantity: number;
  reward_window_seconds: number;
  code_count: number;
  temporary_attribution_count: number;
  attribution_count: number;
  reservation_count: number;
  created_at: string;
};

export type AdminReferralsResponse = { campaigns: readonly AdminReferralCampaign[] };

export type AdminReferralCode = {
  id: string;
  campaign_version_id: string;
  code: string;
  inviter_user_id: string;
  status: string;
  created_at: string;
};

export type AdminReferralAttribution = {
  id: string;
  campaign_version_id: string;
  code_id: string;
  referred_user_id: string;
  inviter_user_id: string;
  locked_at: string;
  status: string;
};

export type AdminReferralReward = {
  id: string;
  campaign_version_id: string;
  attribution_id: string;
  referred_user_id: string;
  inviter_user_id: string;
  product_version_id: string | null;
  payment_attempt_id: string | null;
  quantity: number;
  status: string;
  reserved_at: string;
  committed_at: string | null;
};

export type AdminReferralRewardSlot = {
  id: string;
  campaign_version_id: string;
  product_version_id: string;
  slot_key: string;
  enabled: boolean;
  total_limit: number;
  quantity: number;
  created_at: string;
};

export type AdminReferralResponse = {
  campaign: AdminReferralCampaign;
  codes: readonly AdminReferralCode[];
  attributions: readonly AdminReferralAttribution[];
  slots: readonly AdminReferralRewardSlot[];
  rewards: readonly AdminReferralReward[];
};
