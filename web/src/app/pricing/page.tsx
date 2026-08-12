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
      intro="测试期说明：公网预览入口无 TLS、无真实支付。付费向解读（今日/本周/六爻）仅运营开通，不会产生扣款；正式商户接入前价格只作展示。"
    >
      <section className={styles.grid3} aria-label="商品列表">
        <article className={styles.card}>
          <h2>免费</h2>
          <p className={styles.price}>¥0</p>
          <ul>
            <li>一个本人受测档案与确定性八字排盘</li>
            <li>有限白话概览与 3 条现实核对</li>
            <li>测试期可自助使用 Preview；付费向能力需运营开通</li>
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
            <li>当前绑定一个事业或工作问题、卦象、方式与起卦时刻</li>
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
        title="测试期：无在线购买，付费轨仅运营开通"
        description="当前不开放自动续费、代币余额、充值钱包或永久无限 AI。联调/dogfood 环境可能使用真实邮箱 OTP 与模型，但仍无微信支付/支付宝；数据可能被按人删除或在测试窗口结束后清空。按钮点击不会被写成已付款。"
      />
    </EditorialPage>
  );
}
