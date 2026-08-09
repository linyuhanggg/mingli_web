import { readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReadingResult } from "@/components/readings/reading-result";
import { VerificationForm } from "@/components/readings/verification-form";
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
}));

const VERSION_ID = "33333333-3333-4333-8333-333333333333";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function problemResponse(title: string, status: number) {
  return jsonResponse({ title, status, request_id: "request-1" }, status);
}

function guestSession() {
  return jsonResponse(
    {
      status: "active",
      expires_at: "2026-08-11T00:00:00Z",
      csrf_token: "csrf-token-with-at-least-thirty-two-characters",
    },
    201,
  );
}

function readingSummary(
  status: string,
  overrides: Partial<Record<string, unknown>> = {},
) {
  return {
    reading_version_id: VERSION_ID,
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    capability_id: "fortune",
    version: 1,
    status,
    object_id: "near_time_personal",
    dimension_ids: [],
    horizon: {
      kind_id: "week",
      start: "2026-08-10",
      end: "2026-08-16",
    },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-10T01:00:00Z",
    ...overrides,
  };
}

const acceptedCopy = "先给结论。\n\n再说明依据，原字原序。";
const acceptedCopyQuery = acceptedCopy.replace(/\s+/g, " ");

function factPanel() {
  return {
    question: "近七日最值得关注什么？",
    vocabulary: [
      { id: "term:steady", label: "稳中求进", description: "先守住节奏" },
    ],
    facts: [
      {
        ref: "fact:opaque-1",
        subject_ref: "profile-version:secret-profile-id",
        kind_id: "fact:career-structure",
        value: {
          birth_datetime: "1994-04-30T05:55:00+08:00",
          state_token: "opaque-runtime-token",
          candidate: "模型草稿",
          prompt: "内部提示词",
        },
        display_text: "当前结构更支持持续积累。",
      },
    ],
    evidence: [
      {
        ref: "evidence:opaque-classic-1",
        source_title: "滴天髓",
        locator: "卷一",
        excerpt: "顺势而为，先定其基。",
        supports_fact_refs: ["fact:opaque-1"],
      },
    ],
    findings: [
      {
        ref: "finding:opaque-1",
        subject_ref: "profile-version:secret-profile-id",
        dimension_ids: ["career"],
        kind_id: "finding:trend",
        data: { candidate: "不要显示" },
        fact_refs: ["fact:opaque-1"],
        evidence_refs: ["evidence:opaque-classic-1"],
        limit_kind_ids: ["limit:traditional"],
        support_mode: "exact",
      },
    ],
    claim_scopes: [
      {
        subject_ref: "profile-version:secret-profile-id",
        dimension_id: "career",
        allowed_kind_ids: ["finding:trend"],
        certainty_ceiling_id: "moderate",
        fact_refs: ["fact:opaque-1"],
        evidence_refs: ["evidence:opaque-classic-1"],
      },
    ],
    limits: [
      {
        kind_id: "limit:traditional",
        public_text: "仅供传统文化参考，不构成现实决策保证。",
        scope_refs: ["profile-version:secret-profile-id"],
        detail_ids: [],
      },
    ],
    prior_answer: "上一版已接纳正文。",
    request_view: {
      subject_refs: ["profile-version:secret-profile-id"],
      capability_ids: ["fortune"],
      object_id: "near_time_personal",
      dimension_ids: ["career"],
      horizon: {
        kind_id: "week",
        start: "2026-08-10",
        end: "2026-08-16",
      },
    },
  };
}

