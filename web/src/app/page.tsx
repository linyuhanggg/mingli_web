import {
  BookOpenText,
  CheckCircle2,
  FileText,
  ShieldCheck,
  Sparkles,
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

import styles from "./home.module.css";


const tasks = [
  {
    label: "TASK 01",
    title: "八字命盘起盘",
    description:
      "输入生辰，即时形成可复现的四柱干支与十神格局概览，并由确定性核心给出有边界的白话解读。",
    href: "/app/profile/new",
    action: "立即进入排盘",
    meta: "输入生辰 · 盘出四柱与格局",
    icon: Sparkles,
  },
  {
    label: "TASK 02",
    title: "今日与近七日",
    description:
      "从已确认档案出发查看阶段节奏，把时间拆成可核对的短周期提示，而不是制造每天重算的焦虑。",
    href: "/app/fortune/today",
    action: "开启阶段推算",
    meta: "阶段节奏 · 今日与近七日",
    icon: FileText,
  },
  {
    label: "TASK 03",
    title: "学术中心与古籍库",
    description:
      "查看方法、边界与可核对依据。正式解读会把结论、条件与来源分开，拒绝神秘包装。",
    href: "/methodology",
    action: "进入学术典籍库",
    meta: "方法边界 × 可核对依据",
    icon: BookOpenText,
  },
] as const;

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

const freeFeatures = [
  "完整建档与有限八字概览",
  "基础命格与阶段节奏提示",
  "3 条现实核对位",
  "方法与边界公开查阅",
] as const;

const proFeatures = [
  "包含免费版所有功能",
  "个人命盘深度解读与同盘追问",
  "流年、大限与今日近七日分析",
  "永久查看已购解读档案",
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
                    融合确定性命理计算与现代化大语言模型，拒绝套路化鸡汤与迷信泛论。提供可验证的原典依据、盘面事实与清晰的命运格局推演。
                  </p>
                  <div className={styles.actions}>
                    <ButtonLink className={styles.primaryAction} href="/app/profile/new">
                      免费体验起盘档案
                    </ButtonLink>
                    <ButtonLink
                      className={styles.secondaryAction}
                      href="/methodology"
                      variant="secondary"
                    >
                      查阅学术典籍库
                    </ButtonLink>
                  </div>
                  <ul className={styles.trustline} aria-label="核心承诺">
                    <li>
                      <CheckCircle2 aria-hidden="true" size={15} />
                      <span>100% 逻辑可溯源</span>
                    </li>
                    <li>
                      <ShieldCheck aria-hidden="true" size={15} />
                      <span>端到端数据私密</span>
                    </li>
                    <li>
                      <BookOpenText aria-hidden="true" size={15} />
                      <span>附带原典注解</span>
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
                  <h2 id="tasks-title">选择您的建档研究入口</h2>
                </div>
                <p>
                  三大核心功能均支持完整免费试用。正式资料登录后才承诺长期保存；盘面始终由确定性核心计算。
                </p>
              </div>
            </HomeSectionMotion>
            <HomeTaskGridMotion className={styles.taskGrid}>
              {tasks.map((task) => (
                <HomeTaskItemMotion key={task.href}>
                  <article className={styles.taskCard}>
                    <div className={styles.taskTop}>
                      <span>{task.label}</span>
                      <task.icon aria-hidden="true" size={18} strokeWidth={1.7} />
                    </div>
                    <h3>{task.title}</h3>
                    <p className={styles.taskMeta}>{task.meta}</p>
                    <p>{task.description}</p>
                    <ButtonLink className={styles.taskAction} href={task.href} variant="text">
                      {task.action}
                    </ButtonLink>
                  </article>
                </HomeTaskItemMotion>
              ))}
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
                  <p className={styles.sectionEyebrow}>透明权益 / ARCHIVE TIERS</p>
                  <h2 id="pricing-title">体验版与学术专业版对比</h2>
                </div>
                <p>
                  首版不卖自动续费、充值币或永久无限 AI。真实支付通道尚未接入时，只展示已冻结商品目录。
                </p>
              </div>
            </HomeSectionMotion>
            <HomeLedgerMotion className={styles.priceGrid}>
              <HomeLedgerItemMotion>
                <div className={styles.priceCard}>
                  <p className={styles.priceLabel}>基础研习</p>
                  <h3>免费体验档案</h3>
                  <p className={styles.priceValue}>
                    ¥0 <span>/ 永久免费</span>
                  </p>
                  <ul>
                    {freeFeatures.map((item) => (
                      <li key={item}>
                        <CheckCircle2 aria-hidden="true" size={15} />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                  <ButtonLink className={styles.priceSecondary} href="/app/profile/new" variant="secondary">
                    直接开始起盘
                  </ButtonLink>
                </div>
              </HomeLedgerItemMotion>
              <HomeLedgerItemMotion>
                <div className={`${styles.priceCard} ${styles.priceCardFeatured}`}>
                  <span className={styles.recommended}>RECOMMENDED</span>
                  <p className={styles.priceLabel}>学术与深度研究</p>
                  <h3>专业学术版</h3>
                  <p className={styles.priceValue}>
                    ¥29.90 <span>/ 按次深度解读</span>
                  </p>
                  <ul>
                    {proFeatures.map((item) => (
                      <li key={item}>
                        <CheckCircle2 aria-hidden="true" size={15} />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                  <ButtonLink className={styles.pricePrimary} href="/pricing">
                    解锁专业排盘报告
                  </ButtonLink>
                </div>
              </HomeLedgerItemMotion>
            </HomeLedgerMotion>
          </section>
        </Container>
      </main>
    </PublicPageShell>
  );
}
