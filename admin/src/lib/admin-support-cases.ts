export type AdminSupportCaseCategory =
  | "account"
  | "delivery"
  | "billing"
  | "reading"
  | "referral"
  | "profile_correction"
  | "algorithm_review"
  | "after_sales"
  | "compensation"
  | "other";

export type AdminSupportCaseStatus = "open" | "in_review" | "resolved" | "rejected";

export type AdminSupportCase = {
  id: string;
  owner_user_id: string | null;
  subject_ref: string;
  category: AdminSupportCaseCategory;
  summary: string;
  status: AdminSupportCaseStatus;
  created_by_staff_user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminSupportCasesResponse = {
  cases: readonly AdminSupportCase[];
};
