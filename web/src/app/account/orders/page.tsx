import type { Metadata } from "next";

import { AccountCommerceSurface } from "@/components/surfaces/account-commerce-surface";

export const metadata: Metadata = { title: "订单与权益", description: "查看订单和权益事实。" };

export default function AccountOrdersPage() {
  return <AccountCommerceSurface kind="orders" />;
}
