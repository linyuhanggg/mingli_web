import type { Metadata } from "next";

import { CommerceSurface } from "@/components/surfaces";
import { commerceSurfaces } from "@/lib/secondary-surfaces";

export const metadata: Metadata = { title: "订单", description: "查看这份订单。" };

export default async function CheckoutDetailPage({
  params,
}: {
  params: Promise<{ orderId: string }>;
}) {
  await params;
  return <CommerceSurface surface={commerceSurfaces.order} />;
}
