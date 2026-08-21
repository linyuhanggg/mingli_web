import type { Metadata } from "next";

import { BaziChart } from "@/components/readings/bazi-chart";
import { BaziResultSixStates } from "@/components/ui-lab/bazi-result-six-states";
import {
  BAZI_EVIDENCE_RESULT_EVIDENCE,
  BAZI_EVIDENCE_RESULT_VIEW_MODEL,
} from "@/fixtures/bazi-evidence-result";
import { buildBaziChartViewFromViewModel } from "@/lib/reading-display";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "八字结果页验收 Fixture",
  description: "仅用于开发浏览器验收的八字结果页 Fixture。",
  robots: { index: false, follow: false },
};

export default function BaziResultLabPage() {
  return (
    <main className={styles.page} id="main-content">
      <h1 className={styles.srOnly}>八字结果页浏览器验收</h1>
      <div aria-label="演示数据边界" className={styles.boundary} role="note">
        <strong>演示 Fixture</strong>
        <span>不代表 Runtime 已发布</span>
      </div>
      <section aria-label="八字结果页生产组件" className={styles.chart}>
        <BaziResultSixStates>
          <BaziChart
            chart={buildBaziChartViewFromViewModel(BAZI_EVIDENCE_RESULT_VIEW_MODEL)}
            evidence={BAZI_EVIDENCE_RESULT_EVIDENCE}
            title="八字结果页验收切片"
          />
        </BaziResultSixStates>
      </section>
    </main>
  );
}
