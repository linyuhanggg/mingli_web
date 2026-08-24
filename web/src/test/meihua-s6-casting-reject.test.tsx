import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  MEIHUA_S6_COUNT,
  MEIHUA_S6_HEXAGRAM_SOURCE,
  MEIHUA_S6_LOWER,
  MEIHUA_S6_METHOD,
  MEIHUA_S6_MOVING,
  MEIHUA_S6_NUMBER,
  MEIHUA_S6_UPPER,
} from "@/components/task/meihua-entry-copy";
import { mapMeihuaCastingRejection } from "@/components/task/meihua-casting-reject";
import { ProductTaskPage } from "@/components/task/product-task-page";
import { ApiError } from "@/lib/api";

const mockStartMeihuaReading = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/meihua",
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
  startMeihuaReading: mockStartMeihuaReading,
}));

afterEach(() => {
  cleanup();
  mockStartMeihuaReading.mockReset();
});

function values(method: string) {
  return { meihuaCastingMethod: method };
}

async function fillShared(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("当前问题"), "这件事后续如何");
  await user.selectOptions(screen.getByLabelText("判断侧重"), "outcome");
  fireEvent.change(screen.getByLabelText("事件时间"), {
    target: { value: "2026-08-21T09:30" },
  });
  await user.type(screen.getByLabelText("事件地点"), "上海市");
}

describe("meihua S6 casting-rejection mapper", () => {
  it("maps compiler tokens to S1 fields without leaking engineering copy", () => {
    expect(
      mapMeihuaCastingRejection(
        new ApiError("Invalid request", 400, "Meihua number must be a positive integer"),
        values("supplied_number"),
      ),
    ).toEqual({ field: "meihuaNumber", message: MEIHUA_S6_NUMBER });
    expect(
      mapMeihuaCastingRejection(
        new ApiError("Invalid request", 400, "Meihua count must be a positive integer"),
        values("sound_count"),
      ),
    ).toEqual({ field: "meihuaCount", message: MEIHUA_S6_COUNT });
    expect(
      mapMeihuaCastingRejection(
        new ApiError("Invalid request", 400, "Meihua upper_trigram must be one of"),
        values("observation"),
      ),
    ).toEqual({ field: "meihuaUpperTrigram", message: MEIHUA_S6_UPPER });
    expect(
      mapMeihuaCastingRejection(
        new ApiError("Invalid request", 400, "Meihua lower_trigram must be one of"),
        values("observation"),
      ),
    ).toEqual({ field: "meihuaLowerTrigram", message: MEIHUA_S6_LOWER });
    expect(
      mapMeihuaCastingRejection(
        new ApiError("Invalid request", 400, "Meihua moving_line must be within 1..6"),
        values("supplied_hexagram"),
      ),
    ).toEqual({ field: "meihuaMovingLine", message: MEIHUA_S6_MOVING });
    expect(
      mapMeihuaCastingRejection(
        new ApiError("Invalid request", 400, "Meihua provenance must be a non-empty object"),
        values("supplied_hexagram"),
      ),
    ).toEqual({ field: "meihuaSource", message: MEIHUA_S6_HEXAGRAM_SOURCE });
    expect(
      mapMeihuaCastingRejection(
        new ApiError("unsupported Meihua casting method: 'stroke'", 400),
        values("time"),
      ),
    ).toEqual({ field: "meihuaCastingMethod", message: MEIHUA_S6_METHOD });
  });

  it("falls back to the selected method's S1 field when the compiler only says Invalid request", () => {
    expect(
      mapMeihuaCastingRejection(new ApiError("Invalid request", 400), values("supplied_number")),
    ).toEqual({ field: "meihuaNumber", message: MEIHUA_S6_NUMBER });
    expect(
      mapMeihuaCastingRejection(new ApiError("Invalid request", 400), values("supplied_hexagram")),
    ).toEqual({ field: "meihuaMovingLine", message: MEIHUA_S6_MOVING });
  });

  it("maps pydantic loc on 422 to the same S1 fields", () => {
    const detail = [{ loc: ["body", "number"], msg: "Input should be greater than 0" }];
    const mapped = mapMeihuaCastingRejection(
      new ApiError("服务暂时不可用，请稍后重试", 422, JSON.stringify(detail)),
      values("supplied_number"),
    );
    expect(mapped).toEqual({ field: "meihuaNumber", message: MEIHUA_S6_NUMBER });
  });

  it("leaves 503 to the generic unavailable mapper", () => {
    expect(
      mapMeihuaCastingRejection(new ApiError("Runtime release unavailable", 503), values("time")),
    ).toBeNull();
  });
});

