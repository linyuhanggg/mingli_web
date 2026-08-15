import { Container } from "@/components/container";
import { ChartSimilarityFlow } from "@/components/chart-similarity-flow";
import { FiveElementsFactsFlow } from "@/components/five-elements-facts-flow";
import { RhythmFactsFlow } from "@/components/rhythm-facts-flow";
import { TimeCheckFlow } from "@/components/time-check-flow";
import { PublicContentSurface } from "@/components/surfaces";
import { PublicPageShell } from "@/components/public-page-shell";
import { getToolContentSource, getToolSurface } from "@/lib/secondary-surfaces";

export default async function ToolDetailPage({
  params,
}: {
  params: Promise<{ tool: string }>;
}) {
  const { tool } = await params;
  if (tool === "five-elements") {
    return (
      <PublicPageShell>
        <main id="main-content" tabIndex={-1}>
          <Container>
            <FiveElementsFactsFlow />
          </Container>
        </main>
      </PublicPageShell>
    );
  }
  if (tool === "rhythm") {
    return (
      <PublicPageShell>
        <main id="main-content" tabIndex={-1}>
          <Container>
            <RhythmFactsFlow />
          </Container>
        </main>
      </PublicPageShell>
    );
  }
  if (tool === "chart-similarity") {
    return (
      <PublicPageShell>
        <main id="main-content" tabIndex={-1}>
          <Container>
            <ChartSimilarityFlow />
          </Container>
        </main>
      </PublicPageShell>
    );
  }
  if (tool === "time-check") {
    return (
      <PublicPageShell>
        <main id="main-content" tabIndex={-1}>
          <Container>
            <TimeCheckFlow />
          </Container>
        </main>
      </PublicPageShell>
    );
  }
  return (
    <PublicContentSurface
      contentSource={getToolContentSource(tool)}
      surface={getToolSurface(tool)}
    />
  );
}
