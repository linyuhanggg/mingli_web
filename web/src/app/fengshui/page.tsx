import type { Metadata } from "next";

import { ProductTaskPage } from "@/components/task/product-task-page";

export const metadata: Metadata = {
  title: "风水",
  description: "空间观察、罗盘测量与风水结构事实入口。",
};

export default function FengshuiPage() {
  return <ProductTaskPage productId="fengshui" />;
}
