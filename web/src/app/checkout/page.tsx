import type { Metadata } from "next";

import { CommerceSurface } from "@/components/surfaces";
import { commerceSurfaces } from "@/lib/secondary-surfaces";

export const metadata: Metadata = { title: "订单确认", description: "确认一次性产品订单。" };

export default function CheckoutPage() {
  return <CommerceSurface surface={commerceSurfaces.checkout} />;
}
