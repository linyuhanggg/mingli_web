import type { Metadata } from "next";
import Link from "next/link";

import { RegistrationForm } from "@/components/registration-form";
import { SecondaryStatus } from "@/components/surfaces/secondary-status";
import { SecondarySurfaceFrame } from "@/components/surfaces/secondary-surface-frame";
import styles from "@/components/surfaces/secondary-surfaces.module.css";

export const metadata: Metadata = { title: "注册", description: "注册命理工具账号。" };

export default function RegisterPage() {
  return (
    <SecondarySurfaceFrame
      eyebrow="注册"
      intro="先验证手机或邮箱，再设置密码并分别记录隐私政策与服务条款的当前版本。"
      title="注册按验证、设密码、同意政策推进。"
    >
      <div className={styles.authGrid}>
        <RegistrationForm />
        <aside aria-label="注册状态与其他入口" className={styles.authAside}>
          <SecondaryStatus
            description="OTP 核验后才建立身份；政策版本以服务端收到的事实为准。"
            state="need-login"
            title="需要验证身份"
          />
          <nav aria-label="其他认证入口">
            <ul className={styles.linkList}>
              <li><Link href="/auth/login">返回登录</Link></li>
              <li><Link href="/auth/recover">找回账号</Link></li>
              <li><Link href="/privacy">查看隐私政策</Link></li>
              <li><Link href="/terms">查看服务条款</Link></li>
            </ul>
          </nav>
        </aside>
      </div>
    </SecondarySurfaceFrame>
  );
}
