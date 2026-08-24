import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { liuyaoS6IncompleteMessage } from "@/components/task/liuyao-entry-copy";
import { mapLiuyaoCastingRejection } from "@/components/task/liuyao-casting-reject";
import { ProductTaskPage } from "@/components/task/product-task-page";
import { ApiError } from "@/lib/api";

const mockStartLiuyaoReading = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/liuyao",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: vi.fn(() => new Promise(() => undefined)),
  getCapabilityProjection: vi.fn().mockResolvedValue({
    runtime_release_profile: "v53-time-check",
    source_status: "available",
    capabilities: [],
  }),
  listProfiles: vi.fn().mockResolvedValue({ profiles: [] }),
  startLiuyaoReading: mockStartLiuyaoReading,
}));

afterEach(() => {
  cleanup();
  mockStartLiuyaoReading.mockReset();
});

const FILLED = ["old-yang", "young-yin", "young-yang", "old-yin", "young-yin", "young-yang"] as const;

function lineRow(index: number) {
  const row = document.getElementById(`liuyao-line-${index}`);
  if (!row) throw new Error(`missing liuyao-line-${index}`);
  return row;
}

async function fillCompleteCast(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("当前问题"), "这次求财如何");
  await user.selectOptions(screen.getByLabelText("起卦方式"), "manual");
  fireEvent.change(screen.getByLabelText("事件时间"), {
    target: { value: "2026-08-21T22:10" },
  });
  await user.type(screen.getByLabelText("事件地点"), "上海市");
  for (let index = 0; index < 6; index += 1) {
    await user.click(within(lineRow(index)).getByRole("radio", { name: LINE_LABELS[index] }));
  }
}

const LINE_LABELS = [
  "老阳（9 · 动）",
  "少阴（8）",
  "少阳（7）",
  "老阴（6 · 动）",
  "少阴（8）",
  "少阳（7）",
] as const;

describe("liuyao S6 incomplete-cast mapper", () => {
  it("maps compiler tokens to the first missing S1 line without leaking engineering copy", () => {
    expect(
      mapLiuyaoCastingRejection(
        new ApiError("Invalid request", 400, "liuyao cast must be six bottom-up tosses or digital_coin"),
        ["old-yang", "", "", "", "", ""],
      ),
    ).toEqual({ index: 1, message: liuyaoS6IncompleteMessage(1) });
    expect(
      mapLiuyaoCastingRejection(
        new ApiError("Invalid request", 400, "liuyao toss values must be integers in 6..9"),
        FILLED,
      ),
    ).toEqual({ index: 0, message: liuyaoS6IncompleteMessage(0) });
  });

  it("uses pydantic loc on 422 to the named missing line", () => {
    const detail = [{ loc: ["body", "cast", 3], msg: "Field required" }];
    expect(
      mapLiuyaoCastingRejection(
        new ApiError("服务暂时不可用，请稍后重试", 422, JSON.stringify(detail)),
        FILLED,
      ),
    ).toEqual({ index: 3, message: liuyaoS6IncompleteMessage(3) });
  });

  it("falls back to the first empty line when the compiler only says Invalid request", () => {
    expect(
      mapLiuyaoCastingRejection(new ApiError("Invalid request", 400), [
        "old-yang",
        "young-yin",
        "",
        "",
        "",
        "",
      ]),
    ).toEqual({ index: 2, message: liuyaoS6IncompleteMessage(2) });
  });

  it("does not invent GAP-LY or steal question_class / 503", () => {
    expect(
      mapLiuyaoCastingRejection(
        new ApiError("unsupported Liuyao question class: 'health'", 400),
        FILLED,
      ),
    ).toBeNull();
    expect(
      mapLiuyaoCastingRejection(new ApiError("Runtime release unavailable", 503), FILLED),
    ).toBeNull();
    expect(liuyaoS6IncompleteMessage(0)).not.toMatch(/GAP-LY|question_class|cast/);
  });
});

describe("/liuyao S6 incomplete cast stays on S1", () => {
  it("points a compiler rejection at the first missing line and hides engineering terms", async () => {
    mockStartLiuyaoReading.mockRejectedValue(
      new ApiError("Invalid request", 400, "liuyao cast must be six bottom-up tosses or digital_coin"),
    );
    const user = userEvent.setup();
    render(<ProductTaskPage productId="liuyao" />);
    await fillCompleteCast(user);
    await user.click(screen.getByRole("button", { name: /^立即起卦 · 查看本卦与变卦$/ }));

    const message = liuyaoS6IncompleteMessage(0);
    const nearby = await screen.findByText(message);
    expect(nearby).toBeVisible();
    expect(nearby).toHaveAttribute("id", "liuyao-line-0-error");
    expect(lineRow(0)).toHaveAccessibleDescription(message);
    expect(lineRow(0)).toHaveFocus();
    expect(screen.getByRole("form", { name: /六爻/ })).toBeVisible();
    expect(screen.queryByText(/Invalid request/)).not.toBeInTheDocument();
    expect(screen.queryByText(/bottom-up/)).not.toBeInTheDocument();
    expect(screen.queryByText(/digital_coin/)).not.toBeInTheDocument();
    expect(screen.queryByText(/GAP-LY/)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /工作台/ })).not.toBeInTheDocument();
  });

  it("points a loc-indexed 422 at 四爻", async () => {
    mockStartLiuyaoReading.mockRejectedValue(
      new ApiError(
        "服务暂时不可用，请稍后重试",
        422,
        JSON.stringify([{ loc: ["body", "cast", 3], msg: "Field required" }]),
      ),
    );
    const user = userEvent.setup();
    render(<ProductTaskPage productId="liuyao" />);
    await fillCompleteCast(user);
    await user.click(screen.getByRole("button", { name: /^立即起卦 · 查看本卦与变卦$/ }));

    const message = liuyaoS6IncompleteMessage(3);
    const nearby = await screen.findByText(message);
    expect(nearby).toHaveAttribute("id", "liuyao-line-3-error");
    expect(lineRow(3)).toHaveAccessibleDescription(message);
    expect(lineRow(3)).toHaveFocus();
    expect(screen.queryByText(/Field required/)).not.toBeInTheDocument();
  });

  it("does not steal 503 into a line error", async () => {
    mockStartLiuyaoReading.mockRejectedValue(new ApiError("Runtime release unavailable", 503));
    const user = userEvent.setup();
    render(<ProductTaskPage productId="liuyao" />);
    await fillCompleteCast(user);
    await user.click(screen.getByRole("button", { name: /^立即起卦 · 查看本卦与变卦$/ }));

    await waitFor(() => {
      expect(screen.getByRole("status", { name: "服务暂时不可用，请稍后重试。" })).toHaveAttribute(
        "data-state",
        "unavailable",
      );
    });
    expect(screen.queryByText(liuyaoS6IncompleteMessage(0))).not.toBeInTheDocument();
    expect(screen.queryByText(/Runtime/)).not.toBeInTheDocument();
  });
});
