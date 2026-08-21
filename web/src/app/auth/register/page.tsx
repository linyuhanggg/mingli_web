import type { Metadata } from "next";

import { AuthShell } from "@/components/auth-shell";
import { RegistrationForm } from "@/components/registration-form";

export const metadata: Metadata = { title: "注册", description: "注册命理工具账号。" };

export default function RegisterPage() {
  return (
    <AuthShell
      intro="先验证手机或邮箱，再设密码并同意政策。"
      links={[
        { href: "/auth/login", label: "返回登录" },
        { href: "/auth/recover", label: "找回账号" },
      ]}
      title="注册"
    >
      <RegistrationForm />
    </AuthShell>
  );
}
