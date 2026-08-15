import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "梅花易数", description: "梅花易数问题录入、时间起卦与阅读入口。" };

export default function MeihuaPage() {
  return <ProductTaskPage productId="meihua" />;
}
