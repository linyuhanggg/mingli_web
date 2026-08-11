import { AdminShell } from "@/components/admin-shell";
import ui from "@/components/ui.module.css";

export default function Page() {
  return (
    <AdminShell title="订单支付" duty="查订单与支付事实。客户端回跳不算到账。">
      <section className={ui.paper}>
        <p className={ui.empty}>订单列表尚未接入。Phase B 接 Admin orders API。</p>
      </section>
    </AdminShell>
  );
}