function readingResult(
  overrides: Partial<Record<string, unknown>> = {},
) {
  return {
    reading_version_id: VERSION_ID,
    status: "accepted",
    accepted_copy: acceptedCopy,
    fact_panel: factPanel(),
    verification: null,
    input_request: null,
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

describe("ReadingVersionSummary polling and explicit result fetch", () => {
  it("polls the summary, then GETs /result and renders the exact Accepted Copy", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === `/api/v1/readings/${VERSION_ID}`) {
        return jsonResponse(readingSummary("accepted"));
      }
      if (path === `/api/v1/readings/${VERSION_ID}/result`) {
        return jsonResponse(readingResult());
      }
      return problemResponse("Unexpected request", 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const acceptedRegion = await screen.findByRole("region", { name: "判断" });
    const copy = within(acceptedRegion).getByText(acceptedCopyQuery);
    expect(copy.textContent).toBe(acceptedCopy);
    expect(fetchMock.mock.calls.map(([url]) => String(url)).slice(0, 2)).toEqual([
      `/api/v1/readings/${VERSION_ID}`,
      `/api/v1/readings/${VERSION_ID}/result`,
    ]);
  });

  it("renders structured facts, evidence, limits, prior answer, and server horizon without opaque refs", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) return jsonResponse(readingResult());
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText("当前结构更支持持续积累。")).toBeVisible();
    expect(screen.getByText("滴天髓")).toBeVisible();
    expect(screen.getByText("顺势而为，先定其基。")).toBeVisible();
    expect(screen.getByText("仅供传统文化参考，不构成现实决策保证。")).toBeVisible();
    expect(screen.getByText("上一版已接纳正文。")).toBeVisible();
    expect(screen.getAllByText(/2026年8月10日/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/2026年8月16日/).length).toBeGreaterThan(0);

    const visible = document.body.textContent ?? "";
    expect(visible).not.toMatch(
      /fact:opaque|evidence:opaque|finding:opaque|profile-version:secret|1994-04-30|opaque-runtime-token|模型草稿|内部提示词|不要显示/i,
    );
    expect(visible).not.toContain("state_token");
  });

  it.each([
    ["input_ready", "准备解读"],
    ["prepared", "事实已准备"],
    ["completing", "正在接纳正文"],
    ["delayed", "交付延迟"],
  ])("shows the real %s state and the server-provided horizon", async (status, text) => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse(readingSummary(status)));
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    const matches = await screen.findAllByText(text);
    expect(matches.length).toBeGreaterThan(0);
    expect(matches[0]).toBeVisible();
    const horizons = screen.getAllByText(/2026年8月10日.*2026年8月16日/);
    expect(horizons.length).toBeGreaterThan(0);
    expect(screen.queryByText(/排队中/)).not.toBeInTheDocument();
  });

  it("keeps runtime_unknown explicit and offers a manual state check", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse(readingSummary("runtime_unknown")));
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText(/运行状态暂时未知/)).toBeVisible();
    expect(screen.getByRole("button", { name: /重新检查状态/ })).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shows terminal_stopped as a terminal state with a restart path", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        jsonResponse(readingSummary("terminal_stopped")),
      ),
    );

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText(/本次解读已停止/)).toBeVisible();
    expect(screen.getByRole("link", { name: /重新发起/ })).toHaveAttribute(
      "href",
      "/app",
    );
  });

  it("turns a transient poll error into a manual retry and then fetches the result", async () => {
    let pollCount = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) return jsonResponse(readingResult());
      pollCount += 1;
      return pollCount === 1
        ? problemResponse("暂时无法读取状态", 500)
        : jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/暂时无法读取状态/);
    await user.click(screen.getByRole("button", { name: /重试/ }));

    expect(await screen.findByText(acceptedCopyQuery)).toBeVisible();
    expect(pollCount).toBe(2);
  });

  it("shows an accepted-result fetch error instead of getting stuck in loading", async () => {
    let resultCount = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path.endsWith("/result")) {
        resultCount += 1;
        return resultCount === 1
          ? problemResponse("正文暂时读取失败", 500)
          : jsonResponse(readingResult());
      }
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("正文暂时读取失败");
    await user.click(screen.getByRole("button", { name: "重试" }));
    expect(await screen.findByText(acceptedCopyQuery)).toBeVisible();
    expect(resultCount).toBe(2);
  });
});

