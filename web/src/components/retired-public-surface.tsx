import Link from "next/link";

import { Container } from "./container";
import { PublicPageShell } from "./public-page-shell";
import styles from "./retired-public-surface.module.css";

type RetiredPublicSurfaceProps = Readonly<{
  title: string;
}>;

export function RetiredPublicSurface({ title }: RetiredPublicSurfaceProps) {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={styles.container}>
          <section
            aria-describedby="retired-public-surface-description"
            aria-labelledby="retired-public-surface-title"
            className={styles.status}
            data-status="retired"
            role="status"
          >
            <p className={styles.eyebrow}>入口状态更新</p>
            <h1 id="retired-public-surface-title">{title}</h1>
            <p className={styles.description} id="retired-public-surface-description">
              公开入口已改为人生 K 线。
            </p>
            <p className={styles.note}>
              旧地址继续保留，避免书签或外部链接变成空白页；这里不再读取或展示原栏目内容。
            </p>
            <div className={styles.actions}>
              <Link className={styles.primaryAction} href="/life-kline">
                前往人生 K 线
              </Link>
              <Link className={styles.secondaryAction} href="/">
                返回首页
              </Link>
            </div>
          </section>
        </Container>
      </main>
    </PublicPageShell>
  );
}
