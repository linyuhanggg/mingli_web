import { ButtonLink } from "@/components/button-link";
import { Container } from "@/components/container";
import { PublicPageShell } from "@/components/public-page-shell";
import { TaskCard } from "@/components/task-card";

import styles from "./home.module.css";


const tasks = [
  {
    index: "01",
    eyebrow: "Profile",
    title: "命理档案",
    description: "确认出生时间、地点与历法口径，先得到可复现的八字概览。",
    href: "/app/profile/new",
    action: "开始建档",
  },
  {
    index: "02",
    eyebrow: "Rhythm",
    title: "今日与近七日",
    description: "从自己的档案出发，查看轻量阶段提示，不制造每天都要算一遍的焦虑。",
    href: "/app/fortune/today",
    action: "查看今日提示",
  },
  {
    index: "03",
    eyebrow: "Liuyao",
    title: "一事一问",
    description: "把问题说具体，摇卦或录入已有卦，再得到结论、条件与现实核对。",
    href: "/app/ask/liuyao",
    action: "开始起卦",
  },
] as const;

export default function HomePage() {
  return (
    <PublicPageShell>
      <main className={styles.main}>
        <section className={styles.hero}>
          <Container className={styles.heroGrid}>
            <div>
              <p className={styles.eyebrow}>Personal Fate Archive · Beta</p>
              <h1>
                先把人生事实算清楚，<em>再谈方向。</em>
              </h1>
            </div>
            <div className={styles.heroIntro}>
              <p>
                一份属于你的命理档案。先确定盘面与证据，再用大白话说明结论、条件和不确定之处。
              </p>
              <div className={styles.actions}>
                <ButtonLink href="/app/profile/new">免费建立命理档案</ButtonLink>
                <ButtonLink href="/app/ask/liuyao" variant="secondary">
                  问一件具体的事
                </ButtonLink>
              </div>
              <ul className={styles.trustline} aria-label="服务特点">
                <li>游客可先试</li>
                <li>不卖无限 AI</li>
                <li>结果可核对</li>
              </ul>
            </div>
          </Container>
        </section>

        <section className={styles.tasks} aria-labelledby="tasks-title">
          <Container>
            <div className={styles.sectionHeader}>
              <div>
                <p className={styles.eyebrow}>Three clear starts</p>
                <h2 id="tasks-title">从一个明确任务开始。</h2>
              </div>
              <p>
                不是空白聊天框，也不让术语挡在门口。每个入口都说明需要什么、会得到什么，以及哪里不能乱下结论。
              </p>
            </div>
            <div className={styles.taskGrid}>
              {tasks.map((task) => (
                <TaskCard key={task.index} {...task} />
              ))}
            </div>
          </Container>
        </section>

        <section className={styles.method} aria-labelledby="method-title">
          <Container className={styles.methodGrid}>
            <div className={styles.sectionHeader}>
              <div>
                <p className={styles.eyebrow}>How it works</p>
                <h2 id="method-title">先算，再讲，再请你核对。</h2>
              </div>
              <p>
                确定性计算负责盘面、事实与来源；AI 只负责白话表达，不自己算盘，也不能凭空补古籍出处。
              </p>
            </div>
            <ol className={styles.steps}>
              <li>
                <strong>STEP 01</strong>
                <span>确认时间、地点与采用口径</span>
              </li>
              <li>
                <strong>STEP 02</strong>
                <span>生成不可变事实简报</span>
              </li>
              <li>
                <strong>STEP 03</strong>
                <span>给出结论、依据与边界</span>
              </li>
              <li>
                <strong>STEP 04</strong>
                <span>留下三条现实核对</span>
              </li>
            </ol>
          </Container>
        </section>

        <section className={styles.sample} aria-labelledby="sample-title">
          <Container>
            <div className={styles.sectionHeader}>
              <div>
                <p className={styles.eyebrow}>Result anatomy</p>
                <h2 id="sample-title">一眼看懂，不藏关键条件。</h2>
              </div>
              <p>示例只演示信息结构，不使用任何真实个人资料，也不伪装成一次真实排盘。</p>
            </div>
            <div className={styles.sampleGrid}>
              <article className={styles.sampleCard}>
                <small>01 · 先给结论</small>
                <h3>当前更适合收束目标，而不是同时开三条新线。</h3>
                <p>结论会标明适用范围，不写成保证发生的预言。</p>
              </article>
              <article className={styles.sampleCard}>
                <small>02 · 再讲依据</small>
                <h3>每个关键判断都回到事实简报。</h3>
                <p>有古籍命中才展示来源；零命中就保持零。</p>
              </article>
              <article className={styles.sampleCard}>
                <small>03 · 最后核对</small>
                <h3>现实反馈不会偷偷改盘。</h3>
                <p>符合、部分符合、不符合和暂不清楚都会独立保存。</p>
              </article>
            </div>
          </Container>
        </section>

        <section className={styles.pricing} aria-labelledby="pricing-title">
          <Container>
            <div className={styles.sectionHeader}>
              <div>
                <p className={styles.eyebrow}>Simple pricing</p>
                <h2 id="pricing-title">免费先看清，再按一份结果付费。</h2>
              </div>
              <p>首版没有自动续费、充值币或永久无限 AI。正式支付通道尚未接入。</p>
            </div>
            <div className={styles.priceGrid}>
              <article className={styles.priceCard}>
                <h3>免费概览</h3>
                <p className={styles.price}>¥0</p>
                <p>本人档案、有限概览、现实核对与轻量节奏。</p>
                <ButtonLink href="/app/profile/new" variant="text">
                  先免费开始
                </ButtonLink>
              </article>
              <article className={styles.priceCard}>
                <h3>个人命盘深度解读</h3>
                <p className={styles.price}>¥29.90</p>
                <p>绑定一个档案版本，永久查看，7 天内 3 次同盘追问。</p>
                <ButtonLink href="/pricing" variant="text">
                  查看交付范围
                </ButtonLink>
              </article>
              <article className={styles.priceCard}>
                <h3>一事一问 · 六爻</h3>
                <p className={styles.price}>¥9.90</p>
                <p>绑定具体问题与卦象，永久查看，72 小时内 2 次同盘追问。</p>
                <ButtonLink href="/pricing" variant="text">
                  查看购买边界
                </ButtonLink>
              </article>
            </div>
          </Container>
        </section>
      </main>
    </PublicPageShell>
  );
}
