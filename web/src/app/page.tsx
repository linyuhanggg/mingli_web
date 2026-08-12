import {
  Archive,
  BookOpenText,
  CalendarRange,
  CheckCircle2,
  MessageCircleQuestion,
  ShieldCheck,
} from "lucide-react";

import { ButtonLink } from "@/components/button-link";
import { Container } from "@/components/container";
import {
  HomeHeroMotion,
  HomeLedgerItemMotion,
  HomeLedgerMotion,
  HomeSectionMotion,
  HomeStepItemMotion,
  HomeStepsMotion,
  HomeTaskGridMotion,
  HomeTaskItemMotion,
} from "@/components/home-motion";
import { PublicPageShell } from "@/components/public-page-shell";
import { TimeArchive } from "@/components/time-archive";
import {
  PRODUCT_CAPABILITIES,
  type ProductCapabilityId,
  type ProductTaskTone,
} from "@/lib/product-capabilities";

import styles from "./home.module.css";


const taskIcons = {
  bazi: Archive,
  fortune: CalendarRange,
  liuyao: MessageCircleQuestion,
} satisfies Record<ProductCapabilityId, typeof Archive>;

const taskToneStyles = {
  paper: styles.taskCardPaper,
  ink: styles.taskCardInk,
  clay: styles.taskCardClay,
} satisfies Record<ProductTaskTone, string>;

const methods = [
  {
    index: "壹",
    title: "确定性命理核心",
    text: "盘面、事实与可表达边界由确定性核心生成，不交给模型猜。",
  },
  {
    index: "贰",
    title: "可核对的典籍引注",
    text: "结论、条件与来源分层呈现，AI 只在允许事实内组织白话。",
  },
  {
    index: "叁",
    title: "私密与无恐吓承诺",
    text: "个人生辰数据不进公共缓存，拒绝灾祸恐吓式营销。",
  },
] as const;

const pricingOffers = [
  {
    label: "FREE / 基础能力",
    title: "免费基础能力",
    price: "¥0",
    suffix: "/ 当前免费",
    features: [
      "一个本人档案与确定性八字排盘",
      "有限白话概览与 3 条现实核对",
      "今日 / 近七日摘要与六爻基础卦象",
    ],
    action: "查看免费能力边界",
  },
  {
    label: "ONE-OFF / 单次报告",
    title: "个人命盘深度解读",
    price: "¥29.90",
    suffix: "/ 单次",
    features: [
      "绑定一个已经确认的档案版本",
      "已接纳报告永久查看",
      "7 天内 3 次同盘追问",
    ],
    action: "查看八字报告交付",
  },
  {
    label: "ONE-OFF / 单次报告",
    title: "一事一问 · 六爻事件报告",
    price: "¥9.90",
    suffix: "/ 单次",
    features: [
      "当前绑定一个事业或工作问题",
      "事件报告永久查看",
      "72 小时内 2 次同盘追问",
    ],
    action: "查看六爻报告交付",
  },
] as const;

