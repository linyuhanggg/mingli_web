import { ButtonLink } from "@/components/button-link";
import { Container } from "@/components/container";
import { PublicPageShell } from "@/components/public-page-shell";
import { ReadingAnatomy } from "@/components/reading-anatomy";
import { TaskCard } from "@/components/task-card";
import { TimeArchive } from "@/components/time-archive";

import styles from "./home.module.css";


const tasks = [
  {
    label: "PROFILE / 个人长期档案",
    title: "建立命理档案",
    description: "确认出生时间、地点与历法口径，先得到可复现的八字概览。游客可先填写，登录后才承诺长期保存。",
    href: "/app/profile/new",
    action: "免费开始建档",
    tone: "paper",
  },
  {
    label: "RHYTHM / 轻量阶段提示",
    title: "今日与近七日",
    description: "从已确认档案出发查看阶段节奏，不制造每天都要重新算一遍的焦虑。",
    href: "/app",
    action: "进入今日档案",
    tone: "ink",
  },
  {
    label: "LIUYAO / 一个具体问题",
    title: "一事一问",
    description: "把问题说具体，摇卦或录入已有卦，再阅读结论、条件与现实核对。",
    href: "/app/ask/liuyao",
    action: "开始整理问题",
    tone: "clay",
  },
] as const;

const steps = [
  ["01", "确认输入", "时间、地点、历法与采用口径由你最后确认。"],
  ["02", "形成事实", "确定性核心产生不可变事实简报与可表达边界。"],
  ["03", "白话成稿", "AI 只负责在允许事实内组织自然中文。"],
  ["04", "现实核对", "留下三条现实核对；反馈独立保存，不会偷偷改盘或覆盖旧正文。"],
] as const;

export default function HomePage() {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <section className={styles.hero} aria-labelledby="hero-title">
          <Container className={styles.heroGrid}>
            <div className={styles.heroCopy}>
              <h1 id="hero-title">
                把时间读成一份
                <span>可核对的个人档案。</span>
              </h1>
              <p className={styles.folio}>FateRadar · Personal Fate Archive</p>
              <p className={styles.heroIntro}>
                先确定盘面、事实与来源，再把结论、条件和不确定之处写成大白话。不是随机聊天，也不靠神秘感藏住依据。
              </p>
              <div className={styles.actions}>
                <ButtonLink href="/app/profile/new">免费建立命理档案</ButtonLink>
                <ButtonLink href="/app/ask/liuyao" variant="secondary">
                  问一件具体的事
                </ButtonLink>
              </div>
              <ul className={styles.trustline} aria-label="核心承诺">
                <li>
                  <strong>确定性命理核心</strong>
                  <span>盘面不交给模型猜</span>
                </li>
                <li>
                  <strong>可核对依据</strong>
                  <span>结论、条件与来源分开读</span>
                </li>
                <li>
                  <strong>私密个人解读</strong>
                  <span>正式资料不进公共缓存</span>
                </li>
              </ul>
            </div>
            <TimeArchive />
          </Container>
        </section>

        <section className={styles.tasks} aria-labelledby="tasks-title">
          <Container>
            <div className={styles.sectionHeader}>
              <h2 id="tasks-title">先做一件明确的事。</h2>
              <p>
                P0 只开放三个入口。完整命理能力留在核心里，未准备好的体系不会被包装成空产品。
              </p>
            </div>
            <div className={styles.taskGrid}>
              {tasks.map((task) => (
                <TaskCard key={task.href} {...task} />
              ))}
            </div>
          </Container>
        </section>

        <section className={styles.method} aria-labelledby="method-title">
          <Container className={styles.methodGrid}>
            <div className={styles.methodIntro}>
              <h2 id="method-title">先算，再讲，再请你核对。</h2>
              <p>
                确定性计算负责盘面、事实与来源；AI 只负责白话表达。换模型不会改盘，现实反馈也不会覆盖历史版本。
              </p>
              <ButtonLink href="/methodology" variant="secondary">
                查看完整方法与边界
              </ButtonLink>
            </div>
            <ol className={styles.steps}>
              {steps.map(([index, title, text]) => (
                <li key={index}>
                  <span>{index}</span>
                  <div>
                    <strong>{title}</strong>
                    <p>{text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Container>
        </section>

        <section className={styles.sample} aria-labelledby="sample-title">
          <Container className={styles.sampleGrid}>
            <div className={styles.sectionHeader}>
              <h2 id="sample-title">一份解读，关键层级不能藏。</h2>
              <p>
                下面只演示信息结构，不使用真实个人资料，也不伪装成一次真实排盘。切换查看正文怎样从结论走到核对。
              </p>
            </div>
            <ReadingAnatomy />
          </Container>
        </section>

        <section className={styles.pricing} aria-labelledby="pricing-title">
          <Container>
            <div className={styles.sectionHeader}>
              <h2 id="pricing-title">免费先看清，再为一份明确结果付费。</h2>
              <p>
                首版不卖自动续费、充值币或永久无限 AI。真实支付通道尚未接入，当前只展示已冻结的商品目录。
              </p>
            </div>
            <div className={styles.priceLedger}>
              <article>
                <div>
                  <h3>免费概览</h3>
                  <p>本人档案、有限概览、3 条现实核对与轻量节奏。</p>
                </div>
                <strong>¥0</strong>
                <ButtonLink href="/app/profile/new" variant="text">先免费开始</ButtonLink>
              </article>
              <article>
                <div>
                  <h3>个人命盘深度解读</h3>
                  <p>绑定一个档案版本，永久查看，7 天内 3 次同盘追问。</p>
                </div>
                <strong>¥29.90</strong>
                <ButtonLink href="/pricing" variant="text">查看交付范围</ButtonLink>
              </article>
              <article>
                <div>
                  <h3>一事一问 · 六爻</h3>
                  <p>绑定具体问题与卦象，永久查看，72 小时内 2 次同盘追问。</p>
                </div>
                <strong>¥9.90</strong>
                <ButtonLink href="/pricing" variant="text">查看购买边界</ButtonLink>
              </article>
            </div>
          </Container>
        </section>

        <section className={styles.close} aria-labelledby="close-title">
          <Container className={styles.closeGrid}>
            <div>
              <h2 id="close-title">资料归你，边界也该看得见。</h2>
              <p>
                出生资料、问题正文、解读与核对反馈都按高敏感业务数据保护。保存、导出、删除和撤销设备进入账户边界。
              </p>
            </div>
            <div className={styles.closeActions}>
              <ButtonLink href="/privacy" variant="secondary">阅读隐私边界</ButtonLink>
              <ButtonLink href="/app/profile/new">开始免费建档</ButtonLink>
            </div>
          </Container>
        </section>
      </main>
    </PublicPageShell>
  );
}
