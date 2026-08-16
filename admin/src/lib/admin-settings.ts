import type { StaffRole } from "@/lib/api";

export type AdminSettings = {
  environment: "local" | "test" | "staging" | "production";
  cookie_secure: boolean;
  otp_adapter: "fake" | "disabled" | "smtp";
  runtime_adapter: "fake" | "one-shot";
  admin_session_hours: number;
  dogfood_entitlement_gates_enabled: boolean;
  real_traffic_enabled: boolean;
  alert_sink_enabled: boolean;
};

export type AdminSettingsResponse = AdminSettings;

export type AdminSettingsRole = StaffRole;
