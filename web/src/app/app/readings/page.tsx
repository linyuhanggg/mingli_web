import { FileClock, ShieldCheck } from "lucide-react";
import Link from "next/link";

import styles from "@/components/app-surface.module.css";
import { StatusPanel } from "@/components/status-panel";


const states = [
  ["待付款", "只代表订单已建立；未收到渠道确认，不会授予权益。", "idle"],
  ["正在确认付款", "客户端回跳后等待服务端验签或主动查单。", "processing"],
  ["生成与校验中", "已付款也不等于已交付；正文仍须通过事实与结构校验。", "processing"],
  ["暂时未完成", "权益未核销，可继续生成或进入人工处理。", "error"],
  ["已交付", "只在 Accepted Copy 落库且 Fulfillment 为 DELIVERED 时出现。", "success"],
] as const;

export default function ReadingsPage() {
  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1>历史里保存的是版本，不是一串聊天消息。</h1>
        <div>
          <p>每个解读根可以包含初次解读、核对后的新版本与同盘追问。旧正文保持可回看，不会被新答案覆盖。</p>
          <div className={styles.metaLine}>
            <span><FileClock aria-hidden="true" size={15} /> 解读版本可回看</span>
            <span><ShieldCheck aria-hidden="true" size={15} /> 权益与交付分开</span>
          </div>
        </div>
      </header>

      <StatusPanel
        state="empty"
        title="目前没有真实解读记录"
        description="完成档案或一事一问并获得服务端 Accepted Copy 后，历史才会显示。结构示例不会混入你的真实记录。"
        actionHref="/app/profile/new"
        actionLabel="先建立档案"
      />

      <section className={styles.paper} aria-labelledby="status-title">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="status-title">交付状态必须拆开说</h2>
            <p>下面是界面状态说明，不是你的订单或解读历史。</p>
          </div>
        </div>
        <ul className={styles.legendList}>
          {states.map(([label, description, state]) => (
            <li key={label}>
              <span className={styles.stateTag} data-state={state}>{label}</span>
              <p>{description}</p>
            </li>
          ))}
        </ul>
        <div className={styles.actionRow}>
          <Link className={styles.secondaryButton} href="/app/readings/demo">查看解读详情结构示例</Link>
        </div>
      </section>
    </div>
  );
}