export default function HomePage() {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={styles.stack}>
          <section className={styles.hero} aria-labelledby="hero-title">
            <HomeHeroMotion>
              <div className={styles.heroGrid}>
                <div className={styles.heroCopy}>
                  <p className={styles.kicker}>东方编辑档案 · 命盘 AI 架构</p>
                  <h1 id="hero-title">
                    把时间变成私密、
                    <span>可核对的个人档案。</span>
                  </h1>
                  <p className={styles.heroIntro}>
                    先由确定性核心形成盘面事实，再由 AI 在事实范围内组织白话。原典命中时才展示可定位来源；没有命中时明确留空。
                  </p>
                  <div className={styles.actions}>
                    <ButtonLink className={styles.primaryAction} href="/app/profile/new">
                      免费体验起盘档案
                    </ButtonLink>
                    <ButtonLink
                      className={styles.secondaryAction}
                      href="/app/ask/liuyao"
                      variant="secondary"
                    >
                      问一件工作上的事
                    </ButtonLink>
                  </div>
                  <ul className={styles.trustline} aria-label="核心承诺">
                    <li>
                      <CheckCircle2 aria-hidden="true" size={15} />
                      <span>盘面事实可核对</span>
                    </li>
                    <li>
                      <ShieldCheck aria-hidden="true" size={15} />
                      <span>出生资料按隐私政策处理</span>
                    </li>
                    <li>
                      <BookOpenText aria-hidden="true" size={15} />
                      <span>证据与结论分开呈现</span>
                    </li>
                  </ul>
                </div>
                <TimeArchive />
              </div>
            </HomeHeroMotion>
          </section>

          <section className={styles.tasks} aria-labelledby="tasks-title">
            <HomeSectionMotion>
              <div className={styles.sectionHeader}>
                <div>
                  <p className={styles.sectionEyebrow}>核心应用档案 / P0 TASKS</p>
                  <h2 id="tasks-title">从当下最想解决的事开始</h2>
                </div>
                <p>
                  三条路径都对应当前已经实现的功能入口。建档看长期结构，看今日近七日处理时间节奏，事业或工作问题则进入六爻。
                </p>
              </div>
            </HomeSectionMotion>
            <HomeTaskGridMotion className={styles.taskGrid}>
              {PRODUCT_CAPABILITIES.map((capability) => {
                const Icon = taskIcons[capability.id];

                return (
                  <HomeTaskItemMotion key={capability.href}>
                    <article
                      className={`${styles.taskCard} ${taskToneStyles[capability.home.tone]}`}
                      data-tone={capability.home.tone}
                    >
                      <div className={styles.taskTop}>
                        <span>{capability.home.eyebrow}</span>
                        <Icon aria-hidden="true" size={18} strokeWidth={1.7} />
                      </div>
                      <h3>{capability.home.title}</h3>
                      <p className={styles.taskMeta}>{capability.home.meta}</p>
                      <p>{capability.home.description}</p>
                      <div className={styles.taskActions}>
                        <ButtonLink
                          className={styles.taskAction}
                          href={capability.href}
                          variant="text"
                        >
                          {capability.home.action}
                        </ButtonLink>
                        {capability.home.secondaryAction ? (
                          <ButtonLink
                            className={styles.taskAction}
                            href={capability.home.secondaryAction.href}
                            variant="text"
                          >
                            {capability.home.secondaryAction.label}
                          </ButtonLink>
                        ) : null}
                      </div>
                    </article>
                  </HomeTaskItemMotion>
                );
              })}
            </HomeTaskGridMotion>
          </section>

          <section className={styles.method} aria-labelledby="method-title">
            <HomeSectionMotion>
              <div className={styles.sectionHeader}>
                <div>
                  <p className={styles.sectionEyebrow}>严谨学术立场 / METHODOLOGY</p>
                  <h2 id="method-title">以古籍为依据，以理性为框架</h2>
                </div>
                <p>
                  命运不是不可改变的宿命锁链，而是天时、地利、人和综合作用的概率倾向。FateRadar
                  坚持无神秘主义套路、无恐吓式断言。
                </p>
              </div>
            </HomeSectionMotion>
            <HomeStepsMotion className={styles.methodGrid}>
              {methods.map((item) => (
                <HomeStepItemMotion key={item.index}>
                  <article className={styles.methodCard}>
                    <span>{item.index}</span>
                    <h3>{item.title}</h3>
                    <p>{item.text}</p>
                  </article>
                </HomeStepItemMotion>
              ))}
            </HomeStepsMotion>
          </section>

          <section className={styles.pricing} aria-labelledby="pricing-title">
            <HomeSectionMotion>
              <div className={styles.sectionHeader}>
                <div>
                  <p className={styles.sectionEyebrow}>透明权益 / DELIVERY CATALOG</p>
                  <h2 id="pricing-title">免费能力与两种单次报告</h2>
                </div>
                <p>
                  测试期无真实支付、预览入口可能无 TLS；付费向解读仅运营开通。这里只展示商品边界，不会把点击写成已付款。
                </p>
              </div>
            </HomeSectionMotion>
            <HomeLedgerMotion className={styles.priceGrid}>
              {pricingOffers.map((offer, index) => (
                <HomeLedgerItemMotion key={offer.title}>
                  <article
                    className={`${styles.priceCard} ${index === 0 ? styles.priceCardFree : styles.priceCardPaid}`}
                  >
                    <p className={styles.priceLabel}>{offer.label}</p>
                    <h3>{offer.title}</h3>
                    <p className={styles.priceValue}>
                      <strong>{offer.price}</strong> <span>{offer.suffix}</span>
                    </p>
                    <ul>
                      {offer.features.map((item) => (
                        <li key={item}>
                          <CheckCircle2 aria-hidden="true" size={15} />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                    <ButtonLink
                      className={styles.priceAction}
                      href="/pricing"
                      variant={index === 0 ? "secondary" : "primary"}
                    >
                      {offer.action}
                    </ButtonLink>
                  </article>
                </HomeLedgerItemMotion>
              ))}
            </HomeLedgerMotion>
          </section>
        </Container>
      </main>
    </PublicPageShell>
  );
}
