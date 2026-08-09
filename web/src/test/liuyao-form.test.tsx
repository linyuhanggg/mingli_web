import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { LiuyaoForm } from "@/components/liuyao-form";


describe("LiuyaoForm", () => {
  it("accepts a manually recorded hexagram but keeps deterministic casting gated", async () => {
    const user = userEvent.setup();
    render(<LiuyaoForm />);

    await user.type(
      screen.getByRole("textbox", { name: /具体问题/ }),
      "我是否应该在三个月内接受已经拿到的工作邀请？",
    );
    fireEvent.change(screen.getByLabelText(/起卦或记录时刻/), {
      target: { value: "2026-08-09T09:30" },
    });
    await user.type(screen.getByRole("textbox", { name: /城市级地点/ }), "上海市");
    await user.type(screen.getByLabelText(/IANA 时区/), "Asia/Shanghai");
    await user.click(screen.getByRole("radio", { name: /录入已有卦/ }));
    await user.click(screen.getByRole("button", { name: /核对问题与方式/ }));

    expect(await screen.findAllByText("请录入六爻")).toHaveLength(6);

    const castValues = ["6", "7", "8", "9", "6", "9"];
    const castGroup = screen.getByRole("group", { name: /六爻录入（自下而上）/ });
    const castInputs = within(castGroup).getAllByRole("combobox");
    expect(castInputs).toHaveLength(6);
    for (const [index, input] of castInputs.entries()) {
      expect(within(input).getByRole("option", { name: "6 · 老阴（变）" })).toHaveValue("6");
      expect(within(input).getByRole("option", { name: "7 · 少阳" })).toHaveValue("7");
      expect(within(input).getByRole("option", { name: "8 · 少阴" })).toHaveValue("8");
      expect(within(input).getByRole("option", { name: "9 · 老阳（变）" })).toHaveValue("9");
      await user.selectOptions(input, castValues[index]);
    }
    await user.click(screen.getByRole("checkbox", { name: /同一个目标/ }));
    const reviewButton = screen.getByRole("button", { name: /核对问题与方式/ });
    reviewButton.focus();
    await user.keyboard("{Enter}");

    expect(await screen.findByRole("heading", { name: "问题与起卦方式已核对" })).toBeVisible();
    expect(screen.getByText("[6, 7, 8, 9, 6, 9] · 自下而上")).toBeVisible();
    expect(screen.getByText("上海市 · Asia/Shanghai")).toBeVisible();
    expect(screen.getByRole("button", { name: "开始确定性起卦" })).toBeDisabled();
    expect(screen.getByText(/不会用随机占位数据冒充真实卦象/)).toBeVisible();
  });

  it("requires event_datetime, confirmed_timezone and location", async () => {
    const user = userEvent.setup();
    render(<LiuyaoForm />);

    await user.type(screen.getByRole("textbox", { name: /具体问题/ }), "这次岗位面试能否进入下一轮？");
    await user.click(screen.getByRole("checkbox", { name: /同一个目标/ }));
    await user.click(screen.getByRole("button", { name: /核对问题与方式/ }));

    expect(await screen.findByText("请选择起卦或记录时刻")).toBeVisible();
    expect(screen.getByText("请填写起卦所在地（城市级）")).toBeVisible();
    expect(screen.getByText("请确认 IANA 时区")).toBeVisible();
  });

  it("uses the searchable IANA allowlist and rejects a merely well-shaped value", async () => {
    const user = userEvent.setup();
    render(<LiuyaoForm />);

    const timezone = screen.getByLabelText(/已确认 IANA 时区/);
    expect(timezone).toHaveAttribute("list", "liuyao-timezone-options");
    expect(document.querySelectorAll("#liuyao-timezone-options option").length).toBeGreaterThan(300);
    expect(document.querySelector('#liuyao-timezone-options option[value="Pacific/Auckland"]')).not.toBeNull();

    await user.type(screen.getByRole("textbox", { name: /具体问题/ }), "这次岗位面试能否进入下一轮？");
    fireEvent.change(screen.getByLabelText(/起卦或记录时刻/), {
      target: { value: "2026-08-09T20:10" },
    });
    await user.type(screen.getByRole("textbox", { name: /城市级地点/ }), "上海市");
    await user.type(timezone, "Foo/Bar");
    await user.click(screen.getByRole("checkbox", { name: /同一个目标/ }));
    await user.click(screen.getByRole("button", { name: /核对问题与方式/ }));

    expect(await screen.findByText("请选择列表中的有效 IANA 时区")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "问题与起卦方式已核对" })).not.toBeInTheDocument();
  });

  it("names digital casting as digital_coin and never generates it in the browser", async () => {
    const user = userEvent.setup();
    const random = vi.spyOn(Math, "random");
    render(<LiuyaoForm />);

    await user.type(screen.getByRole("textbox", { name: /具体问题/ }), "这次岗位面试能否进入下一轮？");
    fireEvent.change(screen.getByLabelText(/起卦或记录时刻/), {
      target: { value: "2026-08-09T20:10" },
    });
    await user.type(screen.getByRole("textbox", { name: /城市级地点/ }), "上海市");
    await user.type(screen.getByLabelText(/IANA 时区/), "Asia/Shanghai");
    const digitalCoin = screen.getByRole("radio", { name: /digital_coin/ });
    digitalCoin.focus();
    await user.keyboard(" ");
    await user.click(screen.getByRole("checkbox", { name: /同一个目标/ }));
    const reviewButton = screen.getByRole("button", { name: /核对问题与方式/ });
    reviewButton.focus();
    await user.keyboard("{Enter}");

    expect(await screen.findByText("digital_coin · 待 Runtime 安全起卦")).toBeVisible();
    expect(random).not.toHaveBeenCalled();
    random.mockRestore();
  });
});
