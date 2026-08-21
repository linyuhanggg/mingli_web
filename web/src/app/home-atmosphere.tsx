"use client";

import Image from "next/image";
import { useEffect, useRef } from "react";

import styles from "./home.module.css";


export function HomeAtmosphere() {
  const atmosphereRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const atmosphere = atmosphereRef.current;
    if (!atmosphere || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        atmosphere.dataset.active = entry?.isIntersecting ? "true" : "false";
      },
      { threshold: 0.01 },
    );

    // 负 z-index 的绝对定位装饰层在 Chromium 中可能被 IntersectionObserver
    // 误判为离屏；观察真实占位的 Hero section，仍把状态写回装饰层。
    observer.observe(atmosphere.parentElement ?? atmosphere);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      aria-hidden="true"
      className={styles.atmosphere}
      data-active="true"
      data-testid="home-atmosphere"
      ref={atmosphereRef}
    >
      <div className={styles.inkPlane}>
        <Image
          alt=""
          className={styles.inkBackdrop}
          fill
          priority
          sizes="100vw"
          src="/home/hero-ink-wash.webp"
        />
      </div>

      <div className={styles.talismanStage}>
        <div className={`${styles.talismanLayer} ${styles.talismanGhost}`}>
          <Image alt="" fill sizes="(max-width: 767px) 78vw, 36vw" src="/home/talisman-ghost.webp" />
        </div>
        <div className={`${styles.talismanLayer} ${styles.talismanFlame}`}>
          <Image alt="" fill priority sizes="(max-width: 767px) 78vw, 36vw" src="/home/talisman-flame.webp" />
        </div>
        <div className={`${styles.talismanLayer} ${styles.talismanInk}`}>
          <Image alt="" fill priority sizes="(max-width: 767px) 78vw, 36vw" src="/home/talisman-ink.webp" />
        </div>
      </div>
    </div>
  );
}
