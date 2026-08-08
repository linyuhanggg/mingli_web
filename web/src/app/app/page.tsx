import { ButtonLink } from "@/components/button-link";
import { privateShellStyles as styles } from "@/components/private-shell";


export default function AppPage() {
  return (
    <section className={styles.panel}>
      <h1>你的命理档案，从这里继续。</h1>
      <p>
        Phase 1 已完成网站壳与身份基础。档案、今日/近七日、六爻起卦和正式解读将在 Phase 2 接入确定性运行时后开放，这里不会先伪造计算结果。
      </p>
      <div className={styles.nextGrid} aria-label="下一阶段能力">
        <div className={styles.nextCard}>
          <strong>建立受测档案</strong>
          <span>下一阶段：资料确认、隐私同意和不可变 Profile Version</span>
        </div>
        <div className={styles.nextCard}>
          <strong>今日与近七日</strong>
          <span>下一阶段：基于已确认档案生成轻量摘要</span>
        </div>
        <div className={styles.nextCard}>
          <strong>一事一问 · 六爻</strong>
          <span>下一阶段：记录问题、卦象、起卦方式与时刻</span>
        </div>
      </div>
      <ButtonLink href="/account">先完成手机号或邮箱登录</ButtonLink>
    </section>
  );
}
