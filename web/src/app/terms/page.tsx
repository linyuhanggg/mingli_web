import type { Metadata } from "next";

import { EditorialPage, editorialStyles as styles } from "@/components/editorial-page";


export const metadata: Metadata = {
  title: "服务条款（开发期说明）",
  description: "服务范围、AI 标识、付费交付和使用边界。",
};

export default function TermsPage() {
  return (
    <EditorialPage
      eyebrow="Terms · Development notice"
      title="说清楚能交付什么，也说清楚不能承诺什么。"
      intro="本页是进入正式法律审阅前的产品合同草案。运营主体、争议处理、退款细则与生效日期必须在上线 Gate 中由真实资料替换。"
    >
      <section className={styles.grid2}>
        <article className={styles.card}>
          <h2>服务性质</h2>
          <p>本产品提供传统文化参考、个人记录和现实核对工具，不保证某个未来事件必然发生。</p>
        </article>
        <article className={styles.card}>
          <h2>AI 标识</h2>
          <p>自然语言报告会标明 AI 生成或辅助生成；模型只处理经过约束的事实简报。</p>
        </article>
        <article className={styles.card}>
          <h2>专业边界</h2>
          <p>内容不能替代医疗、法律、投资、心理、婚姻或其他需要持证专业人士承担责任的意见。</p>
        </article>
        <article className={styles.card}>
          <h2>付费与交付</h2>
          <p>订单绑定具体商品版本和购买目标。支付成功、权益授予、报告生成和正文交付是不同状态。</p>
        </article>
      </section>
      <section className={styles.prose}>
        <h2>禁止用途</h2>
        <ul>
          <li>利用服务骚扰、歧视、威胁或推断他人的敏感信息；</li>
          <li>把内容包装成诊断、保证收益、改运消灾或确定结果承诺；</li>
          <li>绕过访问控制、批量枚举报告或攻击 OTP 与支付接口。</li>
        </ul>
      </section>
    </EditorialPage>
  );
}
