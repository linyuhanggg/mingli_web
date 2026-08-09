import { ButtonLink } from "@/components/button-link";
import { privateShellStyles as styles } from "@/components/private-shell";


export default function AppPage() {
  return (
    <section className={styles.panel}>
      <h1>选择一项，开始你的解读。</h1>
      <p>
        先建立可复现的命理档案，再查看今日与近七日提示；也可以不建档，直接就一件具体的事起卦。
      </p>
      <div className={styles.nextGrid} aria-label="可用功能">
        <article className={styles.nextCard}>
          <h2>命理档案</h2>
          <span>确认出生资料与时间口径，保存不可变的档案版本。</span>
          <ButtonLink href="/app/profile/new" variant="text">
            建立命理档案
          </ButtonLink>
        </article>
        <article className={styles.nextCard}>
          <h2>今日与近七日</h2>
          <span>从已确认档案出发，查看服务端确定的日期范围与轻量提示。</span>
          <div className={styles.cardActions}>
            <ButtonLink href="/app/fortune/today" variant="text">
              查看今日
            </ButtonLink>
            <ButtonLink href="/app/fortune/week" variant="text">
              查看近七日
            </ButtonLink>
          </div>
        </article>
        <article className={styles.nextCard}>
          <h2>一事一问 · 六爻</h2>
          <span>记录具体问题、卦象、起卦时刻与地点，再生成可核对的解读。</span>
          <ButtonLink href="/app/ask/liuyao" variant="text">
            开始六爻起卦
          </ButtonLink>
        </article>
      </div>
      <ButtonLink href="/account" variant="secondary">
        管理登录与账户
      </ButtonLink>
    </section>
  );
}
