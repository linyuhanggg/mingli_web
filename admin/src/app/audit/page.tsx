import { AdminShell } from "@/components/admin-shell";
import ui from "@/components/ui.module.css";

export default function Page() {
  return (
    <AdminShell title="审计日志" duty="谁在何时对什么做了什么。只追加不改。">
      <section className={ui.paper}>
        <p className={ui.empty}>审计列表尚未接入。Phase B 接 audit-events API。</p>
      </section>
    </AdminShell>
  );
}