describe("waiting_input requirements[].any_of[]", () => {
  it("renders real runtime fields, focuses the first error, and posts only typed values", async () => {
    const inputRequest = {
      requirements: [
        {
          any_of: [
            {
              id: "cast_1",
              label: "初爻",
              type_id: "integer",
              description: "请输入 6、7、8 或 9",
              choices: [],
            },
          ],
        },
        {
          any_of: [
            {
              id: "zi_policy",
              label: "子时口径",
              type_id: "choice",
              description: null,
              choices: [
                { id: "midnight", label: "午夜换日", description: null },
                { id: "solar", label: "太阳时", description: null },
              ],
            },
          ],
        },
      ],
    };
    let pollCount = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return guestSession();
      if (path.endsWith("/input")) {
        return jsonResponse(readingSummary("input_ready"), 201);
      }
      if (path.endsWith("/result")) return jsonResponse(readingResult());
      pollCount += 1;
      return pollCount === 1
        ? jsonResponse(
            readingSummary("waiting_input", { input_request: inputRequest }),
          )
        : jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);
    await screen.findByText("补充资料");
    const submit = screen.getByRole("button", { name: /提交补充资料/ });
    await user.click(submit);

    const firstField = screen.getByLabelText("初爻");
    await waitFor(() => expect(firstField).toHaveFocus());
    expect(firstField).toHaveAttribute("aria-required", "true");
    expect(firstField).toHaveAttribute("aria-invalid", "true");
    expect(firstField).toHaveAttribute("aria-describedby");
    expect(screen.getByRole("alert")).toHaveTextContent(/必填/);

    await user.type(firstField, "8");
    await user.selectOptions(screen.getByLabelText("子时口径"), "midnight");
    await user.click(submit);

    const inputCall = callsTo(fetchMock, "/input")[0];
    expect(inputCall[0]).toBe(`/api/v1/readings/${VERSION_ID}/input`);
    expect(JSON.parse(String(inputCall[1]?.body))).toEqual({
      values: { cast_1: 8, zi_policy: "midnight" },
    });
    expect(String(inputCall[1]?.body)).not.toMatch(
      /state_token|candidate|prompt|birth_datetime/i,
    );
    expect(await screen.findByText(acceptedCopyQuery)).toBeVisible();
  });

  it("keeps the submit label visible and blocks duplicate input submissions while busy", async () => {
    const inputRequest = {
      requirements: [
        {
          any_of: [
            {
              id: "fixture_input",
              label: "合同测试输入",
              type_id: "text",
              description: null,
              choices: [],
            },
          ],
        },
      ],
    };
    let releaseInput: (response: Response) => void = () => {};
    const pendingInput = new Promise<Response>((resolve) => {
      releaseInput = resolve;
    });
    const fetchMock = vi.fn<typeof fetch>((url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return Promise.resolve(guestSession());
      if (path.endsWith("/input")) return pendingInput;
      return Promise.resolve(
        jsonResponse(
          readingSummary("waiting_input", { input_request: inputRequest }),
        ),
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);
    await user.type(await screen.findByLabelText("合同测试输入"), "已补充");
    const submit = screen.getByRole("button", { name: /提交补充资料/ });
    await user.click(submit);
    await waitFor(() => expect(callsTo(fetchMock, "/input")).toHaveLength(1));

    expect(submit).toHaveAccessibleName(/提交补充资料.*正在提交/);
    expect(submit).toHaveAttribute("aria-busy", "true");
    expect(submit).toBeDisabled();
    submit.closest("form")?.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    expect(callsTo(fetchMock, "/input")).toHaveLength(1);

    releaseInput(jsonResponse(readingSummary("input_ready"), 201));
  });

  it("requires exactly one value from each any_of group", async () => {
    const inputRequest = {
      requirements: [
        {
          any_of: [
            {
              id: "known_time",
              label: "已知时刻",
              type_id: "text",
              description: null,
              choices: [],
            },
            {
              id: "time_range",
              label: "大致时段",
              type_id: "text",
              description: null,
              choices: [],
            },
          ],
        },
      ],
    };
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return guestSession();
      return jsonResponse(
        readingSummary("waiting_input", { input_request: inputRequest }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);
    const knownTime = await screen.findByLabelText("已知时刻");
    await user.type(knownTime, "09:30");
    await user.type(screen.getByLabelText("大致时段"), "上午");
    await user.click(screen.getByRole("button", { name: /提交补充资料/ }));

    await waitFor(() => expect(knownTime).toHaveFocus());
    expect(screen.getAllByText("本组只能填写一项")).toHaveLength(2);
    expect(callsTo(fetchMock, "/input")).toHaveLength(0);
  });
});

describe("verification and follow-up", () => {
  it("submits the product-authoritative four-outcome verification with optional note", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(guestSession())
      .mockResolvedValueOnce(
        jsonResponse(
          {
            verification_id: "66666666-6666-4666-8666-666666666666",
            reading_version_id: VERSION_ID,
            outcome: "partial",
            note: "出生地点有出入",
            created_at: "2026-08-10T02:00:00Z",
          },
          201,
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<VerificationForm readingId={VERSION_ID} />);
    expect(screen.getAllByRole("radio")).toHaveLength(4);
    await user.click(screen.getByRole("radio", { name: "部分符合" }));
    await user.type(screen.getByLabelText(/补充说明/), "出生地点有出入");
    await user.click(screen.getByRole("button", { name: /提交核对结果/ }));

    expect(await screen.findByText(/已保存核对结果/)).toBeVisible();
    const verificationCall = callsTo(fetchMock, "/verification")[0];
    expect(verificationCall[0]).toBe(
      `/api/v1/readings/${VERSION_ID}/verification`,
    );
    expect(JSON.parse(String(verificationCall[1]?.body))).toEqual({
      outcome: "partial",
      note: "出生地点有出入",
    });
  });

  it("renders an existing verification from the result instead of asking again", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith("/result")) {
        return jsonResponse(
          readingResult({
            verification: {
              verification_id: "66666666-6666-4666-8666-666666666666",
              reading_version_id: VERSION_ID,
              outcome: "partial",
              note: "部分时间不确定",
              created_at: "2026-08-10T02:00:00Z",
            },
          }),
        );
      }
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);

    expect(await screen.findByText(/已保存：部分符合/)).toBeVisible();
    expect(screen.getByText("部分时间不确定")).toBeVisible();
    expect(screen.queryByRole("button", { name: /提交核对结果/ })).not.toBeInTheDocument();
  });

  it("uses a native Enter-submit form, singular /follow-up, stable key, and new Reading Version id", async () => {
    let followUpAttempts = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return guestSession();
      if (path.endsWith("/result")) return jsonResponse(readingResult());
      if (path.endsWith("/follow-up")) {
        followUpAttempts += 1;
        return followUpAttempts === 1
          ? problemResponse("追问暂时失败，请重试", 500)
          : jsonResponse(
              readingSummary("input_ready", {
                reading_version_id: "77777777-7777-4777-8777-777777777777",
                version: 2,
                prior_answer: acceptedCopy,
              }),
              201,
            );
      }
      return jsonResponse(readingSummary("accepted"));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadingResult readingId={VERSION_ID} />);
    const query = await screen.findByLabelText("追问");
    expect(query.tagName).toBe("INPUT");
    await user.type(query, "换工作方向呢？{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(/重试/);
    await user.type(query, "{Enter}");

    await waitFor(() =>
      expect(routerPush).toHaveBeenCalledWith(
        "/app/readings/77777777-7777-4777-8777-777777777777",
      ),
    );
    const calls = callsTo(fetchMock, "/follow-up");
    expect(calls).toHaveLength(2);
    expect(calls[0][0]).toBe(`/api/v1/readings/${VERSION_ID}/follow-up`);
    expect(JSON.parse(String(calls[0][1]?.body))).toEqual({
      query: "换工作方向呢？",
    });
    expect(getHeader(calls[0][1], "Idempotency-Key")).toMatch(/^.{8,128}$/);
    expect(getHeader(calls[0][1], "Idempotency-Key")).toBe(
      getHeader(calls[1][1], "Idempotency-Key"),
    );
    expect(String(calls[0][1]?.body)).not.toMatch(/state_token|candidate|prompt/i);
  });
});

