import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductInputForm } from "@/components/task/product-input-form";
import { getProductDefinition } from "@/products/catalog";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  listProfiles: vi.fn().mockResolvedValue({ profiles: [] }),
}));

afterEach(cleanup);

describe("product validation labels", () => {
  it.each([
    ["liuyao", "起卦方式"],
    ["meihua", "判断侧重"],
  ] as const)(
    "keeps the %s error summary aligned with its visible labels",
    async (productId, focusLabel) => {
      const user = userEvent.setup();
      render(
        <ProductInputForm
          onConfirm={vi.fn()}
          product={getProductDefinition(productId)}
        />,
      );

      await user.clear(screen.getByLabelText("事件时区"));
      await user.click(screen.getByRole("button", { name: /起卦/ }));

      const summary = await screen.findByRole("alert", { name: "请先修正以下输入" });
      const summaryLinks = within(summary).getAllByRole("link");
      const summaryLabels = summaryLinks.map((link) => link.textContent);

      expect(screen.getByLabelText("事件地点")).toBeVisible();
      expect(screen.getByLabelText("事件时区")).toBeVisible();
      expect(screen.getByLabelText(focusLabel)).toBeVisible();
      expect(summaryLabels).toContain("事件地点");
      expect(summaryLabels).toContain("事件时区");
      expect(summaryLabels).toContain(focusLabel);
      expect(summaryLabels).not.toContain("出生地点");
      expect(summaryLabels).not.toContain("时区");
      if (productId === "liuyao") {
        expect(screen.getByText("请选择起卦方式")).toBeVisible();
        expect(screen.queryByText("请选择场景或侧重")).not.toBeInTheDocument();
        expect(summaryLabels).not.toContain("判断侧重");
      }
    },
  );

  it("keeps the fengshui location error summary aligned with the visible label", async () => {
    const user = userEvent.setup();
    render(
      <ProductInputForm
        onConfirm={vi.fn()}
        product={getProductDefinition("fengshui")}
      />,
    );

    await user.click(screen.getByRole("button", { name: /起盘/ }));

    const summary = await screen.findByRole("alert", { name: "请先修正以下输入" });
    const summaryLabels = within(summary)
      .getAllByRole("link")
      .map((link) => link.textContent);

    expect(screen.getByLabelText("空间所在地点")).toBeVisible();
    expect(screen.getByText("请填写空间所在地点")).toBeVisible();
    expect(summaryLabels).toContain("空间所在地点");
    expect(summaryLabels).not.toContain("出生地点");
  });
});
