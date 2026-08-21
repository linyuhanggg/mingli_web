import type { Metadata } from "next";

import { CommerceSurface } from "@/components/surfaces";
import { commerceSurfaces } from "@/lib/secondary-surfaces";

export const metadata: Metadata = { title: "结账", description: "当前没有可购买的商品。" };

export default function CheckoutPage() {
  return <CommerceSurface surface={commerceSurfaces.checkout} />;
}
