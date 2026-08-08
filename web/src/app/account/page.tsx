import { OtpForm } from "@/components/otp-form";
import { privateShellStyles as styles } from "@/components/private-shell";


export default function AccountPage() {
  return (
    <section className={styles.panel}>
      <h1>验证码就是登录，不用再记一个密码。</h1>
      <p>
        当前使用本地 Fake Adapter 验证完整会话流程，不会发送真实短信或邮件。正式通道通过外部 Gate 后再替换适配器。
      </p>
      <OtpForm />
    </section>
  );
}
