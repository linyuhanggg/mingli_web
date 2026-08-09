import { render, screen, within } from "@testing-library/react";

import AccountPage from "@/app/account/page";
import MethodologyPage from "@/app/methodology/page";
import PricingPage from "@/app/pricing/page";
import PrivacyPage from "@/app/privacy/page";
import SupportPage from "@/app/support/page";
import TermsPage from "@/app/terms/page";


describe("public contract pages", () => {
  it("exposes a skip-target main landmark on the account page", () => {
    render(<AccountPage />);
    const main = screen.getByRole("main");

    expect(main).toHaveAttribute("id", "main-content");
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
    expect(within(main).getByText(/当前不开放自动续费/)).toBeVisible();
  });

  it("explains calculation, evidence, accepted copy, and AI boundaries", () => {
    render(<MethodologyPage />);
    const main = screen.getByRole("main");
    const pipeline = within(main).getByRole("list", { name: "标准解读链" });

    expect(within(pipeline).getAllByRole("listitem")).toHaveLength(8);
    expect(within(pipeline).getByText("prepare")).toBeVisible();
    expect(within(pipeline).getByText("Fact Brief")).toBeVisible();
    expect(within(main).getByText(/零命中就保持零/)).toBeVisible();
    expect(within(main).getByText(/已接纳正文/)).toBeVisible();
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

  it("treats birth data and readings as protected data and forbids local token storage", () => {
    render(<PrivacyPage />);
    const main = screen.getByRole("main");

    expect(within(main).getByText(/出生日期、时间、地点/)).toBeVisible();
    expect(within(main).getByText(/localStorage 不保存正式访问令牌/)).toBeVisible();
    expect(within(main).getByText(/访问、导出、更正与删除/)).toBeVisible();
  });

  it("labels the service as traditional-culture reference with AI assistance", () => {
    render(<TermsPage />);
    const main = screen.getByRole("main");

    expect(within(main).getByText(/传统文化参考/)).toBeVisible();
    expect(within(main).getByText(/AI 生成或辅助生成/)).toBeVisible();
    expect(within(main).getByText(/不能替代医疗、法律、投资/)).toBeVisible();
  });
});
