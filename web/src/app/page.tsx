import { ArrowRight, ArrowUpRight, Wrench, type LucideIcon } from "lucide-react";

import { ButtonLink } from "@/components/button-link";
import { Container } from "@/components/container";
import {
  HomeHeroItemMotion,
  HomeHeroMotion,
  HomeSectionMotion,
  HomeTaskGridMotion,
  HomeTaskItemMotion,
} from "@/components/home-motion";
import { PublicCmsProjection } from "@/components/public-cms-projection";
import { PublicPageShell } from "@/components/public-page-shell";
import { getPublicCmsMetadata } from "@/lib/public-cms-metadata";
import {
  CROSS_PRODUCTS,
  NATAL_PRODUCTS,
  PRODUCT_CATALOG,
  type ProductDefinition,
} from "@/products/catalog";

import { HomeStage } from "./home-stage";
import styles from "./home.module.css";

export async function generateMetadata() {
  return getPublicCmsMetadata("seo.home", {
    title: "十三术同根，五十五部古籍为证",
    description:
      "13 个术数体系、55 部古籍、1328 条证据索引；先给确定性盘面事实，再谈解释与边界。",
  });
}

const EVENT_ENTRIES = [
  PRODUCT_CATALOG.liuyao,
  PRODUCT_CATALOG.qimen,
  PRODUCT_CATALOG.daliuren,
] as const;

const [leadNatal, ...restNatal] = NATAL_PRODUCTS;

const CROSS_BOUNDARIES: Partial<Record<ProductDefinition["id"], string>> = {
  hecan: "八字主理，紫微、七政参证；可带着具体问题进入（原多盘问答）。",
  wenshi: "六爻先行起卦，大六壬与奇门参证同一问题与时空。",
};

const HOME_TASK_COPY: Partial<Record<ProductDefinition["id"], string>> = {
  bazi: "填出生资料，先拿到可核对的四柱。",
  ziwei: "看十二宫与大限。",
  qizheng: "看星盘与限法。",
  liuyao: "问一件具体的事。",
  qimen: "同一时空里看格局。",
  daliuren: "课体与三传对照。",
};

const auxiliary: readonly {
  href: string;
  name: string;
  description: string;
  icon?: LucideIcon;
}[] = [
  {
    href: "/life-kline",
    name: "人生 K 线",
    description: "查看可核对的档案时间层；事实不足时明确说明。",
  },
  {
    href: "/tools",
    name: "工具",
    description: "历法、时间与资料辅助工具。",
    icon: Wrench,
  },
];

const quickStarts = [
  {
    href: "/bazi",
    name: "命盘推演",
    description: "填出生资料，先拿到可核对的四柱。",
  },
  {
    href: "/liuyao",
    name: "事件判断",
    description: "问一件具体的事，再按发生时空逐层核对。",
  },
  {
    href: "/hecan",
    name: "命盘合参",
    description: "让八字、紫微与七政分别计算后互相参证。",
  },
  {
    href: "/jianxiang",
    name: "见相",
    description: "先看面相、手相与体态结构，再谈解释。",
  },
] as const;

function TaskCard({ product }: { product: ProductDefinition }) {
  return (
    <a className={styles.card} href={product.href}>
      <span className={styles.cardTop}>
        <span className={styles.cardName}>{product.name}</span>
        <ArrowUpRight aria-hidden="true" className={styles.cardIcon} size={16} strokeWidth={1.75} />
      </span>
      <span className={styles.cardSummary}>{HOME_TASK_COPY[product.id] ?? product.summary}</span>
    </a>
  );
}

