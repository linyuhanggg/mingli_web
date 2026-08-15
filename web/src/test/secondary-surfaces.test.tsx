import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import ToolsPage from "@/app/tools/page";
import ToolDetailPage from "@/app/tools/[tool]/page";
import { AccountSurface, AuthSurface, CommerceSurface, PublicContentSurface } from "@/components/surfaces";
import {
  accountSurfaces,
  authSurfaces,
  commerceSurfaces,
  getToolSurface,
  publicContentSurfaces,
} from "@/lib/secondary-surfaces";

vi.mock("next/navigation", () => ({
  usePathname: () => "/auth/login",
}));

const requestJsonMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, requestJson: requestJsonMock };
});

describe("secondary surface families", () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
  });

  it("keeps auth fields visibly labelled, focusable, readonly, and non-submitting", () => {
    render(<AuthSurface surface={authSurfaces.login} />);

    const form = screen.getByRole("form", { name: "登录表单" });
    const identity = within(form).getByLabelText("手机或邮箱");
    const password = within(form).getByLabelText("密码");
    const submit = within(form).getByRole("button", { name: "登录暂未开放" });

    expect(identity).toHaveAttribute("readonly");
    expect(identity).not.toHaveAttribute("placeholder");
    expect(password).toHaveAttribute("readonly");
    expect(password).not.toHaveAttribute("placeholder");
    expect(submit).toBeDisabled();
    expect(within(form).getByText(/不会提交任何资料/)).toBeVisible();
    expect(screen.getByRole("status", { name: "登录暂不可用" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
  });

  it.each([
    ["登录", authSurfaces.login],
    ["注册", authSurfaces.register],
  ] as const)("keeps policy links reachable from %s", (_name, surface) => {
    render(<AuthSurface surface={surface} />);

    const policyNav = screen.getByRole("navigation", { name: "其他认证入口" });
    expect(within(policyNav).getByRole("link", { name: "查看隐私政策" })).toHaveAttribute(
      "href",
      "/privacy",
    );
    expect(within(policyNav).getByRole("link", { name: "查看服务条款" })).toHaveAttribute(
      "href",
      "/terms",
    );
  });

  it("renders account routes as a login requirement without fabricated records", () => {
    render(<AccountSurface surface={accountSurfaces.history} />);

    expect(screen.getByRole("heading", { level: 1, name: "任务、版本与报告历史" })).toBeVisible();
    expect(screen.getByRole("status", { name: "需要登录" })).toHaveAttribute(
      "data-state",
      "need-login",
    );
    expect(screen.getByRole("link", { name: "前往登录" })).toHaveAttribute("href", "/auth/login");
    expect(screen.queryByText(/示例报告|模拟记录|订单 #/)).not.toBeInTheDocument();
  });

  it("keeps commerce unavailable without prices, orders, or success claims", () => {
    render(<CommerceSurface surface={commerceSurfaces.checkout} />);

    const main = screen.getByRole("main");
    expect(within(main).getByRole("status", { name: "测试期未开放" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
    expect(within(main).getByText(/当前不会创建或保存订单/)).toBeVisible();
    expect(within(main).queryByText(/¥|支付成功|订单号/)).not.toBeInTheDocument();
  });

  it("keeps policy links reachable from checkout", () => {
    render(<CommerceSurface surface={commerceSurfaces.checkout} />);

    const policyNav = screen.getByRole("navigation", { name: "购买相关政策" });
    expect(within(policyNav).getByRole("link", { name: "查看隐私政策" })).toHaveAttribute(
      "href",
      "/privacy",
    );
    expect(within(policyNav).getByRole("link", { name: "查看服务条款" })).toHaveAttribute(
      "href",
      "/terms",
    );
  });

  it("uses a real empty state for an unpublished library", () => {
    render(<PublicContentSurface surface={publicContentSurfaces.library} />);

    expect(screen.getByRole("status", { name: "还没有已发布内容" })).toHaveAttribute(
      "data-state",
      "empty",
    );
    expect(screen.queryByRole("link", { name: /阅读全文/ })).not.toBeInTheDocument();
  });

  it("prebuilds an honest disabled search and topic filter for an unpublished library", () => {
    render(<PublicContentSurface surface={publicContentSurfaces.library} />);

    const search = screen.getByRole("search", { name: "知识内容筛选" });
    expect(within(search).getByRole("searchbox", { name: "搜索内容" })).toBeDisabled();
    expect(within(search).getByRole("combobox", { name: "按主题筛选" })).toBeDisabled();
    expect(within(search).getByRole("button", { name: "筛选" })).toBeDisabled();
    expect(within(search).getByRole("option", { name: "全部主题" })).toBeInTheDocument();
    expect(within(search).getByText(/发布内容后可用/)).toBeVisible();
  });

  it("renders only published CMS projections when the public content source is connected", async () => {
    requestJsonMock.mockResolvedValue({
      items: [
        {
          content_key: "library.intro",
          locale: "zh-CN",
          revision: 3,
          title: "公开文章标题",
          summary: "公开文章摘要",
          topic: "术数基础",
          source_title: "公开来源",
          source_url: "https://example.com/source",
          body: "公开文章正文",
          created_at: "2026-08-14T03:00:00Z",
        },
      ],
    });

    render(
      <PublicContentSurface
        contentSource={{ kind: "index", prefix: "library.", hrefBase: "/library" }}
        surface={publicContentSurfaces.library}
      />,
    );

    expect(await screen.findByText("公开文章正文")).toBeVisible();
    expect(screen.getByText("公开文章标题")).toBeVisible();
    expect(screen.getByText("公开文章摘要")).toBeVisible();
    expect(screen.getAllByText("术数基础").some((node) => node.tagName === "P")).toBe(true);
    expect(screen.getByRole("link", { name: "公开来源" })).toHaveAttribute(
      "href",
      "https://example.com/source",
    );
    expect(screen.getByRole("link", { name: "阅读 library.intro" })).toHaveAttribute(
      "href",
      "/library/intro",
    );
    expect(within(screen.getByRole("search", { name: "知识内容筛选" })).getByRole("searchbox", { name: "搜索内容" })).toBeEnabled();
    expect(within(screen.getByRole("search", { name: "知识内容筛选" })).getByRole("combobox", { name: "按主题筛选" })).toBeEnabled();
    expect(screen.queryByRole("status", { name: "还没有已发布内容" })).not.toBeInTheDocument();
    expect(requestJsonMock).toHaveBeenCalledWith(
      "/api/v1/content?prefix=library.&locale=zh-CN&limit=100",
    );
  });

  it("submits real library filters after a published projection loads", async () => {
    requestJsonMock
      .mockResolvedValueOnce({
        items: [
          {
            content_key: "library.intro",
            locale: "zh-CN",
            revision: 3,
            title: "公开文章标题",
            summary: "公开文章摘要",
            topic: "术数基础",
            source_title: null,
            source_url: null,
            body: "公开文章正文",
            created_at: "2026-08-14T03:00:00Z",
          },
        ],
      })
      .mockResolvedValue({
        items: [
          {
            content_key: "library.filtered",
            locale: "zh-CN",
            revision: 1,
            title: "筛选后的文章",
            summary: "筛选结果",
            topic: "方法与边界",
            source_title: null,
            source_url: null,
            body: "筛选后的正文",
            created_at: "2026-08-14T03:05:00Z",
          },
        ],
      });

    const user = (await import("@testing-library/user-event")).default.setup();
    render(
      <PublicContentSurface
        contentSource={{ kind: "index", prefix: "library.", hrefBase: "/library" }}
        surface={publicContentSurfaces.library}
      />,
    );

    const search = await screen.findByRole("search", { name: "知识内容筛选" });
    await user.type(within(search).getByRole("searchbox", { name: "搜索内容" }), "方法");
    await user.selectOptions(within(search).getByRole("combobox", { name: "按主题筛选" }), "方法与边界");
    await user.click(within(search).getByRole("button", { name: "筛选" }));

    expect(await screen.findByText("筛选后的文章")).toBeVisible();
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      "/api/v1/content?prefix=library.&locale=zh-CN&limit=100&q=%E6%96%B9%E6%B3%95&topic=%E6%96%B9%E6%B3%95%E4%B8%8E%E8%BE%B9%E7%95%8C",
    );
  });

  it("switches an article away from the unavailable title after a published projection loads", async () => {
    requestJsonMock.mockResolvedValue({
      content_key: "library.intro",
      locale: "zh-CN",
      revision: 3,
      body: "公开文章正文",
      created_at: "2026-08-14T03:00:00Z",
    });

    render(
      <PublicContentSurface
        contentSource={{ kind: "item", contentKey: "library.intro" }}
        surface={publicContentSurfaces.article}
      />,
    );

    expect(await screen.findByRole("heading", { level: 1, name: "公开知识文章" })).toBeVisible();
    expect(screen.queryByRole("heading", { level: 1, name: "这篇内容目前不可查看。" })).not.toBeInTheDocument();
  });

  it("keeps the daily product title when its published projection loads", async () => {
    requestJsonMock.mockResolvedValue({
      content_key: "daily",
      locale: "zh-CN",
      revision: 2,
      body: "今日公开内容",
      created_at: "2026-08-14T03:00:00Z",
    });

    render(
      <PublicContentSurface
        contentSource={{ kind: "item", contentKey: "daily" }}
        surface={publicContentSurfaces.daily}
      />,
    );

    expect(await screen.findByRole("heading", { level: 1, name: "每日" })).toBeVisible();
    expect(screen.queryByRole("heading", { level: 1, name: "公开知识文章" })).not.toBeInTheDocument();
    expect(screen.getByText("今日公开内容")).toBeVisible();
  });

  it("renders published tool projections from the tools index", async () => {
    requestJsonMock.mockResolvedValue({
      items: [
        {
          content_key: "tools.time-check",
          locale: "zh-CN",
          revision: 4,
          body: "寻时定盘的公开说明",
          created_at: "2026-08-14T03:00:00Z",
        },
      ],
    });

    render(<ToolsPage />);

    expect(await screen.findByText("寻时定盘的公开说明")).toBeVisible();
    expect(screen.getByRole("link", { name: "阅读 tools.time-check" })).toHaveAttribute(
      "href",
      "/tools/time-check",
    );
    expect(screen.queryByRole("status", { name: "工具能力暂不可用" })).not.toBeInTheDocument();
    expect(requestJsonMock).toHaveBeenCalledWith(
      "/api/v1/content?prefix=tools.&locale=zh-CN&limit=100",
    );
  });

  it("keeps a tool detail in its product language after its projection loads", async () => {
    requestJsonMock.mockResolvedValue({
      content_key: "tools.name",
      locale: "zh-CN",
      revision: 4,
      body: "姓名分析的公开说明",
      created_at: "2026-08-14T03:00:00Z",
    });

    const page = await ToolDetailPage({ params: Promise.resolve({ tool: "name" }) });
    render(page);

    expect(await screen.findByRole("heading", { level: 1, name: "姓名分析" })).toBeVisible();
    expect(screen.queryByRole("heading", { level: 1, name: "公开知识文章" })).not.toBeInTheDocument();
    expect(screen.getByText("姓名分析的公开说明")).toBeVisible();
    expect(requestJsonMock).toHaveBeenCalledWith("/api/v1/content/tools.name");
  });

  it("does not project CMS content into an unknown tool route", async () => {
    const page = await ToolDetailPage({ params: Promise.resolve({ tool: "private-route-value" }) });
    render(page);

    expect(screen.getByRole("heading", { level: 1, name: "这个工具入口尚未开放。" })).toBeVisible();
    expect(requestJsonMock).not.toHaveBeenCalledWith("/api/v1/content/tools.private-route-value");
  });

  it("does not echo unknown dynamic route segments into page copy", () => {
    const unknown = getToolSurface("private-route-value");

    expect(JSON.stringify(unknown)).not.toContain("private-route-value");
    expect(unknown.state).toBe("unavailable");
    expect(getToolSurface("time-check").title).toBe("寻时定盘");
  });

  it("labels the connected tool slices separately from unavailable tools", () => {
    const entries = publicContentSurfaces.tools.entries ?? [];
    expect(entries.find((entry) => entry.href === "/tools/rhythm")?.status).toBe("已接事实");
    expect(entries.find((entry) => entry.href === "/tools/five-elements")?.status).toBe(
      "已接有界事实",
    );
    expect(entries.find((entry) => entry.href === "/tools/chart-similarity")?.status).toBe(
      "已接有界事实",
    );
    expect(entries.find((entry) => entry.href === "/tools/time-check")?.status).toBe(
      "已接候选事实",
    );
    expect(entries.find((entry) => entry.href === "/tools/dream")?.status).toBe("适配中");
  });

  it.each([
    ["time-check", "寻时定盘", ["已知时间范围", "可核对事件"]],
    ["chart-similarity", "同盘匹配", ["左侧已确认盘面", "右侧已确认盘面"]],
    ["rhythm", "本命音律", ["本命资料", "音律侧重"]],
    ["five-elements", "五行事实与调候", ["已确认盘面", "关注主题"]],
    ["dream", "解梦", ["梦境内容", "现实背景"]],
    ["name", "姓名分析", ["姓名", "使用场景"]],
  ] as const)("exposes a readonly input boundary for %s", (slug, title, fields) => {
    render(<PublicContentSurface surface={getToolSurface(slug)} />);

    const form = screen.getByRole("form", { name: `${title}输入` });
    for (const label of fields) {
      expect(within(form).getByLabelText(label)).toHaveAttribute("readonly");
    }
    expect(within(form).getByRole("button", { name: "提交暂未开放" })).toBeDisabled();
    expect(within(form).getByText(/不会提交或保存资料/)).toBeVisible();
    expect(screen.getByRole("status", { name: `${title}暂不可用` })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
  });

  it("keeps visible focus rules and 44px targets in the family CSS module", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/surfaces/secondary-surfaces.module.css"),
      "utf8",
    );

    expect(css).toContain(":focus-visible");
    expect(css).toMatch(/outline:\s*2px solid var\(--color-focus\)/);
    expect(css).toMatch(/min-height:\s*2\.75rem/);
  });
});
