import { Button, Dialog } from "mingli-web";

const body: React.CSSProperties = {
  margin: 0,
  color: "var(--color-text-secondary)",
  fontSize: "var(--font-size-body)",
  lineHeight: 1.7,
};

export function Confirm() {
  return (
    <Dialog
      open
      onOpenChange={() => {}}
      title="删除这份档案？"
      description="档案删除后，基于它生成的历史解读也会一并移除，且无法恢复。"
      trigger={<Button variant="destructive">删除档案</Button>}
    >
      <p style={body}>如果只是想暂时隐藏，可以改用归档，归档后仍可随时恢复。</p>
      <div style={{ display: "flex", gap: "12px", marginTop: "20px" }}>
        <Button variant="destructive">确认删除</Button>
        <Button variant="ghost">取消</Button>
      </div>
    </Dialog>
  );
}
