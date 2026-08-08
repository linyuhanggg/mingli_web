import { StatusPanel } from "@/components/status-panel";


export default function AppLoading() {
  return (
    <StatusPanel
      state="loading"
      title="正在载入私人档案"
      description="正在读取当前授权下的档案与解读状态；页面不会用占位结果冒充真实内容。"
    />
  );
}
