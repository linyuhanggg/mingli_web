import type { Metadata } from "next";

import { EditorialPage, editorialStyles as styles } from "@/components/editorial-page";


export const metadata: Metadata = {
  title: "方法与边界",
  description: "FateRadar 如何先计算事实、再生成白话、校验后接纳和交付。",
};

export default function MethodologyPage() {
  return (
    <EditorialPage
      eyebrow="FateRadar · Methodology"
      title="先算再讲，证据和边界都能回看。"
      intro="命理核心、模型表达与产品交付各管一件事。换模型不会改盘，用户反馈也不会覆盖历史事实。"
    >
      <ol className={styles.pipeline} aria-label="标准解读链">
        {[
          "输入确认",
          "Profile Version",
          "prepare",
          "Fact Brief",
          "候选成稿",
          "校验",
          "complete",
          "Accepted",
        ].map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <section className={styles.grid3}>
        <article className={styles.card}>
          <h2>确定性命理层</h2>
          <p>规范化历法、时区、地点和口径，负责盘面事实、古籍证据、限制与连续状态。</p>
        </article>
        <article className={styles.card}>
          <h2>受约束表达层</h2>
          <p>模型不能自行算盘、补造证据或决定权益，只能在事实简报允许的范围内写成自然中文。</p>
        </article>
        <article className={styles.card}>
          <h2>产品交付层</h2>
          <p>负责账号、不可变版本、订单、权益、任务、报告、追问、隐私和访问授权。</p>
        </article>
      </section>
      <section className={styles.grid2}>
        <article className={styles.prose}>
          <h2>证据不靠模型补</h2>
          <p>
            每个事实声明必须回指 Fact Brief；古籍只有真正命中且能定位时才展示，零命中就保持零。
          </p>
        </article>
        <article className={styles.prose}>
          <h2>Accepted 后原样交付</h2>
          <p>
            候选稿先过结构、事实、隐私和内容安全合同，之后才交给核心 complete。已接纳正文不会被二次改写；更正会产生新的解读版本。
          </p>
        </article>
      </section>
      <p className={styles.notice}>
        命理解读用于传统文化参考和自我观察，不以“保证应验”替代现实证据，也不替代专业判断。
      </p>
    </EditorialPage>
  );
}
