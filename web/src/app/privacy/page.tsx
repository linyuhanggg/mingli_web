import type { Metadata } from "next";

import { EditorialPage, editorialStyles as styles } from "@/components/editorial-page";


export const metadata: Metadata = {
  title: "隐私政策（开发期说明）",
  description: "命理资料、登录身份、会话和模型数据的处理边界。",
};

export default function PrivacyPage() {
  return (
    <EditorialPage
      eyebrow="FateRadar · Privacy"
      title="个人资料只为这次明确任务服务。"
      intro="本页是 Phase 1 的产品与工程边界说明，不冒充已经过法律审阅的最终隐私政策。上线前会补齐真实主体、第三方清单、保存期限和联系渠道。"
    >
      <section className={styles.prose}>
        <h2>我们把哪些数据按高敏感业务数据保护</h2>
        <p>
          出生日期、时间、地点、性别、问题正文、联系方式、命理解读和核对反馈都会进入严格访问边界，即使单个字段未必落入同一法律分类。
        </p>
      </section>
      <section className={styles.grid2}>
        <article className={styles.card}>
          <h2>浏览器与会话</h2>
          <p>
            网站使用 HttpOnly Cookie 保存短期游客关系与可撤销设备会话。localStorage 不保存正式访问令牌、完整报告或长期出生资料。
          </p>
        </article>
        <article className={styles.card}>
          <h2>模型最小化输入</h2>
          <p>默认只发送本次成稿需要的事实简报和问题，不发送手机号、邮箱、订单信息或无关账号资料。</p>
        </article>
        <article className={styles.card}>
          <h2>日志与监控</h2>
          <p>普通日志不记录 OTP、Cookie、完整出生资料、问题正文、报告或模型密钥。</p>
        </article>
        <article className={styles.card}>
          <h2>你的权利</h2>
          <p>正式账户区会提供访问、导出、更正与删除入口，并允许撤回非必要同意和撤销其他设备。</p>
        </article>
      </section>
      <p className={styles.notice}>
        测试期/联调预览：入口可能无 TLS；允许使用真实邮箱 OTP 与模型供应商，但支付仍为 Fake/未接入。
        你可请求按邮箱删除账户相关档案与解读；测试窗口结束默认清空测试库敏感数据。勿把本环境当作生产。
      </p>
    </EditorialPage>
  );
}
