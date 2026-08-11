import { act, render } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import RootLayout from "@/app/layout";


const navigation = vi.hoisted(() => ({ pathname: "/" }));

vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
}));

function layout() {
  const root = RootLayout({ children: <main>页面内容</main> });
  const body = root.props.children;
  return <>{body.props.children}</>;
}

beforeEach(() => {
  navigation.pathname = "/";
  vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
});

describe("route scroll policy", () => {
  it("starts a forward route at the top instead of inheriting the old page position", () => {
    const view = render(layout());

    navigation.pathname = "/app/ask/liuyao";
    view.rerender(layout());

    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
  });

  it("leaves browser history navigation to native scroll restoration", () => {
    navigation.pathname = "/app/ask/liuyao";
    const view = render(layout());

    act(() => {
      window.dispatchEvent(new PopStateEvent("popstate"));
      navigation.pathname = "/";
      view.rerender(layout());
    });

    expect(window.scrollTo).not.toHaveBeenCalled();
  });
});
