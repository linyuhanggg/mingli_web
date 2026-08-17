import { Status } from "mingli-web";

const stack: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "12px",
};

export function Loading() {
  return (
    <div style={stack}>
      <Status state="loading" />
      <Status state="processing" title="正在推演八字" description="已完成 3/5 步，通常需要十几秒。" />
    </div>
  );
}

export function Resolved() {
  return (
    <div style={stack}>
      <Status state="success" title="解读已生成" description="共 6 个分区，可在下方逐段查看。" />
      <Status state="empty" title="还没有档案" description="新建一份出生资料后，这里会显示历史解读。" />
    </div>
  );
}

export function Problems() {
  return (
    <div style={stack}>
      <Status state="error" title="推演失败" description="上游算法超时，请稍后重试；本次不计费。" />
      <Status state="unavailable" title="太乙暂不可用" description="该体系尚未完成算法校验，暂未开放。" />
    </div>
  );
}

export function Gated() {
  return (
    <div style={stack}>
      <Status state="unauthorized" />
      <Status state="locked" title="解读已锁定" description="分享链接已过期，请让作者重新生成。" />
    </div>
  );
}
