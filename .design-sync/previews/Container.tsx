import { Container } from "mingli-web";

export function Basic() {
  return (
    <Container
      style={{
        border: "1px dashed var(--color-border-strong)",
        padding: "var(--space-lg)",
      }}
    >
      <p style={{ margin: 0 }}>
        Container 把内容夹在页面统一的最大宽度里，页面正文一律用它包裹。
      </p>
    </Container>
  );
}
