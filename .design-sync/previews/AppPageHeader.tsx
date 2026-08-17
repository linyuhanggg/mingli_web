import { AppPageHeader } from "mingli-web";

export function Basic() {
  return (
    <AppPageHeader
      title="推演历史"
      description="按时间顺序查看已生成的解读，可随时归档或删除。"
    />
  );
}

export function WithMeta() {
  return (
    <AppPageHeader
      title="订单与权益"
      description="查看已购买的解读次数与剩余额度。"
      meta={<span>剩余 3 次 · 到期日 2026-12-31</span>}
    />
  );
}

export function Stacked() {
  return (
    <AppPageHeader
      title="账户设置"
      description="管理登录方式、通知偏好与数据导出。"
      stacked
    />
  );
}
