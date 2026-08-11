import styles from "./ui.module.css";

export function KpiChip({
  label,
  value,
  isStub = false,
}: {
  label: string;
  value: number | string;
  isStub?: boolean;
}) {
  return (
    <div className={styles.kpi}>
      <strong>{value}</strong>
      <span>{label}</span>
      {isStub ? <em>待接入</em> : null}
    </div>
  );
}
