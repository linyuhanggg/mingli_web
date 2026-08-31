import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DailyPage from "@/app/daily/page";
import LibraryPage from "@/app/library/page";
import LibraryArticlePage from "@/app/library/[slug]/page";
import ToolsPage from "@/app/tools/page";
import ToolDetailPage from "@/app/tools/[tool]/page";
import { ApiError } from "@/lib/api";
import { getToolSurface, publicContentSurfaces } from "@/lib/secondary-surfaces";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  requestJson: vi.fn(),
  listProfiles: vi.fn(),
  createIdempotencyKey: vi.fn(),
  formatProfileOption: vi.fn((profile: { version: number }) => `档案 ${profile.version}`),
  startTimeCheckReading: vi.fn(),
  startChartSimilarityReading: vi.fn(),
  startRhythmReading: vi.fn(),
  startFiveElementsFactsReading: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/daily",
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
  listProfiles: api.listProfiles,
  createIdempotencyKey: api.createIdempotencyKey,
  formatProfileOption: api.formatProfileOption,
  startTimeCheckReading: api.startTimeCheckReading,
  startChartSimilarityReading: api.startChartSimilarityReading,
  startRhythmReading: api.startRhythmReading,
  startFiveElementsFactsReading: api.startFiveElementsFactsReading,
}));

vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  requestJson: api.requestJson,
}));

