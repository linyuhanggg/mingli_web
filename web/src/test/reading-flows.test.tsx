import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FortuneFlow } from "@/components/fortune-flow";
import { LiuyaoForm } from "@/components/liuyao-form";
import { ProfileForm } from "@/components/profile-form";
import { resetApiCache } from "@/lib/api";

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
  useSearchParams: () => new URLSearchParams(),
}));

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function problemResponse(title: string, status: number) {
  return jsonResponse({ title, status, request_id: "request-1" }, status);
}

function guestSession(csrfToken = "csrf-token-with-at-least-thirty-two-characters") {
  return jsonResponse(
    {
      status: "active",
      expires_at: "2026-08-11T00:00:00Z",
      csrf_token: csrfToken,
    },
    201,
  );
}

const profiles = {
  profiles: [
    {
      profile_id: "11111111-1111-4111-8111-111111111111",
      profile_version_id: "22222222-2222-4222-8222-222222222222",
      subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
      version: 1,
      created_at: "2026-08-09T12:00:00Z",
    },
  ],
};

function readingSummary(
  overrides: Partial<Record<string, unknown>> = {},
) {
  return {
    reading_version_id: "33333333-3333-4333-8333-333333333333",
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: profiles.profiles[0].profile_version_id,
    capability_id: "fortune",
    version: 1,
    status: "input_ready",
    object_id: "near_time_personal",
    dimension_ids: [],
    horizon: {
      kind_id: "day",
      start: "2026-08-10",
      end: "2026-08-10",
    },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-10T01:00:00Z",
    ...overrides,
  };
}

function getHeader(init: RequestInit | undefined, name: string): string | null {
  return new Headers(init?.headers).get(name);
}

function callsTo(fetchMock: ReturnType<typeof vi.fn>, suffix: string) {
  return fetchMock.mock.calls.filter(([url]) => String(url).endsWith(suffix));
}

afterEach(() => {
  vi.unstubAllGlobals();
  routerPush.mockReset();
});

beforeEach(() => {
  resetApiCache();
});

