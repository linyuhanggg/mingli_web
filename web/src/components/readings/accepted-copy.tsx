import styles from "./accepted-copy.module.css";

export function AcceptedCopy({
  text,
  emptyText,
  emptyHint,
}: Readonly<{
  text?: string | null;
  emptyText?: string;
  emptyHint?: string;
}>) {
  if (text) {
    return <p className={styles.copy}>{text}</p>;
  }
  return (
    <>
      <p className={styles.empty}>{emptyText ?? "服务端尚未返回已接纳正文。"}</p>
      {emptyHint ? <p className={styles.empty}>{emptyHint}</p> : null}
    </>
  );
}