beforeEach(() => {
  api.getAccount.mockReset();
  api.requestJson.mockReset();
  api.listProfiles.mockReset();
  api.createIdempotencyKey.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.listProfiles.mockResolvedValue({ profiles: [] });
  api.createIdempotencyKey.mockReturnValue("tool-intent-1");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("retired daily / library and tool failure states", () => {
  it("keeps /daily on the retired replacement surface without a content request", () => {
    render(<DailyPage />);

    expect(screen.getByRole("heading", { name: "每日已下线" })).toBeVisible();
    expect(screen.getByRole("link", { name: "前往人生 K 线" })).toHaveAttribute(
      "href",
      "/life-kline",
    );
    expect(api.requestJson).not.toHaveBeenCalled();
  });

  it("keeps /library and its slug on the same retired replacement surface", async () => {
    render(<LibraryPage />);
    expect(screen.getByRole("heading", { name: "知识内容已下线" })).toBeVisible();
    expect(api.requestJson).not.toHaveBeenCalled();

    render(await LibraryArticlePage({ params: Promise.resolve({ slug: "intro" }) }));
    expect(screen.getAllByRole("heading", { name: "知识内容已下线" })).toHaveLength(2);
    expect(api.requestJson).not.toHaveBeenCalled();
  });

  it("says 读取失败，请重试 on an opened tool when profiles fail to load", async () => {
    api.listProfiles.mockRejectedValue(new Error("profile boom"));
    const page = await ToolDetailPage({ params: Promise.resolve({ tool: "time-check" }) });
    render(page);

    expect(await screen.findByRole("alert")).toHaveTextContent("读取失败，请重试");
    expect(screen.queryByText("还没有可用的档案")).not.toBeInTheDocument();
    expect(screen.queryByText("profile boom")).not.toBeInTheDocument();
  });
});

describe("library / tools product shell", () => {
  it("does not wrap /library or /tools in AuthShell", () => {
    for (const file of [
      "src/app/library/page.tsx",
      "src/app/library/[slug]/page.tsx",
      "src/components/library-page.tsx",
      "src/app/tools/page.tsx",
      "src/app/tools/[tool]/page.tsx",
      "src/components/tool-page.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source, file).not.toContain("AuthShell");
      expect(source, file).not.toContain("其他认证入口");
    }
  });

  it("marks unopened tool entries as disabled with no href", () => {
    render(<ToolsPage />);

    expect(screen.queryByRole("navigation", { name: "其他认证入口" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "解梦" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "姓名分析" })).toBeDisabled();
    expect(screen.queryByRole("link", { name: "解梦" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "姓名分析" })).not.toBeInTheDocument();
    expect(screen.getAllByText("尚未开放").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "寻时定盘" })).toHaveAttribute("href", "/tools/time-check");
  });
});

describe("opened tools 去建档", () => {
  it("sends 去建档 to /account/profiles/new on an opened tool", async () => {
    const page = await ToolDetailPage({ params: Promise.resolve({ tool: "time-check" }) });
    render(page);

    expect(await screen.findByRole("link", { name: "去建档" })).toHaveAttribute(
      "href",
      "/account/profiles/new",
    );
    expect(screen.queryByRole("link", { name: "去建档" })).not.toHaveAttribute(
      "href",
      "/app/profile/new",
    );
  });

  it("keeps every opened tool 去建档 off /app/profile/new", () => {
    for (const file of [
      "src/components/time-check-flow.tsx",
      "src/components/chart-similarity-flow.tsx",
      "src/components/rhythm-facts-flow.tsx",
      "src/components/five-elements-facts-flow.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source, file).toContain('href="/account/profiles/new">去建档');
      expect(source, file).not.toContain('href="/app/profile/new">去建档');
    }
  });
});

const constructionPhrases = [
  "接通",
  "未接通",
  "拼接临时",
  "旺衰、喜忌、用神结论仍未接通。",
  "内容服务接通前不拼接临时解释。",
  "确定性规则接通前不输出结论。",
] as const;

const productionPageFiles = [
  "src/app/daily/page.tsx",
  "src/components/daily-page.tsx",
  "src/app/library/page.tsx",
  "src/app/library/[slug]/page.tsx",
  "src/components/library-page.tsx",
  "src/app/tools/page.tsx",
  "src/app/tools/[tool]/page.tsx",
  "src/components/tool-page.tsx",
  "src/components/five-elements-facts-flow.tsx",
] as const;

function expectNoConstructionCopy(text: string, label: string) {
  for (const phrase of constructionPhrases) {
    expect(text, `${label} still has ${phrase}`).not.toContain(phrase);
  }
}

describe("production daily / library / tools copy", () => {
  it("does not keep construction phrases on production pages", async () => {
    api.requestJson.mockResolvedValue({ items: [] });

    const { container: tools, unmount: unmountTools } = render(<ToolsPage />);
    expectNoConstructionCopy(tools.textContent ?? "", "/tools");
    expect(
      screen.getByText("展示服务端五行库存与调候适用性事实。旺衰、喜忌、用神没有可展示的结论。"),
    ).toBeVisible();
    expect(screen.getByText("尚未开放。没有可展示的解梦结论。")).toBeVisible();
    expect(screen.getByText("尚未开放。没有可展示的姓名结论。")).toBeVisible();
    unmountTools();

    for (const slug of ["five-elements", "dream", "name"] as const) {
      const page = await ToolDetailPage({ params: Promise.resolve({ tool: slug }) });
      const { container, unmount } = render(page);
      expectNoConstructionCopy(container.textContent ?? "", `/tools/${slug}`);
      unmount();
    }

    const { container: daily, unmount: unmountDaily } = render(<DailyPage />);
    expect(screen.getByRole("heading", { name: "每日已下线" })).toBeVisible();
    expectNoConstructionCopy(daily.textContent ?? "", "/daily");
    unmountDaily();

    const { container: library, unmount: unmountLibrary } = render(<LibraryPage />);
    expect(screen.getByRole("heading", { name: "知识内容已下线" })).toBeVisible();
    expectNoConstructionCopy(library.textContent ?? "", "/library");
    unmountLibrary();
  });

  it("does not leave the retired construction sentences in production sources", () => {
    for (const file of productionPageFiles) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expectNoConstructionCopy(source, file);
    }

    const catalog = readFileSync(resolve(process.cwd(), "src/lib/secondary-surfaces.ts"), "utf8");
    expect(catalog).not.toContain("旺衰、喜忌、用神结论仍未接通。");
    expect(catalog).not.toContain("内容服务接通前不拼接临时解释。");
    expect(catalog).not.toContain("确定性规则接通前不输出结论。");

    expectNoConstructionCopy(
      JSON.stringify(publicContentSurfaces.tools.entries ?? []),
      "tools entries",
    );
    for (const slug of ["five-elements", "dream", "name"] as const) {
      const surface = getToolSurface(slug);
      expectNoConstructionCopy(surface.intro, `${slug} intro`);
      expectNoConstructionCopy(JSON.stringify(surface.form ?? {}), `${slug} form`);
    }
  });
});
