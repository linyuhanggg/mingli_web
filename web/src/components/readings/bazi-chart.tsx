import type { BaziChartView } from "@/lib/reading-display";

import styles from "./bazi-chart.module.css";

const PILLAR_ORDER = [
  { key: "year" as const, label: "年柱" },
  { key: "month" as const, label: "月柱" },
  { key: "day" as const, label: "日柱" },
  { key: "hour" as const, label: "时柱" },
];

function MetaRow({
  label,
  value,
}: Readonly<{ label: string; value: string | null | undefined }>) {
  if (!value) return null;
  return (
    <div className={styles.metaRow}>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export function BaziChart({
  chart,
  title = "八字命盘",
}: Readonly<{ chart: BaziChartView; title?: string }>) {
  const hasPillars =
    chart.pillars &&
    Boolean(
      chart.pillars.year ||
        chart.pillars.month ||
        chart.pillars.day ||
        chart.pillars.hour,
    );

  return (
    <section className={styles.chart} aria-label="八字命盘">
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>确定性盘面</p>
          <h3 className={styles.title}>{title}</h3>
        </div>
        {chart.activeLuck ? (
          <p className={styles.luckBadge}>当前大运 · {chart.activeLuck}</p>
        ) : null}
      </header>

      <div className={styles.centerBoard}>
        <div className={styles.brandBlock}>
          <p className={styles.brand}>FateRadar</p>
          <p className={styles.brandSub}>
            {chart.dayMaster ? `日主 ${chart.dayMaster}` : "八字本命"}
          </p>
          {chart.monthCommand ? (
            <p className={styles.brandMeta}>月令 {chart.monthCommand}</p>
          ) : null}
        </div>

        {hasPillars ? (
          <div className={styles.pillarGrid} role="list" aria-label="四柱">
            {PILLAR_ORDER.map((pillar) => {
              const value = chart.pillars?.[pillar.key] || "—";
              const stem = value.slice(0, 1) || "—";
              const branch = value.slice(1, 2) || "";
              return (
                <div className={styles.pillarCard} key={pillar.key} role="listitem">
                  <span className={styles.pillarLabel}>{pillar.label}</span>
                  <span className={styles.pillarStem}>{stem}</span>
                  <span className={styles.pillarBranch}>{branch || "—"}</span>
                  <span className={styles.pillarFull}>{value}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <p className={styles.emptyPillars}>
            服务端尚未返回可展示的四柱结构；下方仍保留公开事实摘要。
          </p>
        )}

        <dl className={styles.metaList}>
          <MetaRow label="出生时间" value={chart.birthTime} />
          <MetaRow label="性别" value={chart.gender} />
          <MetaRow label="地点" value={chart.location} />
          <MetaRow label="时间口径" value={chart.timeBasis} />
          <MetaRow label="子时策略" value={chart.ziHour} />
          <MetaRow label="时区" value={chart.timezone} />
          <MetaRow label="目标日期" value={chart.targetDay} />
          <MetaRow label="目标周期" value={chart.targetPeriod} />
          <MetaRow label="历法口径" value={chart.calendarSummary} />
        </dl>
      </div>

      {chart.highlights.length > 0 ? (
        <div className={styles.highlights}>
          <h4>盘面要点</h4>
          <ul>
            {chart.highlights.map((item) => (
              <li key={item.key}>
                <strong>{item.label}</strong>
                <span>{item.text}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {chart.secondary.length > 0 ? (
        <details className={styles.secondary}>
          <summary>口径与补充事实</summary>
          <ul>
            {chart.secondary.map((item) => (
              <li key={item.key}>
                <strong>{item.label}</strong>
                <span>{item.text}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}
