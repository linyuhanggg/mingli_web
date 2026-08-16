import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = {
  title: "禄命纳音",
  description: "禄命、四柱纳音与三元关系事实入口。",
};

export default function LumingNayinPage() {
  return <ProductTaskPage productId="luming-nayin" />;
}
