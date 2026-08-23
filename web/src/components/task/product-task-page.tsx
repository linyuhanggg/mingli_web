import { ArrowLeft } from "lucide-react";
import { Suspense } from "react";

import { Container } from "@/components/container";
import { PublicPageShell } from "@/components/public-page-shell";
import { Status } from "@/components/ui/status";
import { getProductDefinition, type ProductId } from "@/products/catalog";

import { LIUYAO_ENTRY_SUITABILITY } from "./liuyao-entry-copy";
import { MEIHUA_ENTRY_SUITABILITY } from "./meihua-entry-copy";
import { ProductTaskExperience } from "./product-task-experience";
import styles from "./task-shell.module.css";

const ENTRY_SUITABILITY: Partial<Record<ProductId, string>> = {
  liuyao: LIUYAO_ENTRY_SUITABILITY,
  meihua: MEIHUA_ENTRY_SUITABILITY,
};

const ENTRY_SEAL: Partial<Record<ProductId, string>> = {
  liuyao: "六爻",
  meihua: "梅",
};

export function ProductTaskPage({ productId }: { productId: ProductId }) {
  const product = getProductDefinition(productId);
  const suitability = ENTRY_SUITABILITY[productId] ?? product.summary;
  const seal = ENTRY_SEAL[productId];

  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={styles.container}>
          <header className={styles.pageLine}>
            <a className={styles.backLink} href="/arts">
              <ArrowLeft aria-hidden="true" size={16} strokeWidth={1.8} />
              返回
            </a>
            {seal ? (
              <span aria-hidden="true" className={styles.sealMark} data-seal={productId}>
                {seal}
              </span>
            ) : null}
            <h1>{product.name}</h1>
            <p>{suitability}</p>
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
