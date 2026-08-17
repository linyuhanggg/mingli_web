import { Button, Drawer, Field } from "mingli-web";

const body: React.CSSProperties = {
  margin: "0 0 16px",
  color: "var(--color-text-secondary)",
  fontSize: "var(--font-size-body)",
  lineHeight: 1.7,
};

export function BottomSheet() {
  return (
    <Drawer
      open
      onOpenChange={() => {}}
      side="bottom"
      title="校正出生时刻"
      description="真太阳时换算会影响时柱，跨界时请以出生地经度为准。"
      trigger={<Button variant="secondary">校正时刻</Button>}
    >
      <p style={body}>当前按 Asia/Shanghai 换算，偏移 −14 分钟，时柱未跨界。</p>
      <Field label="出生时刻" description="24 小时制，精确到分钟。">
        <input type="text" name="birth-time" defaultValue="07:35" />
      </Field>
      <div style={{ display: "flex", gap: "12px", marginTop: "20px" }}>
        <Button variant="primary">保存并重排</Button>
        <Button variant="ghost">取消</Button>
      </div>
    </Drawer>
  );
}
