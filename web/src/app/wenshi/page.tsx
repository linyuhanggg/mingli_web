import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = { title: "问事合参", description: "六爻、大六壬、奇门同问同刻的合参入口。" };

export default function WenshiPage() {
  return <ProductTaskPage productId="wenshi" />;
}