export default function HomePage() {
  return (
    <PublicPageShell>
      <main className={`${styles.main} xuan-order-home`} id="main-content" tabIndex={-1}>
        <HomeStage>
          <section aria-labelledby="home-hero" className={styles.heroStage}>
            <Container className={styles.heroFrame}>
              <HomeHeroMotion className={styles.hero}>
                <HomeHeroItemMotion>
                  <p aria-hidden="true" className={styles.heroKicker}>
                    一卷可证伪的命理
                  </p>
                </HomeHeroItemMotion>
                <HomeHeroItemMotion>
                  <h1 aria-label="十三术同根，五十五部古籍为证" id="home-hero">
                    <span>十三术同根，</span>
                    <span>五十五部古籍为证</span>
                  </h1>
                </HomeHeroItemMotion>
                <HomeHeroItemMotion>
                  <p className={styles.heroSub}>以统一命盘为底，沿古籍证据逐层展开推演。</p>
                </HomeHeroItemMotion>
                <HomeHeroItemMotion>
                  <div className={styles.heroActions}>
                    <span data-magnetic>
                      <ButtonLink className={styles.heroPrimary} href="/bazi">
                        开始排盘
                      </ButtonLink>
                    </span>
                    <span>
                      <ButtonLink className={styles.heroSecondary} href="/hecan" variant="secondary">
                        命盘合参
                      </ButtonLink>
                    </span>
                  </div>
                </HomeHeroItemMotion>
                <HomeHeroItemMotion>
                  <p className={styles.heroProof}>
                    <span>
                      <strong>13</strong> 个术数体系
                    </span>
                    <span>
                      <strong>55</strong> 部古籍
                    </span>
                    <span>
                      <strong>1328</strong> 条证据索引
                    </span>
                  </p>
                </HomeHeroItemMotion>
              </HomeHeroMotion>
            </Container>
          </section>

          <section aria-labelledby="home-start" className={styles.quickStart}>
            <Container className={styles.quickStartInner}>
              <header className={styles.quickStartHead}>
                <div>
                  <span aria-hidden="true" className={styles.chapter}>卷首入门</span>
                  <h2 id="home-start">先做这一件</h2>
                </div>
                <p>先给确定性盘面事实，再谈解释与边界。</p>
              </header>
              <nav aria-label="首页快捷入口">
                <HomeTaskGridMotion className={styles.quickStartGrid}>
                  {quickStarts.map((entry) => (
                    <HomeTaskItemMotion key={entry.href}>
                      <a className={styles.quickStartEntry} href={entry.href}>
                        <span className={styles.quickStartTop}>
                          <strong>{entry.name}</strong>
                          <ArrowRight aria-hidden="true" size={17} strokeWidth={1.75} />
                        </span>
                        <small>{entry.description}</small>
                      </a>
                    </HomeTaskItemMotion>
                  ))}
                </HomeTaskGridMotion>
              </nav>
            </Container>
          </section>

          <Container className={styles.container}>
            <HomeSectionMotion dividerClassName={styles.sectionDivider}>
              <section aria-label="机制" className={styles.mechanism}>
                <ul>
                  <li>
                    <strong>确定性盘面免费</strong>
                    <span>同一套算法生成盘面，可复现、可核对。</span>
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
            </HomeSectionMotion>

            <HomeSectionMotion delay={0.04} dividerClassName={styles.sectionDivider}>
              <section aria-labelledby="home-natal" className={styles.section}>
                <div className={styles.sectionHead}>
                  <div>
                    <h2 id="home-natal">命盘</h2>
                  </div>
                  <p>从出生资料开始，观察长期结构与时间层。</p>
                </div>
                <a className={styles.leadCard} href={leadNatal.href}>
                  <span className={styles.leadCardBody}>
                    <span className={styles.leadCardEyebrow}>最常用的入口</span>
                    <strong>{leadNatal.name}</strong>
                    <span className={styles.leadCardSummary}>{HOME_TASK_COPY.bazi}</span>
                  </span>
                  <span className={styles.leadCardAction}>
                    排一张八字
                    <ArrowRight aria-hidden="true" size={16} strokeWidth={1.75} />
                  </span>
                </a>
                <div className={styles.natalRestGrid}>
                  {restNatal.map((product) => (
                    <TaskCard key={product.id} product={product} />
                  ))}
                </div>
              </section>
            </HomeSectionMotion>

            <HomeSectionMotion delay={0.05} dividerClassName={styles.sectionDivider}>
              <section aria-labelledby="home-event" className={styles.section}>
                <div className={styles.sectionHead}>
                  <div>
                    <h2 id="home-event">事件判断</h2>
                  </div>
                  <p>围绕同一件具体事情，记录问题、过程与发生时空。</p>
                </div>
                <div className={styles.cardGrid}>
                  {EVENT_ENTRIES.map((product) => (
                    <TaskCard key={product.id} product={product} />
                  ))}
                </div>
              </section>
            </HomeSectionMotion>

            <HomeSectionMotion dividerClassName={styles.sectionDivider}>
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
            </HomeSectionMotion>

            <HomeSectionMotion dividerClassName={styles.sectionDivider}>
              <section aria-labelledby="home-cross" className={styles.section}>
                <div className={styles.sectionHead}>
                  <div>
                    <h2 id="home-cross">合参</h2>
                  </div>
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
            </HomeSectionMotion>

            <HomeSectionMotion dividerClassName={styles.sectionDivider}>
              <section aria-labelledby="home-aux" className={styles.section}>
                <div className={styles.sectionHead}>
                  <h2 id="home-aux">辅助</h2>
                  <p>查看人生时间层，或使用校对与资料工具。</p>
                </div>
                <div className={styles.auxGrid}>
                  {auxiliary.map(({ href, name, description, icon: Icon }) => (
                    <a className={styles.auxEntry} href={href} key={href}>
                      {Icon ? (
                        <Icon aria-hidden="true" className={styles.auxIcon} size={20} strokeWidth={1.7} />
                      ) : (
                        <span aria-hidden="true" className={styles.auxIcon} />
                      )}
                      <span className={styles.auxBody}>
                        <strong>{name}</strong>
                        <small>{description}</small>
                      </span>
                      <ArrowRight aria-hidden="true" className={styles.auxArrow} size={17} strokeWidth={1.8} />
                    </a>
                  ))}
                </div>
              </section>
            </HomeSectionMotion>

            <PublicCmsProjection
              heading="已发布公告"
              silentWhenUnavailable
              source={{ kind: "index", prefix: "notice" }}
            />

            <section aria-labelledby="home-closing" className={styles.closing}>
              <div>
                <h2 id="home-closing">先拿到一张可核对的盘</h2>
                <p>不需要注册。填出生资料就能得到确定性四柱；要保存、跨设备或深读时再登录。</p>
              </div>
              <div className={styles.closingActions}>
                <span>
                  <ButtonLink className={styles.heroPrimary} href="/bazi">
                    开始排盘
                  </ButtonLink>
                </span>
                <ButtonLink className={styles.heroSecondary} href="/methodology" variant="secondary">
                  方法与边界
                </ButtonLink>
              </div>
            </section>
          </Container>
        </HomeStage>
      </main>
    </PublicPageShell>
  );
}
