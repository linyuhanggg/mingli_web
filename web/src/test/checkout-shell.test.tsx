import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import CheckoutPage from "@/app/checkout/page";
import CheckoutDetailPage from "@/app/checkout/[orderId]/page";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  recordConsent: vi.fn(),
  getAccount: vi.fn(() => new Promise(() => undefined)),
}));

describe("checkout two-page shell", () => {
  it("keeps /checkout on a 30px title without construction copy", () => {
    render(<CheckoutPage />);

    expect(screen.getByRole("heading", { level: 1, name: "结账" })).toBeVisible();
    expect(screen.getByText("当前没有可购买的商品。")).toBeVisible();
    expect(screen.getByRole("status", { name: "测试期未开放" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
    expect(screen.getByText(/当前不会创建或保存订单/)).toBeVisible();
    expect(screen.queryByText(/真实 Offer|占位价格|购买前先确认真实商品|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText(/¥|订单号/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^支付成功$/)).not.toBeInTheDocument();
  });

  it("keeps /checkout/[orderId] on a 30px title without guessing an order", async () => {
    const page = await CheckoutDetailPage({
      params: Promise.resolve({ orderId: "order-demo-1" }),
    });
    render(page);

    expect(screen.getByRole("heading", { level: 1, name: "订单" })).toBeVisible();
    expect(screen.getByText("查看这份订单。")).toBeVisible();
    expect(screen.getByRole("status", { name: "测试期未开放" })).toHaveAttribute(
      "data-state",
      "unavailable",
    );
    expect(screen.queryByText("order-demo-1")).not.toBeInTheDocument();
    expect(screen.queryByText(/订单快照必须来自服务端|§10|§6\.2/)).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.queryByText(/¥|订单号/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^支付成功$/)).not.toBeInTheDocument();
  });

  it("keeps policy links and does not start P6-002 consent from these pages", async () => {
    const { recordConsent } = await import("@/lib/api");
    render(<CheckoutPage />);

    const policyNav = screen.getByRole("navigation", { name: "购买相关政策" });
    expect(within(policyNav).getByRole("link", { name: "查看隐私政策" })).toHaveAttribute(
      "href",
      "/privacy",
    );
    expect(within(policyNav).getByRole("link", { name: "查看服务条款" })).toHaveAttribute(
      "href",
      "/terms",
    );
    expect(recordConsent).not.toHaveBeenCalled();
  });

  it("locks the shared header to --font-size-page", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/account-section-shell.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.header h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
  });

  it("does not put construction chrome on the two production files", () => {
    for (const file of [
      "src/app/checkout/page.tsx",
      "src/app/checkout/[orderId]/page.tsx",
      "src/components/surfaces/commerce-surface.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/development_code|调试码/);
      expect(source).not.toMatch(/SecondarySurfaceFrame|authGrid|§10|§6\.2/);
      expect(source).not.toMatch(/AppPageHeader|recordConsent/);
    }
    expect(
      readFileSync(resolve(process.cwd(), "src/components/surfaces/commerce-surface.tsx"), "utf8"),
    ).toMatch(/AccountSectionShell/);
  });
});