describe("Profile contract", () => {
  it("creates a non-empty 本人 draft and confirms backend-valid enums and offset datetime", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return guestSession();
      if (path === "/api/v1/profiles/drafts") {
        return jsonResponse(
          { draft_id: "55555555-5555-4555-8555-555555555555", status: "draft" },
          201,
        );
      }
      if (path.endsWith("/confirm")) {
        return jsonResponse(profiles.profiles[0], 201);
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ProfileForm />);

    await user.type(screen.getByLabelText("出生时间"), "1994-04-30T05:55");
    await user.type(screen.getByLabelText("出生地点"), "北京市朝阳区");
    await user.selectOptions(screen.getByLabelText("性别"), "female");
    await user.selectOptions(screen.getByLabelText("时间口径"), "civil");
    await user.selectOptions(screen.getByLabelText("子时口径"), "midnight");
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    await waitFor(() =>
      expect(routerPush).toHaveBeenCalledWith("/app/profiles?created=1"),
    );
    const draftCall = callsTo(fetchMock, "/api/v1/profiles/drafts")[0];
    expect(JSON.parse(String(draftCall[1]?.body))).toEqual({ label: "本人" });

    const confirmCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/confirm"),
    );
    expect(JSON.parse(String(confirmCall?.[1]?.body))).toMatchObject({
      birth_datetime: "1994-04-30T05:55:00+08:00",
      timezone: "Asia/Shanghai",
      location: "北京市朝阳区",
      gender: "female",
      time_basis_policy: "civil",
      zi_hour_policy: "midnight",
    });
  });

  it("offers only the backend profile enums and focuses the first invalid field", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(guestSession()));
    const user = userEvent.setup();

    render(<ProfileForm />);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /保存档案/ })).toBeEnabled(),
    );

    expect(
      Array.from(screen.getByLabelText("性别").querySelectorAll("option")).map(
        (option) => option.value,
      ),
    ).toEqual(["", "female", "male", "other"]);
    expect(
      Array.from(screen.getByLabelText("时间口径").querySelectorAll("option")).map(
        (option) => option.value,
      ),
    ).toEqual(["", "civil", "solar", "lunar"]);
    expect(
      Array.from(screen.getByLabelText("子时口径").querySelectorAll("option")).map(
        (option) => option.value,
      ),
    ).toEqual(["", "midnight", "substitute", "solar"]);

    await user.click(screen.getByRole("button", { name: /保存档案/ }));
    const birthInput = screen.getByLabelText("出生时间");
    await waitFor(() => expect(birthInput).toHaveFocus());
    expect(birthInput).toHaveAttribute("aria-required", "true");
    expect(birthInput).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("请选择性别", { selector: "p" })).toBeVisible();
    expect(screen.getByText("请选择时间口径", { selector: "p" })).toBeVisible();
    expect(screen.getByText("请选择子时口径", { selector: "p" })).toBeVisible();
  });

  it("clears a stale CSRF token after 403, bootstraps once, and retries once", async () => {
    let guestCalls = 0;
    let draftCalls = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url, init) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") {
        guestCalls += 1;
        return guestSession(
          guestCalls === 1
            ? "stale-csrf-token-with-at-least-thirty-two-chars"
            : "fresh-csrf-token-with-at-least-thirty-two-chars",
        );
      }
      if (path === "/api/v1/profiles/drafts") {
        draftCalls += 1;
        if (draftCalls === 1) {
          return problemResponse("CSRF validation failed", 403);
        }
        expect(getHeader(init, "X-CSRF-Token")).toBe(
          "fresh-csrf-token-with-at-least-thirty-two-chars",
        );
        return jsonResponse(
          { draft_id: "55555555-5555-4555-8555-555555555555", status: "draft" },
          201,
        );
      }
      if (path.endsWith("/confirm")) return jsonResponse(profiles.profiles[0], 201);
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ProfileForm />);
    await user.type(screen.getByLabelText("出生时间"), "1994-04-30T05:55");
    await user.type(screen.getByLabelText("出生地点"), "北京市朝阳区");
    await user.selectOptions(screen.getByLabelText("性别"), "female");
    await user.selectOptions(screen.getByLabelText("时间口径"), "civil");
    await user.selectOptions(screen.getByLabelText("子时口径"), "midnight");
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    await waitFor(() =>
      expect(routerPush).toHaveBeenCalledWith("/app/profiles?created=1"),
    );
    expect(guestCalls).toBe(2);
    expect(draftCalls).toBe(2);
  });

  it("does not retry forever when the refreshed CSRF token is also rejected", async () => {
    let guestCalls = 0;
    let draftCalls = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") {
        guestCalls += 1;
        return guestSession(`csrf-${guestCalls}-token-with-at-least-thirty-two-characters`);
      }
      if (path === "/api/v1/profiles/drafts") {
        draftCalls += 1;
        return problemResponse("CSRF validation failed", 403);
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ProfileForm />);
    await user.type(screen.getByLabelText("出生时间"), "1994-04-30T05:55");
    await user.type(screen.getByLabelText("出生地点"), "北京市朝阳区");
    await user.selectOptions(screen.getByLabelText("性别"), "female");
    await user.selectOptions(screen.getByLabelText("时间口径"), "civil");
    await user.selectOptions(screen.getByLabelText("子时口径"), "midnight");
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /CSRF validation failed/,
    );
    expect(guestCalls).toBe(2);
    expect(draftCalls).toBe(2);
  });

  it("does not retry a non-CSRF 403 response", async () => {
    let guestCalls = 0;
    let draftCalls = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") {
        guestCalls += 1;
        return guestSession();
      }
      if (path === "/api/v1/profiles/drafts") {
        draftCalls += 1;
        return problemResponse("Profile access forbidden", 403);
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ProfileForm />);
    await user.type(screen.getByLabelText("出生时间"), "1994-04-30T05:55");
    await user.type(screen.getByLabelText("出生地点"), "北京市朝阳区");
    await user.selectOptions(screen.getByLabelText("性别"), "female");
    await user.selectOptions(screen.getByLabelText("时间口径"), "civil");
    await user.selectOptions(screen.getByLabelText("子时口径"), "midnight");
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Profile access forbidden/,
    );
    expect(guestCalls).toBe(1);
    expect(draftCalls).toBe(1);
  });
});

