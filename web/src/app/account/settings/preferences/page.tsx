import type { Metadata } from "next";

import { AccountSessionBoundary } from "@/components/account-session-context";
import { AccountSectionShell } from "@/components/account-section-shell";
import NotificationPreferencesForm from "@/components/notification-preferences-form";

export const metadata: Metadata = { title: "通知偏好", description: "站内通知默认开启；邮件和短信由你分别控制。" };

export default function AccountPreferencesPage() {
  return (
    <AccountSessionBoundary>
      <AccountSectionShell intro="站内通知默认开启；邮件和短信由你分别控制。" title="通知偏好">
        <NotificationPreferencesForm />
      </AccountSectionShell>
    </AccountSessionBoundary>
  );
}
