import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReadingResult } from "@/components/readings/reading-result";
import { RuntimeChart } from "@/components/readings/runtime-chart";
import { Status } from "@/components/ui/status";
import { resetApiCache } from "@/lib/api";
import type { MeihuaChartViewModel } from "@/view-models/registry";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

const VERSION_ID = "33333333-3333-4333-8333-333333333333";

const VIEW: MeihuaChartViewModel = {
  schema_version: "meihua-chart/v1",
  subject_ref: "meihua:six-states",
  question: "这件事如何推进？",
  casting_method: "time",
  primary_hexagram: { name: "水雷屯", upper_trigram: "坎", lower_trigram: "震" },
  mutual_hexagram: null,
  changed_hexagram: null,
  moving_lines: [3],
  body_use: {
    body: { position: "lower", trigram: "震", element: "木" },
    use: { position: "upper", trigram: "坎", element: "水" },
    relation: "生",
    status: "calculated_relation_not_verdict",
  },
  core_facts: null,
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function summary(status = "accepted", inputRequest: unknown = null) {
  return {
    reading_version_id: VERSION_ID,
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    capability_id: "meihua",
    product_id: "meihua",
    version: 1,
    status,
    object_id: "concrete_event",
    dimension_ids: [],
    horizon: { kind_id: "instant", start: null, end: null },
    prior_answer: null,
    input_request: inputRequest,
    created_at: "2026-08-10T01:00:00Z",
  };
}

function readyResult() {
  return {
    reading_version_id: VERSION_ID,
    status: "prepared",
    accepted_copy: null,
    fact_panel: null,
    view_model: VIEW,
    document: null,
    verification: null,
    input_request: null,
    capability: {
      capability_id: "meihua",
      label: "梅花易数",
      tier: "B",
      source_system: "meihua",
      runtime_active_rule_count: 2,
      judgment_rule_count: 0,
      source_status: "available",
    },
  };
}

beforeEach(() => resetApiCache());

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("梅花易数六态", () => {
  it("shows loading while the summary is pending", async () => {
    let resolveFetch: (response: Response) => void = () => undefined;
    const pending = new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>()
        .mockImplementationOnce(() => pending)
        .mockResolvedValueOnce(jsonResponse(readyResult())),
    );

    render(<ReadingResult readingId={VERSION_ID} />);
    expect(screen.getByRole("status", { name: "正在同步出盘" })).toHaveAttribute(
      "data-state",
      "loading",
    );
    resolveFetch(jsonResponse(summary()));
    await pending;
  });

  it("maps a missing result to empty", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async (url) => (
      String(url).endsWith("/result")
        ? jsonResponse({ title: "Reading not found" }, 404)
        : jsonResponse(summary())
    )));

    render(<ReadingResult readingId={VERSION_ID} />);
    expect(await screen.findByRole("status", { name: "还没有可展示的盘面" })).toHaveAttribute(
      "data-state",
      "empty",
    );
  });

  it("shows a prepared typed ViewModel as ready without waiting for narrative", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async (url) => (
      String(url).endsWith("/result") ? jsonResponse(readyResult()) : jsonResponse(summary("prepared"))
    )));

    render(<ReadingResult readingId={VERSION_ID} />);
    expect(await screen.findByRole("region", { name: "梅花易数排盘工作台" })).toBeVisible();
    expect(screen.getByText("水雷屯")).toBeVisible();
  });

  it("keeps locked copy scoped away from returned free facts", () => {
    render(
      <>
        <RuntimeChart
          capability={{
            capability_id: "meihua",
            label: "梅花易数",
            tier: "B",
            source_system: "meihua",
            runtime_active_rule_count: 2,
            judgment_rule_count: 0,
            source_status: "available",
          }}
          viewModel={VIEW}
        />
        <Status state="locked" />
      </>,
    );

    expect(screen.getByRole("region", { name: "梅花易数排盘工作台" })).toBeVisible();
    expect(screen.getByRole("status", { name: "深读暂未解锁" })).toHaveAttribute(
      "data-state",
      "locked",
    );
  });

  it("shows need-input without guessing the casting source", async () => {
    const inputRequest = {
      requirements: [{
        any_of: [{
          id: "observation_source",
          label: "观物来源",
          type_id: "text",
          description: "请补充服务端要求的观物来源",
          choices: [],
        }],
      }],
    };
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async () => jsonResponse(summary("waiting_input", inputRequest))));

    render(<ReadingResult readingId={VERSION_ID} />);
    expect(await screen.findByLabelText("观物来源")).toBeVisible();
    expect(screen.getByRole("button", { name: /提交补充资料/ })).toBeEnabled();
    expect(screen.queryByText(/按时间起卦|按数字起卦|按声数起卦/)).not.toBeInTheDocument();
  });

  it("maps a service failure to error", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async () => jsonResponse({ title: "结果暂时读取失败" }, 500)));

    render(<ReadingResult readingId={VERSION_ID} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("结果暂时读取失败");
  });
});
