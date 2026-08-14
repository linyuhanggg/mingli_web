import { ArrowRight, ArrowUpRight, BookOpen, CalendarDays, Wrench } from "lucide-react";

import { ButtonLink } from "@/components/button-link";
import { Container } from "@/components/container";
import { PublicCmsProjection } from "@/components/public-cms-projection";
import { PublicPageShell } from "@/components/public-page-shell";
import { getPublicCmsMetadata } from "@/lib/public-cms-metadata";
import {
  CROSS_PRODUCTS,
  NATAL_PRODUCTS,
  PRODUCT_CATALOG,
  type ProductDefinition,
} from "@/products/catalog";

import styles from "./home.module.css";

export async function generateMetadata() {
  return getPublicCmsMetadata("seo.home", {
    title: "十三术同根，五十五部古籍为证",
    description:
      "13 个术数体系 Provider、55 部古籍 reference pack、1328 条 evidence index 记录；先给确定性盘面事实，再谈解释与边界。",
  });
}

// DESIGN §6.3：首页事件入口固定为六爻、奇门、大六壬。
const EVENT_ENTRIES = [
  PRODUCT_CATALOG.liuyao,
  PRODUCT_CATALOG.qimen,
  PRODUCT_CATALOG.daliuren,
] as const;

// 命盘区梯度：主入口（白面强边）→ 标准卡 → 浅面卡。
const NATAL_TIERS = [styles.cardLead, "", styles.cardTail] as const;

// 合参卡的主理/参证边界一句话（DESIGN §8.3 / §8.4）。
const CROSS_BOUNDARIES: Partial<Record<ProductDefinition["id"], string>> = {
  hecan: "八字主理，紫微、七政参证；可带着具体问题进入（原多盘问答）。",
  wenshi: "六爻先行起卦，大六壬与奇门参证同一问题与时空。",
};

const auxiliary = [
  {
    href: "/daily",
    name: "每日",
    description: "当天与近阶段的可用时间摘要。",
    icon: CalendarDays,
  },
  {
    href: "/tools",
    name: "工具",
    description: "历法、时间与资料辅助工具。",
    icon: Wrench,
  },
  {
    href: "/library",
    name: "知识内容",
    description: "术数方法、术语与适用边界。",
    icon: BookOpen,
  },
] as const;

function TaskCard({ product, tier = "" }: { product: ProductDefinition; tier?: string }) {
  return (
    <a className={`${styles.card} ${tier}`} href={product.href}>
      <span className={styles.cardTop}>
        <span className={styles.cardName}>{product.name}</span>
        <ArrowUpRight aria-hidden="true" className={styles.cardIcon} size={16} strokeWidth={1.75} />
      </span>
      <span className={styles.cardSummary}>{product.summary}</span>
      <span className={styles.cardMeta}>{product.suitableFor}</span>
    </a>
  );
}

export default function HomePage() {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={styles.container}>
          <section aria-labelledby="home-hero" className={styles.hero}>
            <p className={styles.eyebrow}>命理推演</p>
            <h1 id="home-hero">十三术同根，五十五部古籍为证</h1>
            <p className={styles.heroSub}>
              13 个术数体系 Provider、55 部古籍 reference pack、1328 条 evidence index 记录。
              <br />
              先给确定性盘面事实，再谈解释与边界。
            </p>
            <div className={styles.heroActions}>
              <ButtonLink href="/bazi">开始排盘</ButtonLink>
              <ButtonLink href="/hecan" variant="secondary">
                多术合参
              </ButtonLink>
            </div>
          </section>

          <section aria-label="机制" className={styles.mechanism}>
            <ul>
              <li>
                <strong>确定性盘面免费</strong>
                <span>盘面由 Runtime 确定性生成，可复现、可核对。</span>
              </li>
              <li>
                <strong>事实与解释分层</strong>
                <span>盘面事实与模型表达分开标注，适用边界可见。</span>
              </li>
              <li>
                <strong>多术互证</strong>
                <span>同根资料多术对照，分歧与缺失明示。</span>
              </li>
            </ul>
          </section>

          <section aria-labelledby="home-natal" className={styles.section}>
            <div className={styles.sectionHead}>
              <h2 id="home-natal">命盘</h2>
              <p>从出生资料开始，观察长期结构与时间层。</p>
            </div>
            <div className={styles.cardGrid}>
              {NATAL_PRODUCTS.map((product, index) => (
                <TaskCard key={product.id} product={product} tier={NATAL_TIERS[index] ?? ""} />
              ))}
            </div>
          </section>

          <section aria-labelledby="home-event" className={styles.section}>
            <div className={styles.sectionHead}>
              <h2 id="home-event">事件判断</h2>
              <p>围绕同一件具体事情，记录问题、过程与发生时空。</p>
            </div>
            <div className={styles.cardGrid}>
              {EVENT_ENTRIES.map((product) => (
                <TaskCard key={product.id} product={product} />
              ))}
            </div>
          </section>

          <section aria-labelledby="home-jianxiang" className={styles.observation}>
            <div className={styles.observationCopy}>
              <p className={styles.eyebrowInverse}>观照</p>
              <h2 id="home-jianxiang">见相</h2>
              <p>面相 · 手相 · 体态 · 综合观照。{PRODUCT_CATALOG.jianxiang.summary}</p>
            </div>
            <a className={styles.observationAction} href={PRODUCT_CATALOG.jianxiang.href}>
              进入见相
              <ArrowRight aria-hidden="true" size={16} strokeWidth={1.75} />
            </a>
          </section>

          <section aria-labelledby="home-cross" className={styles.section}>
            <div className={styles.sectionHead}>
              <h2 id="home-cross">合参</h2>
              <p>同一对象、同一问题，多术分别计算后再对照。</p>
            </div>
            <div className={styles.crossGrid}>
              {CROSS_PRODUCTS.map((product) => (
                <a className={styles.crossCard} href={product.href} key={product.id}>
                  <span className={styles.cardTop}>
                    <span className={styles.cardName}>{product.name}</span>
                    <ArrowUpRight
                      aria-hidden="true"
                      className={styles.cardIcon}
                      size={16}
                      strokeWidth={1.75}
                    />
                  </span>
                  <span className={styles.crossBoundary}>
                    {CROSS_BOUNDARIES[product.id] ?? product.summary}
                  </span>
                  <span className={styles.cardMeta}>{product.headline}</span>
                </a>
              ))}
            </div>
          </section>

          <section aria-labelledby="home-aux" className={styles.section}>
            <div className={styles.sectionHead}>
              <h2 id="home-aux">辅助</h2>
              <p>日常查看、校对工具与方法资料。</p>
            </div>
            <div className={styles.auxGrid}>
              {auxiliary.map(({ href, name, description, icon: Icon }) => (
                <a className={styles.auxEntry} href={href} key={href}>
                  <Icon aria-hidden="true" className={styles.auxIcon} size={20} strokeWidth={1.7} />
                  <span className={styles.auxBody}>
                    <strong>{name}</strong>
                    <small>{description}</small>
                  </span>
                  <ArrowRight aria-hidden="true" className={styles.auxArrow} size={17} strokeWidth={1.8} />
                </a>
              ))}
            </div>
          </section>

          <PublicCmsProjection heading="已发布公告" source={{ kind: "index", prefix: "notice" }} />
        </Container>
      </main>
    </PublicPageShell>
  );
}
