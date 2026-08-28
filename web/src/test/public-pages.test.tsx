import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

import AccountPage from "@/app/account/page";
import AboutPage from "@/app/about/page";
import MethodologyPage from "@/app/methodology/page";
import PricingPage from "@/app/pricing/page";
import PrivacyPage from "@/app/privacy/page";
import SupportPage from "@/app/support/page";
import TermsPage from "@/app/terms/page";
import { PrivateShell } from "@/components/private-shell";
import { PublicPageShell } from "@/components/public-page-shell";

const { usePathnameMock } = vi.hoisted(() => ({ usePathnameMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  usePathname: usePathnameMock,
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
}));


function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

beforeEach(() => {
  usePathnameMock.mockReset();
  usePathnameMock.mockReturnValue("/");
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.includes("/api/v1/guest-sessions")) {
        return jsonResponse({ csrf_token: "stub-csrf-token" });
      }
      if (url.includes("/api/v1/account")) {
        return jsonResponse({ title: "Authentication required" }, 401);
      }
      return jsonResponse({ title: "Not Found" }, 404);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});


describe("public contract pages", () => {
  it("keeps /bazi/hepan breadcrumb semantics and 44px link targets", () => {
    usePathnameMock.mockReturnValue("/bazi/hepan");
    render(
      <PublicPageShell>
        <main id="main-content">八字合盘</main>
      </PublicPageShell>,
    );

    const breadcrumb = screen.getByRole("navigation", { name: "面包屑" });
    expect(within(breadcrumb).getByRole("link", { name: "首页" })).toHaveAttribute("href", "/");
    expect(within(breadcrumb).getByRole("link", { name: "八字" })).toHaveAttribute("href", "/bazi");
    expect(within(breadcrumb).getByText("八字合盘")).toHaveAttribute("aria-current", "page");

    const css = readFileSync(
      resolve(process.cwd(), "src/components/public-page-shell.module.css"),
      "utf8",
    );
    const tokens = readFileSync(resolve(process.cwd(), "../ui/tokens.css"), "utf8");
    expect(css).toMatch(
      /\.breadcrumb a\s*\{[^}]*display:\s*inline-flex[^}]*min-width:\s*var\(--ds-touch-min\)[^}]*min-height:\s*var\(--ds-touch-min\)/s,
    );
    expect(tokens).toMatch(/--ds-touch-min:\s*44px/);
  });

  it.each([
    ["/auth/login", "登录", "auth"],
    ["/invite/private-code", "邀请有礼", "private-code"],
    ["/share/private-share-id", "分享结果", "private-share-id"],
    ["/workbench/private-handle", "结果工作台", "private-handle"],
  ] as const)(
    "keeps %s breadcrumbs free of fictional parent links and opaque parameters",
    (pathname, currentLabel, privateValue) => {
      usePathnameMock.mockReturnValue(pathname);
      render(
        <PublicPageShell>
          <main id="main-content">受治理路由</main>
        </PublicPageShell>,
      );

      const breadcrumb = screen.getByRole("navigation", { name: "面包屑" });
      expect(within(breadcrumb).getAllByRole("link")).toHaveLength(1);
      expect(within(breadcrumb).getByRole("link", { name: "首页" })).toHaveAttribute("href", "/");
      expect(within(breadcrumb).getByText(currentLabel)).toHaveAttribute("aria-current", "page");
      expect(breadcrumb).not.toHaveTextContent(privateValue);
      expect(within(breadcrumb).queryByRole("link", { name: currentLabel })).not.toBeInTheDocument();
    },
  );

  it("fails closed instead of deriving breadcrumbs for an unmanaged route", () => {
    usePathnameMock.mockReturnValue("/unmanaged/private-value");
    render(
      <PublicPageShell>
        <main id="main-content">未知路由</main>
      </PublicPageShell>,
    );

    expect(screen.queryByRole("navigation", { name: "面包屑" })).not.toBeInTheDocument();
    expect(screen.queryByText("private-value")).not.toBeInTheDocument();
  });

  it("does not expose internal prebuilt-page wording on the about route", () => {
    render(<AboutPage />);
    const main = screen.getByRole("main");

    expect(main).not.toHaveTextContent("页面已预制");
    expect(within(main).getByText(/正式品牌、运营主体与团队信息尚未冻结/)).toBeVisible();
  });

  it("keeps one skip-target main landmark around the account page", () => {
    render(
      <PrivateShell>
        <AccountPage />
      </PrivateShell>,
    );
    const main = screen.getByRole("main");

    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(main).toHaveAttribute("id", "private-main");
    expect(main).toHaveAttribute("tabindex", "-1");
  });

  it("states the frozen free and one-off product promises", () => {
    render(<PricingPage />);
    const main = screen.getByRole("main");

    expect(within(main).getByText("¥0")).toBeVisible();
    expect(within(main).getByText("¥29.90")).toBeVisible();
    expect(within(main).getByText("¥9.90")).toBeVisible();
    expect(within(main).getByText(/7 天内 3 次同盘追问/)).toBeVisible();
    expect(within(main).getByText(/72 小时内 2 次同盘追问/)).toBeVisible();
    expect(
      within(main).getByText(/当前不开放自动续费、代币余额、充值钱包或永久无限 AI/),
    ).toBeVisible();
    expect(within(main).getByText(/按钮点击不会被写成已付款/)).toBeVisible();
  });

  it("explains calculation, evidence, accepted copy, and AI boundaries", () => {
    render(<MethodologyPage />);
    const main = screen.getByRole("main");
    const pipeline = within(main).getByRole("list", { name: "标准解读链" });

    expect(within(pipeline).getAllByRole("listitem")).toHaveLength(8);
    for (const step of [
      "输入确认",
      "档案版本",
      "计算事实",
      "事实简报",
      "候选成稿",
      "校验",
      "提交核心",
      "已接纳正文",
    ]) {
      expect(within(pipeline).getByText(step)).toBeVisible();
    }
    for (const internalLabel of [
      "Profile Version",
      "prepare",
      "Fact Brief",
      "complete",
      "Accepted",
    ]) {
      expect(within(main).queryByText(new RegExp(internalLabel, "i"))).not.toBeInTheDocument();
    }
    expect(within(main).getByRole("heading", { name: "接纳后原样交付" })).toBeVisible();
    expect(within(main).getByText(/交给核心完成接纳/)).toBeVisible();
    expect(within(main).getByText(/零命中就保持零/)).toBeVisible();
    expect(within(main).getByText(/已接纳正文不会被二次改写/)).toBeVisible();
    expect(within(main).getByText(/模型不能自行算盘/)).toBeVisible();
  });

  it("provides account, payment, report, export, deletion, and human support entries", () => {
    render(<SupportPage />);
    const main = screen.getByRole("main");

    for (const label of ["账号与登录", "付款与退款", "报告与追问", "导出与删除"]) {
      expect(within(main).getByRole("heading", { name: label })).toBeVisible();
    }
    expect(within(main).getByText(/人工支持/)).toBeVisible();
  });

  it("keeps support copy aligned with password-first identity flow", () => {
    render(<SupportPage />);
    const main = screen.getByRole("main");

    expect(within(main).getByText(/密码主登录/)).toBeVisible();
    expect(within(main).getByText(/OTP 用于注册验证、快捷登录和找回密码/)).toBeVisible();
    expect(within(main).getByText(/OTP 核验后设置密码/)).toBeVisible();
    expect(within(main).queryByText(/不需要另设注册密码/)).not.toBeInTheDocument();
  });

  it("treats birth data and readings as protected data and forbids local token storage", () => {
    render(<PrivacyPage />);
    const main = screen.getByRole("main");

    expect(within(main).getByText(/出生日期、时间、地点/)).toBeVisible();
    expect(within(main).getByText(/localStorage 不保存正式访问令牌/)).toBeVisible();
    expect(within(main).getByText(/访问、导出、更正与删除/)).toBeVisible();
  });

  it.each([
    ["隐私政策", PrivacyPage],
    ["服务条款", TermsPage],
  ] as const)("publishes an explicit preview policy state for %s", (_name, Page) => {
    render(<Page />);
    const metadata = screen.getByRole("region", { name: "政策版本" });

    expect(within(metadata).getByText("开发预览 v0.1")).toBeVisible();
    expect(within(metadata).getByText("未生效")).toBeVisible();
    expect(within(metadata).getByRole("link", { name: "前往登录" })).toHaveAttribute(
      "href",
      "/auth/login",
    );
    expect(within(metadata).getByRole("link", { name: "查看价格与交付" })).toHaveAttribute(
      "href",
      "/pricing",
    );
  });

  it("labels the service as traditional-culture reference with AI assistance", () => {
    render(<TermsPage />);
    const main = screen.getByRole("main");

    expect(within(main).getByText(/传统文化参考/)).toBeVisible();
    expect(within(main).getByText(/AI 生成或辅助生成/)).toBeVisible();
    expect(within(main).getByText(/不能替代医疗、法律、投资/)).toBeVisible();
  });
});
