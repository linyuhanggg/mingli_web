"use client";

import { useEffect, useRef, useSyncExternalStore, type ReactNode } from "react";

import { useSafeReducedMotion } from "@/components/motion-primitives";

import styles from "./home.module.css";

function lerp(from: number, to: number, amount: number) {
  return from + (to - from) * amount;
}

function subscribeToMount() {
  return () => undefined;
}

function getClientMounted() {
  return true;
}

function getServerMounted() {
  return false;
}

export function HomeStage({ children }: { children: ReactNode }) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const reduceMotion = useSafeReducedMotion();
  const motionReady = useSyncExternalStore(subscribeToMount, getClientMounted, getServerMounted);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || !motionReady || reduceMotion) return;

    const target = { x: 0.5, y: 0.32 };
    const current = { x: 0.5, y: 0.32 };
    let frame = 0;

    const apply = () => {
      current.x = lerp(current.x, target.x, 0.08);
      current.y = lerp(current.y, target.y, 0.08);
      root.style.setProperty("--home-mx", `${(current.x * 100).toFixed(2)}%`);
      root.style.setProperty("--home-my", `${(current.y * 100).toFixed(2)}%`);
      root.style.setProperty("--home-px", (current.x * 2 - 1).toFixed(3));
      root.style.setProperty("--home-py", (current.y * 2 - 1).toFixed(3));
      const unsettled = Math.abs(current.x - target.x) > 0.001 || Math.abs(current.y - target.y) > 0.001;
      frame = unsettled ? window.requestAnimationFrame(apply) : 0;
    };

    const schedule = () => {
      if (!frame) frame = window.requestAnimationFrame(apply);
    };

    const onMove = (event: PointerEvent) => {
      const box = root.getBoundingClientRect();
      target.x = Math.min(1, Math.max(0, (event.clientX - box.left) / box.width));
      target.y = Math.min(1, Math.max(0, (event.clientY - box.top) / box.height));
      schedule();
    };

    const onLeave = () => {
      target.x = 0.5;
      target.y = 0.32;
      schedule();
    };

    root.addEventListener("pointermove", onMove);
    root.addEventListener("pointerleave", onLeave);
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      root.removeEventListener("pointermove", onMove);
      root.removeEventListener("pointerleave", onLeave);
    };
  }, [motionReady, reduceMotion]);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || !motionReady || reduceMotion || window.matchMedia("(hover: none)").matches) return;

    const magnets = Array.from(root.querySelectorAll<HTMLElement>("[data-magnetic]"));

    const onMove = (event: PointerEvent) => {
      magnets.forEach((node) => {
        const box = node.getBoundingClientRect();
        const dx = event.clientX - (box.left + box.width / 2);
        const dy = event.clientY - (box.top + box.height / 2);
        const near = Math.hypot(dx, dy) < 140;
        node.style.transform = near
          ? `translate3d(${dx * 0.18}px, ${dy * 0.18}px, 0)`
          : "translate3d(0, 0, 0)";
      });
    };

    const onLeave = () => {
      magnets.forEach((node) => {
        node.style.transform = "translate3d(0, 0, 0)";
      });
    };

    root.addEventListener("pointermove", onMove);
    root.addEventListener("pointerleave", onLeave);
    return () => {
      root.removeEventListener("pointermove", onMove);
      root.removeEventListener("pointerleave", onLeave);
    };
  }, [motionReady, reduceMotion]);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || !motionReady) return;
    const nodes = Array.from(root.querySelectorAll<HTMLElement>("[data-count]"));

    const run = (node: HTMLElement) => {
      const end = Number(node.dataset.count);
      if (!Number.isFinite(end)) return;
      if (reduceMotion) {
        node.textContent = String(end);
        return;
      }
      const started = performance.now();
      const duration = 1100;
      const tick = (now: number) => {
        const progress = Math.min(1, (now - started) / duration);
        const eased = 1 - (1 - progress) ** 3;
        node.textContent = String(Math.round(end * eased));
        if (progress < 1) window.requestAnimationFrame(tick);
      };
      window.requestAnimationFrame(tick);
    };

    if (typeof IntersectionObserver === "undefined") {
      nodes.forEach(run);
      return;
    }

    const seen = new WeakSet<HTMLElement>();
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const node = entry.target as HTMLElement;
          if (!entry.isIntersecting || seen.has(node)) return;
          seen.add(node);
          run(node);
        });
      },
      { threshold: 0.6 },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [motionReady, reduceMotion]);

  return (
    <div
      className={styles.stage}
      data-reduced={motionReady && reduceMotion ? "true" : "false"}
      ref={rootRef}
    >
      {motionReady && reduceMotion ? null : (
        <>
          <div aria-hidden="true" className={styles.spotlight} />
          <div aria-hidden="true" className={styles.grain} />
        </>
      )}
      {children}
    </div>
  );
}
