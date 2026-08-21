import type { Metadata } from "next";

import { ToolsIndexView, ToolsPageFrame } from "@/components/tool-page";

export const metadata: Metadata = { title: "工具", description: "只展示已经开放的入口。" };

export default function ToolsPage() {
  return (
    <ToolsPageFrame intro="只展示已经开放的入口。" title="工具">
      <ToolsIndexView />
    </ToolsPageFrame>
  );
}
