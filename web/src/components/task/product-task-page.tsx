import { ArrowLeft } from "lucide-react";
import { Suspense } from "react";

import { Container } from "@/components/container";
import { PublicPageShell } from "@/components/public-page-shell";
import { Status } from "@/components/ui/status";
import { getProductDefinition, type ProductId } from "@/products/catalog";

import { ProductTaskExperience } from "./product-task-experience";
import styles from "./task-shell.module.css";

export function ProductTaskPage({ productId }: { productId: ProductId }) {
  const product = getProductDefinition(productId);

  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={styles.container}>
          <header className={styles.hero}>
            <a className={styles.backLink} href="/arts">
              <ArrowLeft aria-hidden="true" size={16} strokeWidth={1.8} />
              术数总览
            </a>
            <div className={styles.heroCopy}>
              <div>
                <h1>{product.name}：{product.headline}</h1>
                <p>{product.summary}</p>
              </div>
              <dl className={styles.boundarySummary}>
                <div>
                  <dt>适合处理</dt>
                  <dd>{product.suitableFor}</dd>
                </div>
                <div>
                  <dt>现在能拿到</dt>
                  <dd>可复现、可核对的确定性盘面；深度解读、合参与见相仍在分阶段开放。</dd>
                </div>
              </dl>
            </div>
          </header>
          <Suspense
            fallback={(
              <Status
                state="loading"
                title={`正在准备${product.name}录入`}
                description="正在确认页面参数与已保存资料，请稍候。"
              />
            )}
          >
            <ProductTaskExperience product={product} />
          </Suspense>
        </Container>
      </main>
    </PublicPageShell>
  );
}
