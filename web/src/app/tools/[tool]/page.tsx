import type { Metadata } from "next";

import { ChartSimilarityFlow } from "@/components/chart-similarity-flow";
import { FiveElementsFactsFlow } from "@/components/five-elements-facts-flow";
import { RhythmFactsFlow } from "@/components/rhythm-facts-flow";
import { TimeCheckFlow } from "@/components/time-check-flow";
import { ToolBoundaryView, ToolsPageFrame } from "@/components/tool-page";
import { getToolSurface } from "@/lib/secondary-surfaces";

export const metadata: Metadata = { title: "工具", description: "只展示这项工具已经开放的能力。" };

const connected = {
  "time-check": TimeCheckFlow,
  "chart-similarity": ChartSimilarityFlow,
  rhythm: RhythmFactsFlow,
  "five-elements": FiveElementsFactsFlow,
} as const;

export default async function ToolDetailPage({
  params,
}: {
  params: Promise<{ tool: string }>;
}) {
  const { tool } = await params;
  const surface = getToolSurface(tool);
  const Connected = tool in connected ? connected[tool as keyof typeof connected] : null;

  return (
    <ToolsPageFrame
      backHref="/tools"
      backLabel="返回工具"
      intro={surface.intro}
      title={surface.title}
    >
      {Connected ? <Connected /> : <ToolBoundaryView slug={tool} />}
    </ToolsPageFrame>
  );
}
