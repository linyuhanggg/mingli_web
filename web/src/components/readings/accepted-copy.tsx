import styles from "./accepted-copy.module.css";

export function AcceptedCopy({ text }: Readonly<{ text?: string | null }>) {
  return (
    <section className={styles.section} aria-labelledby="accepted-copy-heading">
      <h2 id="accepted-copy-heading" className={styles.heading}>
        已接纳正文
      </h2>
      {text ? (
        <p className={styles.copy}>{text}</p>
      ) : (
        <p className={styles.empty}>服务端尚未返回已接纳正文。</p>
      )}
    </section>
  );
}