describe("split fortune start endpoints", () => {
  it("bootstraps a guest before listing profiles and starts today by Reading Version id", async () => {
    const callOrder: string[] = [];
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      callOrder.push(path);
      if (path === "/api/v1/guest-sessions") return guestSession();
      if (path === "/api/v1/profiles") return jsonResponse(profiles);
      if (path === "/api/v1/readings/today") return jsonResponse(readingSummary(), 201);
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<FortuneFlow mode="today" />);
    const select = await screen.findByRole("combobox", { name: /档案/ });
    expect(callOrder.slice(0, 2)).toEqual([
      "/api/v1/guest-sessions",
      "/api/v1/profiles",
    ]);
    expect(screen.getByText(/目标日期由服务端确认/)).toBeVisible();
    expect(screen.getByText(/当前算法范围：事业与工作/)).toBeVisible();
    await user.selectOptions(select, profiles.profiles[0].profile_version_id);
    await user.click(screen.getByRole("button", { name: /开始今日解读/ }));

    await waitFor(() =>
      expect(routerPush).toHaveBeenCalledWith(
        "/app/readings/33333333-3333-4333-8333-333333333333",
      ),
    );
    const startCall = callsTo(fetchMock, "/api/v1/readings/today")[0];
    expect(JSON.parse(String(startCall[1]?.body))).toEqual({
      profile_version_id: profiles.profiles[0].profile_version_id,
      query: "看看今天的事业与工作节奏",
    });
    const key = getHeader(startCall[1], "Idempotency-Key");
    expect(key).toMatch(/^.{8,128}$/);
    expect(JSON.stringify(startCall[1]?.body)).not.toMatch(/action|requested_timezone/);
  });

  it("starts week through /readings/week with the frozen body", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return guestSession();
      if (path === "/api/v1/profiles") return jsonResponse(profiles);
      if (path === "/api/v1/readings/week") {
        return jsonResponse(
          readingSummary({
            horizon: { kind_id: "week", start: "2026-08-10", end: "2026-08-16" },
          }),
          201,
        );
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<FortuneFlow mode="week" />);
    await user.selectOptions(
      await screen.findByRole("combobox", { name: /档案/ }),
      profiles.profiles[0].profile_version_id,
    );
    await user.click(screen.getByRole("button", { name: /开始近七日解读/ }));

    await waitFor(() => expect(callsTo(fetchMock, "/api/v1/readings/week")).toHaveLength(1));
    const startCall = callsTo(fetchMock, "/api/v1/readings/week")[0];
    expect(JSON.parse(String(startCall[1]?.body))).toEqual({
      profile_version_id: profiles.profiles[0].profile_version_id,
      query: "看看近七日的事业与工作节奏",
    });
    expect(getHeader(startCall[1], "Idempotency-Key")).toMatch(/^.{8,128}$/);
  });

  it("reuses the same Idempotency-Key when the user retries the same intent", async () => {
    let attempts = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return guestSession();
      if (path === "/api/v1/profiles") return jsonResponse(profiles);
      if (path === "/api/v1/readings/today") {
        attempts += 1;
        return attempts === 1
          ? problemResponse("暂时失败，请重试", 500)
          : jsonResponse(readingSummary(), 201);
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<FortuneFlow mode="today" />);
    await user.selectOptions(
      await screen.findByRole("combobox", { name: /档案/ }),
      profiles.profiles[0].profile_version_id,
    );
    const submit = screen.getByRole("button", { name: /开始今日解读/ });
    await user.click(submit);
    expect(await screen.findByRole("alert")).toHaveTextContent(/重试/);
    await user.click(submit);

    await waitFor(() => expect(callsTo(fetchMock, "/api/v1/readings/today")).toHaveLength(2));
    const [first, second] = callsTo(fetchMock, "/api/v1/readings/today");
    expect(getHeader(first[1], "Idempotency-Key")).toBe(
      getHeader(second[1], "Idempotency-Key"),
    );
  });

  it("keeps the original action label while busy and blocks duplicate activation", async () => {
    let releaseStart: (response: Response) => void = () => {};
    const pendingStart = new Promise<Response>((resolve) => {
      releaseStart = resolve;
    });
    const fetchMock = vi.fn<typeof fetch>((url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return Promise.resolve(guestSession());
      if (path === "/api/v1/profiles") return Promise.resolve(jsonResponse(profiles));
      if (path === "/api/v1/readings/today") return pendingStart;
      return Promise.resolve(problemResponse("Unexpected request", 500));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<FortuneFlow mode="today" />);
    await user.selectOptions(
      await screen.findByRole("combobox", { name: /档案/ }),
      profiles.profiles[0].profile_version_id,
    );
    const submit = screen.getByRole("button", { name: /开始今日解读/ });
    await user.click(submit);
    await waitFor(() => expect(callsTo(fetchMock, "/api/v1/readings/today")).toHaveLength(1));

    expect(submit).toBeDisabled();
    expect(submit).toHaveAccessibleName(/开始今日解读.*正在启动/);
    expect(submit).toHaveAttribute("aria-busy", "true");
    fireEvent.submit(submit.closest("form") as HTMLFormElement);
    expect(callsTo(fetchMock, "/api/v1/readings/today")).toHaveLength(1);

    releaseStart(jsonResponse(readingSummary(), 201));
    await waitFor(() => expect(routerPush).toHaveBeenCalled());
  });
});

