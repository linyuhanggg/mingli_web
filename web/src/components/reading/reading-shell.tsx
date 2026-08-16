import { ChevronDown, Download, LockKeyhole, MessageSquareText, Share2 } from "lucide-react";

import { Status } from "@/components/ui/status";
import type { ProductDefinition } from "@/products/catalog";

import styles from "./reading-shell.module.css";

const sectionLinks = [
  ["judgements", "主题判断"],
  ["evidence", "依据"],
  ["boundary", "边界"],
  ["verification", "现实核对"],
  ["correction", "资料纠正"],
  ["follow-up", "追问"],
] as const;

export function ReadingShell({ product }: { product: ProductDefinition }) {
  const sectionId = (name: string) => `${product.id}-reading-${name}`;

  return (
    <article className={styles.reading} aria-labelledby={`${product.id}-reading-title`}>
      <header>
        <h2 id={`${product.id}-reading-title`}>阅读与报告</h2>
        <p>报告是一张连续阅读面；盘面事实、解释与适用边界分开呈现。</p>
      </header>

      <section id={sectionId("summary")}>
        <h3>资料与盘面摘要</h3>
        <p className={styles.placeholderText}>真实盘面生成后，这里只复述已确认资料、时间口径与确定性事实。</p>
      </section>

      <section id={sectionId("answer")}>
        <h3>一句话回答</h3>
        <Status state="unavailable" title="还没有可用回答" description="没有真实盘面时不生成解释、结论或深读 Offer。" />
      </section>

      <nav className={styles.sectionNav} aria-label="报告主题导航">
        {sectionLinks.map(([id, label]) => <a href={`#${sectionId(id)}`} key={id}>{label}</a>)}
      </nav>

      <section id={sectionId("judgements")}>
        <h3>原子判断卡</h3>
        <p className={styles.placeholderText}>每条判断将独立说明结论、条件和适用时间，不把多条结论揉成一段长文。</p>
      </section>

      <section id={sectionId("evidence")}>
        <h3>依据抽屉</h3>
        <button className={styles.disclosure} disabled type="button"><ChevronDown aria-hidden="true" size={17} /> 盘面依据将在结果就绪后展开</button>
      </section>

      <section id={sectionId("boundary")}>
        <h3>适用边界</h3>
        <p className={styles.placeholderText}>只解释当前资料、版本、术数与时间范围；没有来源命中时不会伪造引文。</p>
      </section>

      <section id={sectionId("verification")}>
        <h3>逐条现实核对</h3>
        <p className={styles.placeholderText}>核对只追加 VerificationEvent，不修改盘面、不改变判断权重，也不覆盖已交付报告。</p>
      </section>

      <section id={sectionId("correction")}>
        <h3>资料纠正</h3>
        <p className={styles.placeholderText}>资料纠正会先展示差异，再创建新的资料版本、盘面和报告；它与现实核对是两件事。</p>
      </section>

      <section id={sectionId("follow-up")}>
        <h3>追问</h3>
        <div className={styles.lockedActions}>
          <LockKeyhole aria-hidden="true" size={19} />
          <p>报告交付后才能在同一任务根内追问；越界问题会明确要求重新起盘。</p>
          <button disabled type="button"><MessageSquareText aria-hidden="true" size={16} /> 开始追问</button>
        </div>
      </section>

      <section id={sectionId("delivery")}>
        <h3>导出、分享与版本</h3>
        <p className={styles.placeholderText}>导出与分享只使用允许的报告内容；见相分享永不包含原图或衍生标注图。</p>
        <div className={styles.deliveryActions}>
          <button disabled type="button"><Download aria-hidden="true" size={16} /> 导出报告</button>
          <button disabled type="button"><Share2 aria-hidden="true" size={16} /> 创建分享</button>
          <span>报告版本：等待交付</span>
        </div>
      </section>
    </article>
  );
}
