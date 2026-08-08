import type { Metadata } from "next";

import { EditorialPage, editorialStyles as styles } from "@/components/editorial-page";


export const metadata: Metadata = {
  title: "帮助与支持",
  description: "账号、付款、报告、数据权利和人工售后入口。",
};

export default function SupportPage() {
  return (
    <EditorialPage
      eyebrow="Support"
      title="事情卡住时，先看状态，再找对应入口。"
      intro="Phase 1 先提供清楚的帮助边界。真实工单渠道和服务时段会在运营主体确认后补充，不展示虚构联系方式。"
    >
      <section className={styles.grid2}>
        <article className={styles.card}>
          <h2>账号与登录</h2>
          <p>使用手机号或邮箱验证码。验证码验证成功后自动登录，不需要另设注册密码。</p>
        </article>
        <article className={styles.card}>
          <h2>付款与退款</h2>
          <p>以服务端验签通知或主动查单为准。回跳页面只表示正在确认，不代表真实到账。</p>
        </article>
        <article className={styles.card}>
          <h2>报告与追问</h2>
          <p>账户中的状态会区分待付款、已付款、生成中、待人工检查和已交付。</p>
        </article>
        <article className={styles.card}>
          <h2>导出与删除</h2>
          <p>正式账户区将提供数据导出、档案删除、设备撤销与账号删除申请。</p>
        </article>
      </section>
      <p className={styles.notice}>
        人工支持入口将在客服主体、服务时间与隐私处理流程确认后启用。紧急医疗、法律或人身安全问题请直接联系相应专业机构。
      </p>
    </EditorialPage>
  );
}
