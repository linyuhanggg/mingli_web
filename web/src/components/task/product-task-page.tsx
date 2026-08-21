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
          <header className={styles.pageLine}>
            <a className={styles.backLink} href="/arts">
              <ArrowLeft aria-hidden="true" size={16} strokeWidth={1.8} />
              返回
            </a>
            <h1>{product.name}</h1>
            <p>{product.summary}</p>
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
