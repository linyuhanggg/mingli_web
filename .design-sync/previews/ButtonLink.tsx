import { ButtonLink } from "mingli-web";

const row: React.CSSProperties = { display: "flex", flexWrap: "wrap", gap: "12px" };

export function Variants() {
  return (
    <div style={row}>
      <ButtonLink href="/bazi" variant="primary">
        开始排盘
      </ButtonLink>
      <ButtonLink href="/methodology" variant="secondary">
        查看方法论
      </ButtonLink>
      <ButtonLink href="/support" variant="text">
        帮助与支持
      </ButtonLink>
    </div>
  );
}
