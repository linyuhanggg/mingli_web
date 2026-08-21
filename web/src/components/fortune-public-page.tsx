import { ArrowLeft } from "lucide-react";
import { Suspense } from "react";

import { Container } from "@/components/container";
import { FortuneFlow } from "@/components/fortune-flow";
import { PublicPageShell } from "@/components/public-page-shell";
import { Status } from "@/components/ui/status";

import styles from "./task/task-shell.module.css";

export const FORTUNE_PUBLIC_TITLE = "今日与近七日";
export const FORTUNE_PUBLIC_SUMMARY =
  "选一份已确认的出生档案，查看今天或近七日的事业与工作节奏。";

export function FortunePublicPage() {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={styles.container}>
          <header className={styles.pageLine}>
            <a className={styles.backLink} href="/arts">
              <ArrowLeft aria-hidden="true" size={16} strokeWidth={1.8} />
              返回
            </a>
            <h1>{FORTUNE_PUBLIC_TITLE}</h1>
            <p>{FORTUNE_PUBLIC_SUMMARY}</p>
          </header>
          <Suspense
            fallback={(
              <Status
                state="loading"
                title="正在准备今日与近七日录入"
                description="正在确认页面参数与已保存资料，请稍候。"
              />
            )}
          >
            <FortuneFlow mode="both" />
          </Suspense>
        </Container>
      </main>
    </PublicPageShell>
  );
}
