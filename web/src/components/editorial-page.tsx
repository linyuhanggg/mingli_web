import type { ReactNode } from "react";
import Link from "next/link";

import { Container } from "./container";
import styles from "./editorial-page.module.css";
import { PublicPageShell } from "./public-page-shell";


type EditorialPageProps = {
  eyebrow: string;
  title: string;
  intro: string;
  children: ReactNode;
};

export function EditorialPage({ eyebrow, title, intro, children }: EditorialPageProps) {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container>
          <header className={styles.hero}>
            <div className={styles.heroCopy}>
              <h1>{title}</h1>
              <p className={styles.folio}>{eyebrow}</p>
            </div>
            <p className={styles.intro}>{intro}</p>
          </header>
          <div className={styles.content}>{children}</div>
        </Container>
      </main>
    </PublicPageShell>
  );
}

export function PolicyMeta() {
  return (
    <section className={styles.policyMeta} aria-label="政策版本">
      <dl>
        <div>
          <dt>版本</dt>
          <dd>开发预览 v0.1</dd>
        </div>
        <div>
          <dt>生效状态</dt>
          <dd>未生效</dd>
        </div>
        <div>
          <dt>生效时间</dt>
          <dd>真实主体与法律审阅完成后发布</dd>
        </div>
      </dl>
      <nav className={styles.policyLinks} aria-label="政策相关入口">
        <Link href="/auth/login">前往登录</Link>
        <Link href="/pricing">查看价格与交付</Link>
      </nav>
    </section>
  );
}

export { styles as editorialStyles };