describe("/meihua S6 casting rejection stays on S1", () => {
  it("points a compiler number rejection at 起卦数字 and hides engineering terms", async () => {
    mockStartMeihuaReading.mockRejectedValue(
      new ApiError("Invalid request", 400, "Meihua number must be a positive integer"),
    );
    const user = userEvent.setup();
    render(<ProductTaskPage productId="meihua" />);
    await fillShared(user);
    await user.selectOptions(screen.getByLabelText("梅花起卦方式"), "supplied_number");
    await user.type(screen.getByLabelText("起卦数字"), "17");
    await user.type(screen.getByLabelText("数字资料来源"), "用户现场报数");
    await user.click(screen.getByRole("button", { name: /立即起卦/ }));

    const nearby = await screen.findByText(MEIHUA_S6_NUMBER);
    expect(nearby).toBeVisible();
    expect(nearby).toHaveAttribute("id", "meihua-number-error");
    expect(screen.getByLabelText("起卦数字")).toHaveAccessibleDescription(MEIHUA_S6_NUMBER);
    expect(screen.getByLabelText("起卦数字")).toHaveFocus();
    expect(screen.getByRole("form", { name: /梅花/ })).toBeVisible();
    expect(screen.queryByText(/Invalid request/)).not.toBeInTheDocument();
    expect(screen.queryByText(/moving_line/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Meihua number/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Runtime/)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /工作台/ })).not.toBeInTheDocument();
  });

  it("points a moving-line rejection at 动爻", async () => {
    mockStartMeihuaReading.mockRejectedValue(
      new ApiError("Invalid request", 400, "Meihua moving_line must be within 1..6"),
    );
    const user = userEvent.setup();
    render(<ProductTaskPage productId="meihua" />);
    await fillShared(user);
    await user.selectOptions(screen.getByLabelText("梅花起卦方式"), "supplied_hexagram");
    await user.type(screen.getByLabelText("卦象资料来源"), "用户现场记录");
    await user.click(screen.getByRole("button", { name: /立即起卦/ }));

    const nearby = await screen.findByText(MEIHUA_S6_MOVING);
    expect(nearby).toHaveAttribute("id", "meihua-moving-line-error");
    expect(screen.getByLabelText("动爻")).toHaveAccessibleDescription(MEIHUA_S6_MOVING);
    expect(screen.queryByText(/Invalid request/)).not.toBeInTheDocument();
    expect(screen.queryByText(/moving_line/)).not.toBeInTheDocument();
  });

  it("does not steal 503 into a field error", async () => {
    mockStartMeihuaReading.mockRejectedValue(new ApiError("Runtime release unavailable", 503));
    const user = userEvent.setup();
    render(<ProductTaskPage productId="meihua" />);
    await fillShared(user);
    await user.click(screen.getByRole("button", { name: /立即起卦/ }));

    await waitFor(() => {
      expect(screen.getByRole("status", { name: "服务暂时不可用，请稍后重试。" })).toHaveAttribute(
        "data-state",
        "unavailable",
      );
    });
    expect(screen.queryByText(MEIHUA_S6_NUMBER)).not.toBeInTheDocument();
    expect(screen.queryByText(/Runtime/)).not.toBeInTheDocument();
  });
});
