import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProfileForm } from "@/components/profile-form";


describe("ProfileForm", () => {
  it("validates the three-step profile review without pretending to save a version", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    expect(screen.getByRole("heading", { name: "基本资料" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /继续确认/ }));
    expect(screen.getByRole("heading", { name: "时间口径" })).toBeVisible();

    await user.click(screen.getByRole("button", { name: /继续确认/ }));
    expect(await screen.findByText("请选择公历出生日期")).toBeVisible();
    expect(screen.getByText("请选择出生时间，或勾选时辰不确定")).toBeVisible();

    fireEvent.change(screen.getByLabelText(/公历出生日期/), { target: { value: "1990-06-18" } });
    await user.click(screen.getByRole("checkbox", { name: /出生时辰不确定/ }));
    await user.type(screen.getByRole("textbox", { name: /出生地/ }), "浙江省杭州市");
    await user.click(screen.getByRole("radio", { name: /午夜换日/ }));
    await user.click(screen.getByRole("button", { name: /继续确认/ }));

    expect(screen.getByRole("heading", { name: "确认与同意" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /完成本地核对/ }));
    expect(await screen.findByText("请先确认资料用途与隐私说明")).toBeVisible();

    await user.click(screen.getByRole("checkbox", { name: /我确认以上资料/ }));
    await user.click(screen.getByRole("button", { name: /完成本地核对/ }));

    expect(await screen.findByRole("heading", { name: "资料已在本页核对" })).toBeVisible();
    expect(screen.getByRole("button", { name: "保存并生成免费概览" })).toBeDisabled();
    expect(screen.getByText(/不会在浏览器里自行算盘/)).toBeVisible();
  });

  it("uses explicit lunar fields and preserves leap-month and zi-hour policy in review", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    await user.click(screen.getByRole("button", { name: /继续确认/ }));
    const lunar = screen.getByRole("radio", { name: /^农历/ });
    lunar.focus();
    await user.keyboard(" ");

    expect(lunar).toBeChecked();
    expect(screen.queryByLabelText(/公历出生日期/)).not.toBeInTheDocument();

    const lunarYear = screen.getByRole("textbox", { name: /农历年/ });
    const lunarMonth = screen.getByRole("textbox", { name: /农历月/ });
    const lunarDay = screen.getByRole("textbox", { name: /农历日/ });
    expect(lunarYear).not.toHaveAttribute("type", "date");
    expect(lunarMonth).not.toHaveAttribute("type", "date");
    expect(lunarDay).not.toHaveAttribute("type", "date");

    await user.type(lunarYear, "1990");
    await user.type(lunarMonth, "5");
    await user.type(lunarDay, "26");
    await user.tab();
    expect(screen.getByRole("checkbox", { name: /农历闰月/ })).toHaveFocus();
    await user.keyboard(" ");
    await user.click(screen.getByRole("checkbox", { name: /出生时辰不确定/ }));
    await user.type(screen.getByRole("textbox", { name: /出生地/ }), "福建省福州市");
    await user.click(screen.getByRole("radio", { name: /晚子时换日/ }));
    await user.click(screen.getByRole("button", { name: /继续确认/ }));

    expect(screen.getByText(/农历 · 闰月/)).toBeVisible();
    expect(screen.getByText(/1990 年 5 月 26 日/)).toBeVisible();
    expect(screen.getByText(/late-zi-next-day/)).toBeVisible();
  });

  it("requires an explicit zi_hour_policy before the review step", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    await user.click(screen.getByRole("button", { name: /继续确认/ }));
    fireEvent.change(screen.getByLabelText(/公历出生日期/), { target: { value: "1990-06-18" } });
    await user.click(screen.getByRole("checkbox", { name: /出生时辰不确定/ }));
    await user.type(screen.getByRole("textbox", { name: /出生地/ }), "浙江省杭州市");
    await user.click(screen.getByRole("button", { name: /继续确认/ }));

    expect(await screen.findByText("请选择子时换日策略")).toBeVisible();
    expect(screen.getByRole("heading", { name: "时间口径" })).toBeVisible();
  });

  it("offers the complete searchable IANA list and rejects values outside it", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    await user.click(screen.getByRole("button", { name: /继续确认/ }));
    fireEvent.change(screen.getByLabelText(/公历出生日期/), { target: { value: "1990-06-18" } });
    await user.click(screen.getByRole("checkbox", { name: /出生时辰不确定/ }));
    await user.type(screen.getByRole("textbox", { name: /出生地/ }), "美国纽约市");
    await user.click(screen.getByRole("radio", { name: /午夜换日/ }));

    const timezone = screen.getByLabelText(/^IANA 时区/);
    expect(timezone).toHaveAttribute("list", "profile-timezone-options");
    expect(document.querySelectorAll("#profile-timezone-options option").length).toBeGreaterThan(300);
    expect(document.querySelector('#profile-timezone-options option[value="America/New_York"]')).not.toBeNull();

    await user.clear(timezone);
    await user.type(timezone, "Foo/Bar");
    await user.click(screen.getByRole("button", { name: /继续确认/ }));

    expect(await screen.findByText("请选择列表中的有效 IANA 时区")).toBeVisible();
    expect(screen.getByRole("heading", { name: "时间口径" })).toBeVisible();
  });
});
