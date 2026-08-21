import type { Metadata } from "next";

import { AuthShell } from "@/components/auth-shell";
import { PasswordSetForm } from "@/components/password-set-form";

export const metadata: Metadata = { title: "设置密码", description: "为当前账户设置密码。" };

export default function AuthSetPasswordPage() {
  return (
    <AuthShell
      intro="为当前账户设置密码。"
      links={[
        { href: "/auth/login", label: "返回登录" },
        { href: "/auth/recover", label: "找回账号" },
      ]}
      title="设置密码"
    >
      <PasswordSetForm />
    </AuthShell>
  );
}
