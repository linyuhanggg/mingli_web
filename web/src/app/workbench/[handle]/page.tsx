import { RotateCcw } from "lucide-react";
import Link from "next/link";

import { Container } from "@/components/container";
import { PublicPageShell } from "@/components/public-page-shell";
import { Status } from "@/components/ui/status";

import styles from "./recovery.module.css";

export default async function WorkbenchRecoveryPage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;

  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={styles.container}>
          <header><RotateCcw aria-hidden="true" size={27} strokeWidth={1.6} /><div><h1>恢复任务</h1><p>这里仅用不透明句柄查找任务归属，再回到原产品路由。</p></div></header>
          <section className={styles.handle} aria-labelledby="recovery-handle-title">
            <h2 id="recovery-handle-title">任务句柄</h2>
            <code>{handle}</code>
            <p>URL 不包含出生资料、问题正文、照片、性别或内部凭据。</p>
          </section>
          <Status state="unavailable" title="任务恢复服务尚未接入" description="当前不会猜测任务类型或重建内容。服务接通后会解析并重定向回八字、六爻等所属产品路由。" />
          <Link className={styles.homeLink} href="/">返回任务选择</Link>
        </Container>
      </main>
    </PublicPageShell>
  );
}