describe("Web interface regression guards", () => {
  it("keeps 48px inputs, mobile-safe input text, reduced motion, and bounded pre overflow", () => {
    const root = process.cwd();
    const globals = readFileSync(join(root, "src/app/globals.css"), "utf8");
    expect(globals).toContain("@media (prefers-reduced-motion: reduce)");

    const formCssFiles = [
      "src/components/readings/need-input-form.module.css",
      "src/components/readings/follow-up-form.module.css",
      "src/components/readings/verification-form.module.css",
    ];
    for (const file of formCssFiles) {
      const css = readFileSync(join(root, file), "utf8");
      expect(css).toMatch(/min-height:\s*3rem/);
      expect(css).toMatch(/font-size:\s*1rem/);
      expect(css).not.toMatch(/transition:\s*all/i);
      expect(css).not.toMatch(/animation-[a-z-]+:\s*[^;]*infinite/i);
      expect(css).not.toContain("999px");
    }

    const factCss = readFileSync(
      join(root, "src/components/readings/fact-panel.module.css"),
      "utf8",
    );
    expect(factCss).toMatch(/overflow-x:\s*auto/);
    expect(factCss).toMatch(/max-width:\s*100%/);
  });

  it("does not disable paste or browser zoom in the touched surfaces", () => {
    const root = process.cwd();
    const sources = [
      "src/app/layout.tsx",
      "src/components/profile-form.tsx",
      "src/components/fortune-flow.tsx",
      "src/components/liuyao-form.tsx",
      "src/components/readings/need-input-form.tsx",
      "src/components/readings/follow-up-form.tsx",
      "src/components/readings/verification-form.tsx",
    ]
      .map((file) => readFileSync(join(root, file), "utf8"))
      .join("\n");

    expect(sources).not.toMatch(/onPaste/);
    expect(sources).not.toMatch(/user-scalable\s*=\s*no|maximum-scale\s*=\s*1/i);
  });
});
