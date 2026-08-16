import { CommerceSurface } from "@/components/surfaces";
import { commerceSurfaces } from "@/lib/secondary-surfaces";

export default async function CheckoutDetailPage({
  params,
}: {
  params: Promise<{ orderId: string }>;
}) {
  await params;
  return <CommerceSurface surface={commerceSurfaces.order} />;
}
