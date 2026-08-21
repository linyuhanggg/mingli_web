import type { Metadata } from "next";

import { HepanResultSixStates } from "@/components/ui-lab/hepan-result-six-states";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "八字合盘六态验收 Fixture",
  description: "仅用于开发浏览器验收的八字合盘六态 Fixture。",
  robots: { index: false, follow: false },
};

export default function BaziHepanLabPage() {
  return (
    <main className={styles.page} id="main-content">
      <h1 className={styles.srOnly}>八字合盘浏览器验收</h1>
      <div aria-label="演示数据边界" className={styles.boundary} role="note">
        <strong>演示 Fixture</strong>
        <span>不代表 Runtime 已发布</span>
      </div>
      <section aria-label="八字合盘六态" className={styles.chart}>
        <HepanResultSixStates>
          <section aria-label="合盘工作区">
            <h2>甲方 / 乙方 / 关系区</h2>
            <p>等待双方真实八字 ViewModel。页面不在浏览器计算，也不补演示盘面。</p>
            <p>待接入 · 合盘结果、深读与导出仍待 Runtime 关系事实。</p>
          </section>
        </HepanResultSixStates>
      </section>
    </main>
  );
}
