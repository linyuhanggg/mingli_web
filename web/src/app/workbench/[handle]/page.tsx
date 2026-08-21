import type { Metadata } from "next";
import Link from "next/link";

import { AccountSectionShell } from "@/components/account-section-shell";
import { Container } from "@/components/container";
import { PublicPageShell } from "@/components/public-page-shell";
import { Status } from "@/components/ui/status";

import styles from "./recovery.module.css";

export const metadata: Metadata = { title: "恢复任务", description: "用不透明编号查找任务。" };

export default async function WorkbenchRecoveryPage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;

  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={styles.container}>
          <AccountSectionShell intro="用不透明编号查找任务，再回到原来的产品页。" title="恢复任务">
            <section className={styles.handle} aria-labelledby="recovery-handle-title">
              <h2 id="recovery-handle-title">任务编号</h2>
              <code>{handle}</code>
              <p>编号里不包含出生资料。</p>
            </section>
            <Status
              state="unavailable"
              title="任务恢复暂时不可用"
              description="当前不会猜测任务类型或重建内容。"
            />
            <Link className={styles.homeLink} href="/">返回任务选择</Link>
          </AccountSectionShell>
        </Container>
      </main>
    </PublicPageShell>
  );
}
