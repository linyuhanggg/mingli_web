import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LiuyaoForm } from "@/components/liuyao-form";


const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: routerPush,
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

const api = vi.hoisted(() => ({
  getCsrfToken: vi.fn(),
  startLiuyaoReading: vi.fn(),
  createIdempotencyKey: vi.fn(),
}));

vi.mock("@/lib/api", () => api);


beforeEach(() => {
  routerPush.mockReset();
  api.getCsrfToken.mockReset();
  api.startLiuyaoReading.mockReset();
  api.createIdempotencyKey.mockReset();
  api.getCsrfToken.mockResolvedValue(
    "csrf-token-with-at-least-thirty-two-characters",
  );
  api.createIdempotencyKey.mockReturnValue("liuyao-intent-0001");
  api.startLiuyaoReading.mockResolvedValue({
    reading_version_id: "33333333-3333-4333-8333-333333333333",
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: null,
    capability_id: "liuyao",
    version: 1,
    status: "input_ready",
    object_id: "concrete_event",
    dimension_ids: [],
    horizon: { kind_id: "instant", start: "2026-08-10", end: "2026-08-10" },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-10T01:00:00Z",
  });
});

describe("LiuyaoForm", () => {
  it("submits a manually recorded hexagram through the real liuyao API", async () => {
    const user = userEvent.setup();
    render(<LiuyaoForm />);

    await screen.findByLabelText("起卦时刻");
    await user.type(
      screen.getByLabelText("想清楚问什么"),
      "我是否应该在三个月内接受已经拿到的工作邀请？",
    );
    fireEvent.change(screen.getByLabelText("起卦时刻"), {
      target: { value: "2026-08-09T09:30" },
    });
    await user.type(screen.getByLabelText("起卦地点"), "上海市");

    const scopeNotice = screen.getByRole("region", {
      name: "当前可交付范围：事业与工作",
    });
    expect(scopeNotice).toHaveTextContent("岗位、合作、面试、工作选择与推进");
    expect(screen.queryByRole("radio", { name: "结果走向" })).not.toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "时机与进展" })).not.toBeInTheDocument();

    const tossGroup = screen.getByRole("group", {
      name: /六次投掷.*自下而上/,
    });
    const labels = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"];
    const castValues = ["6", "7", "8", "9", "6", "9"];
    for (let index = 0; index < labels.length; index += 1) {
      const control = screen.getByLabelText(labels[index]);
      expect(control).toBeRequired();
      expect(control).toHaveAttribute("aria-required", "true");
      await user.selectOptions(control, castValues[index]);
    }
    expect(tossGroup).toHaveTextContent("6 老阴");

    await user.click(screen.getByRole("button", { name: /开始解读 · 事业主题/ }));

    await waitFor(() =>
      expect(routerPush).toHaveBeenCalledWith(
        "/app/readings/33333333-3333-4333-8333-333333333333",
      ),
    );
    expect(api.startLiuyaoReading).toHaveBeenCalledTimes(1);
    expect(api.startLiuyaoReading).toHaveBeenCalledWith(
      expect.objectContaining({
        cast: [6, 7, 8, 9, 6, 9],
        query: "我是否应该在三个月内接受已经拿到的工作邀请？",
        location: "上海市",
        timezone: "Asia/Shanghai",
        dimension_ids: ["career"],
      }),
      "liuyao-intent-0001",
    );
  });

  it("requires event_datetime and location with inline errors and focuses the question", async () => {
    const user = userEvent.setup();
    render(<LiuyaoForm />);

    await screen.findByLabelText("起卦时刻");
    const submit = screen.getByRole("button", { name: /开始解读/ });
    expect(submit).toBeEnabled();
    await user.click(submit);

    const question = screen.getByLabelText("想清楚问什么");
    await waitFor(() => expect(question).toHaveFocus());
    expect(question).toHaveAttribute("aria-required", "true");
    expect(question).toHaveAttribute("aria-invalid", "true");
    expect(question).toHaveAttribute("aria-describedby");
    expect(await screen.findByText("请确认起卦时刻")).toBeVisible();
    expect(screen.getByText("请填写起卦地点")).toBeVisible();
    expect(api.startLiuyaoReading).not.toHaveBeenCalled();
  });

  it("uses the searchable IANA allowlist and rejects a merely well-shaped value", async () => {
    const user = userEvent.setup();
    render(<LiuyaoForm />);

    const timezone = await screen.findByLabelText("起卦时区");
    expect(timezone).toHaveAttribute("list", "liuyao-timezone-options");
    expect(
      document.querySelectorAll("#liuyao-timezone-options option").length,
    ).toBeGreaterThan(300);
    expect(
      document.querySelector(
        '#liuyao-timezone-options option[value="Pacific/Auckland"]',
      ),
    ).not.toBeNull();

    await user.type(
      screen.getByLabelText("想清楚问什么"),
      "这次岗位面试能否进入下一轮？",
    );
    fireEvent.change(screen.getByLabelText("起卦时刻"), {
      target: { value: "2026-08-09T20:10" },
    });
    await user.type(screen.getByLabelText("起卦地点"), "上海市");
    await user.clear(timezone);
    await user.type(timezone, "Foo/Bar");
    await user.click(screen.getByRole("button", { name: /开始解读/ }));

    expect(await screen.findByText("请选择列表中的有效 IANA 时区")).toBeVisible();
    expect(api.startLiuyaoReading).not.toHaveBeenCalled();
  });

  it("names digital casting as digital_coin and never generates it in the browser", async () => {
    const user = userEvent.setup();
    const random = vi.spyOn(Math, "random");
    render(<LiuyaoForm />);

    await screen.findByLabelText("起卦时刻");
    await user.type(
      screen.getByLabelText("想清楚问什么"),
      "这次岗位面试能否进入下一轮？",
    );
    fireEvent.change(screen.getByLabelText("起卦时刻"), {
      target: { value: "2026-08-09T20:10" },
    });
    await user.type(screen.getByLabelText("起卦地点"), "上海市");
    const digitalCoin = screen.getByRole("radio", { name: /电子摇卦/ });
    digitalCoin.focus();
    await user.keyboard(" ");
    await user.click(screen.getByRole("button", { name: /开始解读/ }));

    await waitFor(() =>
      expect(api.startLiuyaoReading).toHaveBeenCalledTimes(1),
    );
    expect(api.startLiuyaoReading).toHaveBeenCalledWith(
      expect.objectContaining({ cast: "digital_coin" }),
      "liuyao-intent-0001",
    );
    expect(random).not.toHaveBeenCalled();
    random.mockRestore();
  });

  it("enforces the stricter question length with an inline alert", async () => {
    const user = userEvent.setup();
    render(<LiuyaoForm />);

    await screen.findByLabelText("起卦时刻");
    await user.type(screen.getByLabelText("想清楚问什么"), "太短");
    await user.click(screen.getByRole("button", { name: /开始解读/ }));

    expect(
      await screen.findByText("请把问题写得更具体，至少 6 个字"),
    ).toBeVisible();
    expect(api.startLiuyaoReading).not.toHaveBeenCalled();
  });
});
