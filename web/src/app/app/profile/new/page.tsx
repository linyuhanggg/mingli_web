import { privateShellStyles as styles } from "@/components/private-shell";


export default function NewProfilePage() {
  return (
    <section className={styles.panel}>
      <h1>建档将在 Phase 2 开放。</h1>
      <p>
        表单会覆盖公历/农历、未知时辰、出生地与时区、真太阳时口径、资料确认和隐私同意。在服务端规范化完成前，本页不会在浏览器里自行算盘。
      </p>
    </section>
  );
}
