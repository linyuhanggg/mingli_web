import { ArrowRight } from "lucide-react";

import { Container } from "@/components/container";
import { PublicPageShell } from "@/components/public-page-shell";
import { CROSS_PRODUCTS, EVENT_PRODUCTS, NATAL_PRODUCTS, OBSERVATION_PRODUCTS, type ProductDefinition } from "@/products/catalog";

import styles from "./arts.module.css";

function ProductList({ products }: { products: readonly ProductDefinition[] }) {
  return (
    <div className={styles.productList}>
      {products.map((product) => (
        <a href={product.href} key={product.id}>
          <span><strong>{product.name}</strong><small>{product.suitableFor}</small></span>
          <p>{product.summary}</p>
          <ArrowRight aria-hidden="true" size={18} />
        </a>
      ))}
    </div>
  );
}

export default function ArtsPage() {
  return (
    <PublicPageShell>
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <Container className={styles.container}>
          <header className={styles.hero}>
            <h1>术数总览</h1>
            <p>按任务选择公开产品。内部计算模块不会在这里伪装成独立入口。</p>
          </header>
          <section aria-labelledby="arts-natal"><h2 id="arts-natal">命盘</h2><p>从同一份已确认出生资料建立长期结构。</p><ProductList products={NATAL_PRODUCTS} /></section>
          <section aria-labelledby="arts-event"><h2 id="arts-event">事件判断</h2><p>围绕一个清楚的问题与事件时空起局。</p><ProductList products={EVENT_PRODUCTS} /></section>
          <section aria-labelledby="arts-observation"><h2 id="arts-observation">观照</h2><p>空间、方向与视觉观察分别记录来源和适用边界。</p><ProductList products={OBSERVATION_PRODUCTS} /></section>
          <section aria-labelledby="arts-cross"><h2 id="arts-cross">跨术</h2><p>多术结果分别呈现，再比较信号、分歧与缺失。</p><ProductList products={CROSS_PRODUCTS} /></section>
          <section className={styles.relationships} aria-labelledby="arts-relationships">
            <div><h2 id="arts-relationships">双人合盘</h2><p>双方资料与关系区独立呈现。</p></div>
            <nav aria-label="双人合盘入口">
              <a href="/bazi/hepan">八字合盘</a><a href="/ziwei/hepan">紫微合盘</a><a href="/qizheng/hepan">七政合盘</a>
            </nav>
          </section>
        </Container>
      </main>
    </PublicPageShell>
  );
}
