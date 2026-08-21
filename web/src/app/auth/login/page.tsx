import type { Metadata } from "next";

import { AuthShell } from "@/components/auth-shell";
import { PasswordLoginForm } from "@/components/password-login-form";

export const metadata: Metadata = { title: "登录", description: "登录命理工具。" };

export default function LoginPage() {
  return (
    <AuthShell
      intro="登录后进入账户"
      links={[
        { href: "/auth/verify", label: "用验证码登录" },
        { href: "/auth/register", label: "注册" },
        { href: "/auth/recover", label: "找回账号" },
      ]}
      title="登录"
    >
      <PasswordLoginForm />
    </AuthShell>
  );
}
