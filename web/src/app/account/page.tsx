import { Database, KeyRound, ReceiptText, Smartphone } from "lucide-react";

import styles from "@/components/app-surface.module.css";
import { OtpForm } from "@/components/otp-form";
import { StatusPanel } from "@/components/status-panel";


export default function AccountPage() {
  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1>登录身份只是入口，账户才保存你的档案。</h1>
        <div>
          <p>手机号与邮箱验证码都可以建立可撤销设备会话；它们不是业务 User 本身。当前使用本地 Fake Adapter，不会发送真实短信或邮件。</p>
          <div className={styles.metaLine}>
            <span><KeyRound aria-hidden="true" size={15} /> 默认无密码</span>
            <span><Smartphone aria-hidden="true" size={15} /> 设备会话可撤销</span>
          </div>
        </div>
      </header>

      <div className={styles.dashboard}>
        <section className={styles.paper} aria-labelledby="login-title">
          <div className={styles.sectionHeader}>
            <div>
              <h2 id="login-title">验证码登录</h2>
              <p>验证成功后，无账户就创建，有账户就登录，不再拆成两个入口。</p>
            </div>
          </div>
          <OtpForm />
        </section>

        <aside className={styles.rail} aria-labelledby="account-boundary-title">
          <h2 id="account-boundary-title">账户边界</h2>
          <p>登录成功只代表设备会话建立，不代表支付、模型或其他能力已经开通。</p>
          <ul className={styles.activityList}>
            <li><strong>游客草稿认领</strong><span>服务端接通后一次性、幂等完成</span></li>
            <li><strong>跨设备历史</strong><span>需要当前 User 的授权关系</span></li>
            <li><strong>高风险操作</strong><span>换绑、导出和删除需近期重新验证</span></li>
          </ul>
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
          <StatusPanel state="disabled" title="身份与设备" description="登录并取得当前 User 后，才能查看已绑定身份与撤销其他设备会话。" />
          <StatusPanel state="disabled" title="订单与退款" description="真实支付尚未开放；这里不会展示虚构订单、渠道或已付款状态。" />
          <StatusPanel state="disabled" title="导出数据" description="导出任务需服务端授权与短时下载地址，当前不可用。" />
          <StatusPanel state="disabled" title="删除与撤回" description="账号删除、档案删除与撤回非必要同意都需服务端审计流程。" />
        </div>
        <div className={styles.metaLine}>
          <span><ReceiptText aria-hidden="true" size={15} /> 财务状态不在前端伪造</span>
          <span><Database aria-hidden="true" size={15} /> 正式资料不进 localStorage</span>
        </div>
      </section>
    </div>
  );
}
