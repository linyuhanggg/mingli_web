import type { Metadata } from "next";

import { AuthShell } from "@/components/auth-shell";
import { PasswordRecoveryForm } from "@/components/password-recovery-form";

export const metadata: Metadata = { title: "找回账号", description: "找回命理工具账号。" };

export default function RecoverPage() {
  return (
    <AuthShell
      intro="用已验证的手机或邮箱重设密码。成功后其他已登录设备会退出。"
      note="不会因为找回请求创建新账号"
      links={[
        { href: "/auth/login", label: "返回登录" },
        { href: "/auth/register", label: "注册" },
      ]}
      title="找回账号"
    >
      <PasswordRecoveryForm />
    </AuthShell>
  );
}
