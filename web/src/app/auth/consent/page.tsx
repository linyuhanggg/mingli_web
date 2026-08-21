import type { Metadata } from "next";

import { AuthShell } from "@/components/auth-shell";
import { ConsentForm } from "@/components/consent-form";

export const metadata: Metadata = { title: "政策同意", description: "重新确认当前政策。" };

export default function AuthConsentPage() {
  return (
    <AuthShell
      intro="请分别确认隐私政策和服务条款。"
      links={[
        { href: "/auth/login", label: "返回登录" },
        { href: "/privacy", label: "隐私政策" },
        { href: "/terms", label: "服务条款" },
      ]}
      title="政策同意"
    >
      <ConsentForm />
    </AuthShell>
  );
}