describe("Liuyao contract", () => {
  it("submits six manual tosses bottom-up with confirmed event time, timezone, and location", async () => {
    const callOrder: string[] = [];
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      callOrder.push(path);
      if (path === "/api/v1/guest-sessions") return guestSession();
      if (path === "/api/v1/profiles") return jsonResponse(profiles);
      if (path === "/api/v1/readings/liuyao") {
        return jsonResponse(
          readingSummary({
            profile_version_id: null,
            capability_id: "liuyao",
            object_id: "concrete_event",
            horizon: { kind_id: "instant", start: "2026-08-10", end: "2026-08-10" },
          }),
          201,
        );
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<LiuyaoForm />);
    await screen.findByLabelText("起卦时刻");
    expect(callOrder[0]).toBe("/api/v1/guest-sessions");
    expect(screen.queryByRole("combobox", { name: /档案/ })).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("想清楚问什么"), "今年适合换工作吗？");
    await user.type(screen.getByLabelText("起卦时刻"), "2026-08-10T09:30");
    expect(screen.getByLabelText("起卦时区")).toHaveValue("Asia/Shanghai");
    await user.type(screen.getByLabelText("起卦地点"), "上海市");
    await user.click(screen.getByRole("radio", { name: /手动输入卦象/ }));

    const tossGroup = screen.getByRole("group", {
      name: /六次投掷.*自下而上/,
    });
    expect(tossGroup.tagName).toBe("FIELDSET");
    const labels = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"];
    const tosses = ["6", "7", "8", "9", "6", "7"];
    for (let index = 0; index < labels.length; index += 1) {
      const control = screen.getByLabelText(labels[index]);
      expect(control).toBeRequired();
      expect(control).toHaveAttribute("aria-required", "true");
      await user.selectOptions(control, tosses[index]);
    }
    await user.click(screen.getByRole("button", { name: /开始解读/ }));

    await waitFor(() =>
      expect(routerPush).toHaveBeenCalledWith(
        "/app/readings/33333333-3333-4333-8333-333333333333",
      ),
    );
    const startCall = callsTo(fetchMock, "/api/v1/readings/liuyao")[0];
    expect(JSON.parse(String(startCall[1]?.body))).toEqual({
      cast: [6, 7, 8, 9, 6, 7],
      event_datetime: "2026-08-10T09:30:00+08:00",
      timezone: "Asia/Shanghai",
      location: "上海市",
      query: "今年适合换工作吗？",
      dimension_ids: ["career"],
    });
    expect(getHeader(startCall[1], "Idempotency-Key")).toMatch(/^.{8,128}$/);
    expect(JSON.stringify(startCall[1]?.body)).not.toMatch(
      /profile_version_id|cast_type|state_token|candidate|prompt/i,
    );
  });

  it("submits digital_coin without browser-generated tosses", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return guestSession();
      if (path === "/api/v1/readings/liuyao") {
        return jsonResponse(
          readingSummary({ profile_version_id: null, capability_id: "liuyao" }),
          201,
        );
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<LiuyaoForm />);
    await screen.findByLabelText("起卦时刻");
    await user.type(screen.getByLabelText("想清楚问什么"), "近期适合做决定吗？");
    await user.type(screen.getByLabelText("起卦时刻"), "2026-08-10T10:15");
    await user.type(screen.getByLabelText("起卦地点"), "杭州市");
    await user.click(screen.getByRole("radio", { name: /电子摇卦/ }));
    expect(screen.queryByRole("group", { name: /六次投掷/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /开始解读/ }));

    await waitFor(() => expect(callsTo(fetchMock, "/api/v1/readings/liuyao")).toHaveLength(1));
    const body = JSON.parse(
      String(callsTo(fetchMock, "/api/v1/readings/liuyao")[0][1]?.body),
    );
    expect(body).toEqual({
      cast: "digital_coin",
      event_datetime: "2026-08-10T10:15:00+08:00",
      timezone: "Asia/Shanghai",
      location: "杭州市",
      query: "近期适合做决定吗？",
      dimension_ids: ["career"],
    });
    expect(body).not.toHaveProperty("profile_version_id");
  });

  it("keeps submit enabled for validation, reports errors inline, and focuses the first error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (url) =>
        String(url) === "/api/v1/profiles"
          ? jsonResponse(profiles)
          : guestSession(),
      ),
    );
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
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });
});

describe("split preview API", () => {
  it("posts preview to its frozen endpoint with a caller-stable idempotency key", async () => {
    const api = await import("@/lib/api");
    const startPreview = Reflect.get(api, "startPreviewReading") as
      | undefined
      | ((body: { profile_version_id: string }, key: string) => Promise<unknown>);
    expect(startPreview).toBeTypeOf("function");
    if (!startPreview) return;

    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url) === "/api/v1/guest-sessions") return guestSession();
      if (String(url) === "/api/v1/readings/preview") {
        return jsonResponse(readingSummary({ capability_id: "bazi" }), 201);
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    await startPreview(
      { profile_version_id: profiles.profiles[0].profile_version_id },
      "preview-intent-0001",
    );

    const startCall = callsTo(fetchMock, "/api/v1/readings/preview")[0];
    expect(JSON.parse(String(startCall[1]?.body))).toEqual({
      profile_version_id: profiles.profiles[0].profile_version_id,
    });
    expect(getHeader(startCall[1], "Idempotency-Key")).toBe(
      "preview-intent-0001",
    );
  });
});
