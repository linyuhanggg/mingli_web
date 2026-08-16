import type { StaffRole } from "@/lib/api";

export type AdminStaffStatus = "active" | "suspended";

export type AdminStaff = {
  id: string;
  email: string;
  display_name: string;
  role: StaffRole;
  status: AdminStaffStatus;
  created_at: string;
  last_login_at: string | null;
  unrevoked_session_count: number;
};

export type AdminStaffResponse = {
  staff: readonly AdminStaff[];
};
