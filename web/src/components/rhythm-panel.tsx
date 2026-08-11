import { ArrowRight, CalendarDays, Sun } from "lucide-react";
import Link from "next/link";

import type { ProfileSummary } from "@/lib/api";

import styles from "./dashboard-hub.module.css";


type RhythmPanelProps = {
  latestProfile: ProfileSummary | null;
};

export function RhythmPanel({ latestProfile }: RhythmPanelProps) {
  return (
    <section className={styles.rhythm} aria-labelledby="rhythm-title">
      <div className={styles.rhythmHeader}>
        <div>
          <span className={styles.kicker}>阶段节奏</span>
          <h2 id="rhythm-title">今日与近七日</h2>
        </div>
        <span className={styles.profileMark}>
          {latestProfile ? `最新档案 v${latestProfile.version}` : "需要一份已确认档案"}
        </span>
      </div>

      <nav className={styles.periodLinks} aria-label="阶段解读时间范围">
        <Link aria-label="查看今日" className={styles.periodLink} href="/app/fortune/today">
          <span className={styles.periodIcon} aria-hidden="true">
            <Sun size={20} strokeWidth={1.7} />
          </span>
          <span>
            <strong>今日</strong>
            <small>查看当天的确定日期范围与提示</small>
          </span>
          <ArrowRight aria-hidden="true" size={18} strokeWidth={1.7} />
        </Link>
        <Link aria-label="查看近七日" className={styles.periodLink} href="/app/fortune/week">
          <span className={styles.periodIcon} aria-hidden="true">
            <CalendarDays size={20} strokeWidth={1.7} />
          </span>
          <span>
            <strong>近七日</strong>
            <small>查看服务端确认的一周阶段节奏</small>
          </span>
          <ArrowRight aria-hidden="true" size={18} strokeWidth={1.7} />
        </Link>
      </nav>
    </section>
  );
}
