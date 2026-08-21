import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import LoginPage from "./page";

const adminFetchMock = vi.hoisted(() => vi.fn());
const replaceMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api")>();
  return { ...original, adminFetch: adminFetchMock };
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

function submitLogin() {
  fireEvent.change(screen.getByLabelText("工作邮箱"), {
    target: { value: "staff@example.com" },
  });
  fireEvent.change(screen.getByLabelText("密码"), {
    target: { value: "not-a-real-password" },
  });
  fireEvent.submit(screen.getByRole("button", { name: "进入运营台" }).closest("form")!);
}

describe("Admin login errors", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
    replaceMock.mockReset();
  });

  it("maps credential failures to one linked Chinese alert and focuses email", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      title: "Invalid email or password",
    });
    render(<LoginPage />);

    submitLogin();

    const alert = await screen.findByRole("alert");
    const email = screen.getByLabelText("工作邮箱");
    const password = screen.getByLabelText("密码");
    expect(alert).toHaveTextContent("工作邮箱或密码不正确。");
    expect(screen.queryByText("Invalid email or password")).not.toBeInTheDocument();
    expect(email).toHaveAttribute("aria-invalid", "true");
    expect(password).toHaveAttribute("aria-invalid", "true");
    expect(email).toHaveAttribute("aria-describedby", "admin-login-error");
    expect(password).toHaveAttribute("aria-describedby", "admin-login-error");
    await waitFor(() => expect(email).toHaveFocus());
  });

  it.each([
    [429, "Too many login attempts; please wait and retry", "尝试次数过多，请稍后再试。"],
    [503, "Service unavailable", "登录服务暂时不可用，请稍后重试。"],
  ])("keeps non-field failure status %s off the fields", async (status, title, message) => {
    adminFetchMock.mockResolvedValueOnce({ ok: false, status, title });
    render(<LoginPage />);

    submitLogin();

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByLabelText("工作邮箱")).not.toHaveAttribute("aria-invalid");
    expect(screen.getByLabelText("密码")).not.toHaveAttribute("aria-invalid");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "进入运营台" })).toHaveFocus(),
    );
  });

  it("clears the prior alert and field associations when the user edits", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: false, status: 400, title: "Invalid request" });
    render(<LoginPage />);

    submitLogin();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "请检查工作邮箱和密码后重试。",
    );

    fireEvent.change(screen.getByLabelText("密码"), { target: { value: "changed-password" } });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByLabelText("工作邮箱")).not.toHaveAttribute("aria-describedby");
    expect(screen.getByLabelText("密码")).not.toHaveAttribute("aria-describedby");
  });
});
