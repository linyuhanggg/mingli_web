import Link from "next/link";

import { ConsentForm } from "@/components/consent-form";
import { SecondaryStatus } from "@/components/surfaces/secondary-status";
import { SecondarySurfaceFrame } from "@/components/surfaces/secondary-surface-frame";
import styles from "@/components/surfaces/secondary-surfaces.module.css";

export default function AuthConsentPage() {
  return (
    <SecondarySurfaceFrame
      eyebrow="政策同意"
      intro="每次同意都绑定具体政策版本和确认上下文；当前页面用于登录后的重新确认。"
      title="每次同意都绑定具体政策版本。"
    >
      <div className={styles.authGrid}>
        <ConsentForm />
        <aside aria-label="政策状态与其他入口" className={styles.authAside}>
          <SecondaryStatus
            description="隐私政策与服务条款会作为两条独立事实保存，未登录或服务失败时不会显示已完成。"
            state="need-login"
            title="需要已验证会话"
          />
          <nav aria-label="其他认证入口">
            <ul className={styles.linkList}>
              <li><Link href="/auth/login">返回登录</Link></li>
              <li><Link href="/privacy">查看隐私政策</Link></li>
              <li><Link href="/terms">查看服务条款</Link></li>
            </ul>
          </nav>
        </aside>
      </div>
    </SecondarySurfaceFrame>
  );
}
