import { act, createElement, type HTMLAttributes, type ReactNode } from "react";
import { hydrateRoot, type Root } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const motionRuntime = vi.hoisted(() => ({
  reducedMotion: false,
  controls: {
    set: vi.fn(),
    start: vi.fn().mockResolvedValue(undefined),
    stop: vi.fn(),
  },
}));

vi.mock("motion/react", async () => {
  const React = await import("react");

  type MockMotionProps = HTMLAttributes<HTMLElement> & {
    animate?: unknown;
    children?: ReactNode;
    initial?: unknown;
    transition?: unknown;
  };

  const MotionDiv = React.forwardRef<HTMLElement, MockMotionProps>(
    function MotionDiv(props, ref) {
      const htmlProps = { ...props };
      const { children } = htmlProps;
      delete htmlProps.animate;
      delete htmlProps.children;
      delete htmlProps.initial;
      delete htmlProps.transition;
      return createElement("div", { ...htmlProps, ref }, children);
    },
  );

  return {
    motion: { div: MotionDiv },
    useAnimationControls: () => motionRuntime.controls,
    useIsomorphicLayoutEffect: React.useEffect,
    useReducedMotion: () => motionRuntime.reducedMotion,
  };
});

import { RouteEnter } from "@/components/motion-primitives";

function useProductionMotionEnvironment() {
  vi.stubEnv("NODE_ENV", "production");
  vi.stubEnv("VITEST", "false");
  vi.stubEnv("VITEST_WORKER_ID", undefined);
}

async function hydrateRouteEnter() {
  const element = (
    <RouteEnter className="route" routeKey="/account/history/ut-ready">
      <article>完整历史报告</article>
    </RouteEnter>
  );
  const serverHtml = renderToString(element);
  const container = document.createElement("div");
  container.innerHTML = serverHtml;
  document.body.append(container);
  const recoverableErrors: unknown[] = [];
  let root: Root | undefined;

  await act(async () => {
    root = hydrateRoot(container, element, {
      onRecoverableError: (error) => recoverableErrors.push(error),
    });
    await Promise.resolve();
  });

  return { container, recoverableErrors, root: root!, serverHtml };
}

beforeEach(() => {
  motionRuntime.controls.set.mockReset();
  motionRuntime.controls.start.mockReset().mockResolvedValue(undefined);
  motionRuntime.controls.stop.mockReset();
});

afterEach(() => {
  vi.unstubAllEnvs();
  document.body.replaceChildren();
});

describe("RouteEnter hydration motion", () => {
  it("hydrates reduced motion from visible SSR markup without starting an entrance", async () => {
    motionRuntime.reducedMotion = true;
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const { container, recoverableErrors, root, serverHtml } = await hydrateRouteEnter();
    const wrapper = container.firstElementChild as HTMLElement;

    expect(serverHtml).toContain('style="opacity:1;transform:none"');
    expect(wrapper).toHaveStyle({ opacity: "1", transform: "none" });
    expect(wrapper).toHaveTextContent("完整历史报告");
    expect(recoverableErrors).toEqual([]);
    expect(consoleError).not.toHaveBeenCalled();
    expect(motionRuntime.controls.set).toHaveBeenCalledWith({ opacity: 1, y: 0 });
    expect(motionRuntime.controls.start).not.toHaveBeenCalled();

    await act(async () => root.unmount());
    consoleError.mockRestore();
  });

  it("hydrates no-preference from the same visible SSR state and starts the entrance", async () => {
    useProductionMotionEnvironment();
    motionRuntime.reducedMotion = false;
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const { container, recoverableErrors, root, serverHtml } = await hydrateRouteEnter();
    const wrapper = container.firstElementChild as HTMLElement;

    expect(serverHtml).toContain('style="opacity:1;transform:none"');
    expect(wrapper).toHaveStyle({ opacity: "1", transform: "none" });
    expect(recoverableErrors).toEqual([]);
    expect(consoleError).not.toHaveBeenCalled();
    expect(motionRuntime.controls.set).toHaveBeenCalledWith({ opacity: 0, y: 8 });
    expect(motionRuntime.controls.start).toHaveBeenCalledWith({
      opacity: 1,
      transition: { duration: 0.22, ease: [0.16, 1, 0.3, 1] },
      y: 0,
    });

    await act(async () => root.unmount());
    consoleError.mockRestore();
  });
});
