import { AdminShell } from "@/components/admin-shell";
import ui from "@/components/ui.module.css";

export default function Page() {
  return (
    <AdminShell title="退款审批" duty="审批前先看权益影响。通过/驳回都要原因。">
      <section className={ui.paper}>
        <p className={ui.empty}>退款队列尚未接入。Phase C 接审批写路径。</p>
      </section>
    </AdminShell>
  );
}
