import { privateShellStyles as styles } from "@/components/private-shell";


export default function LiuyaoPage() {
  return (
    <section className={styles.panel}>
      <h1>一事一问将在 Phase 2 开放。</h1>
      <p>
        下一阶段会支持明确问题、摇卦或录入已有卦，并把问题、卦象、方式与时刻组成不可偷换的目标。当前不会返回随机占位卦。
      </p>
    </section>
  );
}
