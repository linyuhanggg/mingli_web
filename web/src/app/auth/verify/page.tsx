import type { Metadata } from "next";

import { AuthShell } from "@/components/auth-shell";
import { OtpForm } from "@/components/otp-form";

export const metadata: Metadata = { title: "验证身份", description: "用验证码登录命理工具。" };

export default function AuthVerifyPage() {
  return (
    <AuthShell
      intro="验证后进入账户"
      links={[
        { href: "/auth/login", label: "返回登录" },
        { href: "/auth/register", label: "注册" },
        { href: "/auth/recover", label: "找回账号" },
      ]}
      title="验证身份"
    >
      <OtpForm />
    </AuthShell>
  );
}
