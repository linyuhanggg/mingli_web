import { BookOpenCheck, LockKeyhole } from "lucide-react";
import Link from "next/link";

import styles from "@/components/app-surface.module.css";
import { StatusPanel } from "@/components/status-panel";


export default function ReadingDetailPage() {
  return (
    <div className={styles.page}>
      <div className={styles.readingLayout}>
        <article className={styles.readingBody}>
          <header className={styles.readingHeader}>
            <span className={styles.stateTag} data-state="success">结构示例 · 非真实交付</span>
            <h1>一份解读应当怎样被阅读。</h1>
            <p>本页只展示 Accepted 正文的组件顺序和状态表达，不包含真实盘面、运势、卦象、古籍命中或个人资料。</p>
          </header>

          <section className={styles.readingSection} aria-labelledby="reading-conclusion">
            <span className={styles.sectionIndex}>01</span>
            <div>
              <h2 id="reading-conclusion">先给结论</h2>
              <p>正式正文会先说明本次问题范围内的判断，并明确适用时间、条件和不能承诺的部分；示例页不生成任何结论。</p>
            </div>
          </section>
          <section className={styles.readingSection} aria-labelledby="reading-reason">
            <span className={styles.sectionIndex}>02</span>
            <div>
              <h2 id="reading-reason">再说明成立原因</h2>
              <p>每个关键判断都必须能回指本次不可变 Fact Brief。模型不能自行算盘，也不能把措辞流畅当成事实依据。</p>
              <ul className={styles.evidenceList}>
                <li><strong>事实引用位置</strong><span>正式内容会显示可读依据；内部 Provider、规则 ID 与 prompt 不对外泄露。</span></li>
                <li><strong>证据命中状态</strong><span>古籍只有实际命中且能定位时才展示。</span></li>
              </ul>
            </div>
          </section>
          <section className={styles.readingSection} aria-labelledby="reading-boundary">
            <span className={styles.sectionIndex}>03</span>
            <div>
              <h2 id="reading-boundary">边界与不确定性</h2>
              <p>资料口径、时间范围与高风险专业边界和正文一起出现，不依靠脚注掩藏。命理解读不替代医疗、法律、投资或其他专业意见。</p>
            </div>
          </section>
          <section className={styles.readingSection} aria-labelledby="reading-check">
            <span className={styles.sectionIndex}>04</span>
            <div>
              <h2 id="reading-check">三条现实核对</h2>
              <p>正式解读会列出三条可回答的现实核对；你的反馈独立保存，不能覆盖原盘与已接纳正文。</p>
              <ul className={styles.verificationList}>
                <li><strong>核对条目位置一</strong><span>符合 / 部分符合 / 不符合 / 暂时不知道</span></li>
                <li><strong>核对条目位置二</strong><span>反馈后若需调整表达，会产生新的解读版本。</span></li>
                <li><strong>核对条目位置三</strong><span>这里不使用虚构事实填充演示。</span></li>
              </ul>
            </div>
          </section>
          <div className={styles.actionRow}>
            <Link className={styles.secondaryButton} href="/app/readings">返回历史与状态</Link>
          </div>
        </article>

        <aside className={`${styles.rail} ${styles.evidenceRail}`} aria-labelledby="evidence-rail-title">
          <h2 id="evidence-rail-title">依据与交付</h2>
          <p><BookOpenCheck aria-hidden="true" size={16} /> 侧栏只展示本次真正命中的来源与版本信息。</p>
          <div className={styles.sourceEmpty}>本结构示例没有古籍命中。零命中保持零，不生成伪出处。</div>
          <StatusPanel
            state="success"
            title="已交付状态示例"
            description="只有 Accepted Copy 已落库且交付完成时，真实页面才会显示这个状态。"
          />
          <p><LockKeyhole aria-hidden="true" size={16} /> 正式报告仅在当前授权下读取。</p>
        </aside>
      </div>
    </div>
  );
}
