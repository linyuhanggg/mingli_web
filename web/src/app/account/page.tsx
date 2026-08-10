import { Database, KeyRound, Mail, ReceiptText } from "lucide-react";

import { AppPageHeader } from "@/components/app-page-header";
import AccountSessionControl from "@/components/account-session-control";
import styles from "@/components/app-surface.module.css";
import { OtpForm } from "@/components/otp-form";


export default function AccountPage() {
  return (
    <main id="main-content" tabIndex={-1} className={styles.page}>
      <AppPageHeader
        title="邮箱是你的默认登录入口。"
        description="首次邮箱验证自动注册账户，已有邮箱直接登录。验证码会发送到你的邮箱，几分钟内有效；仅开发/测试环境才可能额外显示调试码。手机号登录稍后开放。"
        meta={
          <>
            <span><Mail aria-hidden="true" size={15} /> 邮箱验证为主</span>
            <span><KeyRound aria-hidden="true" size={15} /> 设备会话可撤销</span>
          </>
        }
      />

      <div className={styles.dashboard}>
        <section className={styles.paper} aria-labelledby="login-title">
          <div className={styles.sectionHeader}>
            <div>
              <h2 id="login-title">验证码登录</h2>
              <p>验证码发送到邮箱后几分钟内有效；验证成功即建立当前设备会话。</p>
            </div>
          </div>
          <OtpForm />
        </section>

        <aside className={styles.rail} aria-labelledby="account-boundary-title">
          <h2 id="account-boundary-title">账户边界</h2>
          <p>登录成功只代表设备会话建立，不代表支付、模型或其他能力已经开通。</p>
          <p className={styles.railNote}>
            游客草稿认领：服务端接通后一次性、幂等完成；跨设备历史：需当前账号登录并完成授权；高风险操作：换绑、导出和删除需近期重新验证。
          </p>
        </aside>
      </div>

      <section className={styles.paper} aria-labelledby="account-tools-title">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="account-tools-title">设备、订单与数据权利</h2>
            <p>入口已经预留，只有后端返回真实账户状态后才会开放具体操作。</p>
          </div>
        </div>
        <div className={styles.accountGrid}>
          <AccountSessionControl />
          <div className={styles.gateNote}>
            <p>
              订单与退款：真实支付尚未开放，不展示虚构订单、渠道或已付款状态；导出数据：需服务端授权与短时下载地址；删除与撤回：账号删除、档案删除与撤回非必要同意都需服务端审计流程。
            </p>
          </div>
        </div>
        <div className={styles.metaLine}>
          <span><ReceiptText aria-hidden="true" size={15} /> 财务状态不在前端伪造</span>
          <span><Database aria-hidden="true" size={15} /> 正式资料不进 localStorage</span>
        </div>
      </section>
    </main>
  );
}
