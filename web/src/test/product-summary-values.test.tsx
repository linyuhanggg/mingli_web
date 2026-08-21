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

describe("product submit summary values", () => {
  it("uses the visible Taiyi focus option label in the submit summary", async () => {
    const user = userEvent.setup();
    render(
      <ProductInputForm
        onConfirm={vi.fn()}
        product={getProductDefinition("taiyi")}
      />,
    );

    await user.type(screen.getByLabelText("当前问题"), "今年事业是否适合换岗");
    const focusSelect = screen.getByLabelText("判断侧重") as HTMLSelectElement;
    await user.selectOptions(focusSelect, "outcome");

    expect(focusSelect.selectedOptions[0]).toHaveTextContent("年度结果");

    const summary = screen.getByRole("region", { name: "提交前摘要" });
    const focusTerm = within(summary).getByText("侧重");
    expect(focusTerm.nextElementSibling).toHaveTextContent("年度结果");
    expect(within(summary).queryByText("结果观察")).not.toBeInTheDocument();
  });

  it("uses the visible selection focus option label in the submit summary", async () => {
    const user = userEvent.setup();
    render(
      <ProductInputForm
        onConfirm={vi.fn()}
        product={getProductDefinition("selection")}
      />,
    );

    await user.type(screen.getByLabelText("当前问题"), "今年事业是否适合换岗");
    const focusSelect = screen.getByLabelText("判断侧重") as HTMLSelectElement;
    await user.selectOptions(focusSelect, "timing");

    expect(focusSelect.selectedOptions[0]).toHaveTextContent("时间排序");

    const summary = screen.getByRole("region", { name: "提交前摘要" });
    const focusTerm = within(summary).getByText("侧重");
    expect(focusTerm.nextElementSibling).toHaveTextContent("时间排序");
    expect(within(summary).queryByText("时机观察")).not.toBeInTheDocument();
  });
});
