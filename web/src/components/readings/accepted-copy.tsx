import styles from "./accepted-copy.module.css";

export function AcceptedCopy({ text }: Readonly<{ text?: string | null }>) {
  return text ? (
    <p className={styles.copy}>{text}</p>
  ) : (
    <p className={styles.empty}>服务端尚未返回已接纳正文。</p>
  );
}
