import { Button } from "mingli-web";

const row: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "12px",
  alignItems: "center",
};

export function Variants() {
  return (
    <div style={row}>
      <Button variant="primary">开始排盘</Button>
      <Button variant="secondary">保存草稿</Button>
      <Button variant="ghost">稍后再说</Button>
      <Button variant="destructive">删除档案</Button>
    </div>
  );
}

export function Loading() {
  return (
    <div style={row}>
      <Button variant="primary" loading>
        正在推演
      </Button>
      <Button variant="secondary" loading>
        正在保存
      </Button>
    </div>
  );
}

export function Disabled() {
  return (
    <div style={row}>
      <Button variant="primary" disabled>
        开始排盘
      </Button>
      <Button variant="secondary" disabled>
        保存草稿
      </Button>
      <Button variant="ghost" disabled>
        稍后再说
      </Button>
    </div>
  );
}

export function IconOnly() {
  return (
    <div style={row}>
      <Button variant="icon" aria-label="关闭面板">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M6 6l12 12M18 6L6 18"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </Button>
      <Button variant="icon" aria-label="收藏这份解读">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M12 3l2.6 5.8 6.4.7-4.8 4.3 1.3 6.2L12 17l-5.5 3 1.3-6.2L3 9.5l6.4-.7L12 3z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
        </svg>
      </Button>
    </div>
  );
}

export function AsChildLink() {
  return (
    <div style={row}>
      <Button variant="secondary" asChild>
        <a href="#methodology">查看方法论</a>
      </Button>
    </div>
  );
}
