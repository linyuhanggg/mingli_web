import type { Metadata } from "next";

import { EditorialPage, editorialStyles as styles } from "@/components/editorial-page";
import { StatusPanel } from "@/components/status-panel";


export const metadata: Metadata = {
  title: "价格与交付",
  description: "免费能力与两种单次命理解读的交付、追问期限和退款边界。",
};

export default function PricingPage() {
  return (
    <EditorialPage
      eyebrow="FateRadar · Pricing"
      title="每一次付款，都绑定一份明确结果。"
      intro="先免费建立信任，需要更完整的主题报告时再单次购买。当前在线支付尚未开放，不会产生真实扣款。"
    >
      <section className={styles.grid3} aria-label="商品列表">
        <article className={styles.card}>
          <h2>免费</h2>
          <p className={styles.price}>¥0</p>
          <ul>
            <li>一个本人受测档案与确定性八字排盘</li>
            <li>有限白话概览与 3 条现实核对</li>
            <li>今日/近七日摘要与六爻基础卦象</li>
          </ul>
        </article>
        <article className={styles.card}>
          <h2>个人命盘深度解读</h2>
          <p className={styles.price}>¥29.90</p>
          <ul>
            <li>绑定一个已经确认的档案版本</li>
            <li>已接纳报告永久查看</li>
            <li>7 天内 3 次同盘追问</li>
          </ul>
        </article>
        <article className={styles.card}>
          <h2>一事一问 · 六爻</h2>
          <p className={styles.price}>¥9.90</p>
          <ul>
            <li>绑定具体问题、卦象、方式与起卦时刻</li>
            <li>事件报告永久查看</li>
            <li>72 小时内 2 次同盘追问</li>
          </ul>
        </article>
      </section>
      <section className={styles.grid2}>
        <article className={styles.prose}>
          <h2>不是残缺文字解锁</h2>
          <p>
            免费概览与付费报告是两个独立解读根。购买前会展示购买目标、交付范围、金额、追问次数与期限，付款后不能偷换目标。
          </p>
        </article>
        <article className={styles.prose}>
          <h2>付款不等于已经交付</h2>
          <p>
            到账、权益授予、生成和正文交付分别记录。模型失败时不会核销未完成权益；退款按渠道确认结果追加冲正记录。
          </p>
        </article>
      </section>
      <StatusPanel
        state="disabled"
        title="在线购买暂未开放"
        description="当前不开放自动续费、代币余额、充值钱包或永久无限 AI。真实微信与支付宝支付须在商户能力获批并完成小额验收后另行启用，按钮点击不会被写成已付款。"
      />
    </EditorialPage>
  );
}
