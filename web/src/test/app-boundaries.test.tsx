import { render, screen } from "@testing-library/react";

import AppLoading from "@/app/app/loading";
import AppNotFound from "@/app/app/not-found";
import RootLayout from "@/app/layout";


describe("app route boundaries", () => {
  it("gives the loading route a semantic page heading", () => {
    render(<AppLoading />);

    expect(
      screen.getByRole("heading", { level: 1, name: "正在载入私人档案" }),
    ).toBeInTheDocument();
  });

  it("gives the not-found route a semantic page heading", () => {
    render(<AppNotFound />);

    expect(
      screen.getByRole("heading", { level: 1, name: "没有找到这份私人记录" }),
    ).toBeInTheDocument();
  });

  it("renders layout children without a hidden HTML-comment span", () => {
    const { container } = render(
      <RootLayout>
        <p>应用内容</p>
      </RootLayout>,
    );

    expect(screen.getByText("应用内容")).toBeInTheDocument();
    expect(container.querySelector("span[hidden]")).not.toBeInTheDocument();
    expect(container.innerHTML).not.toContain("<!--");
  });
});
