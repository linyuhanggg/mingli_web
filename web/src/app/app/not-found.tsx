import { StatusPanel } from "@/components/status-panel";


export default function AppNotFound() {
  return (
    <>
      <h1 className="sr-only">没有找到这份私人记录</h1>
      <StatusPanel
        state="empty"
        title="没有找到这份私人记录"
        description="记录可能不存在、已删除，或当前设备会话没有访问权限。私人资源不会因为知道 URL 就自动开放。"
        actionHref="/app/readings"
        actionLabel="返回解读历史"
      />
    </>
  );
}
