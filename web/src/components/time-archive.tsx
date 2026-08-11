"use client";

import { motion, useReducedMotion } from "motion/react";

import { easeOutExpo, motionDurations } from "./motion-primitives";
import styles from "./time-archive.module.css";


export function TimeArchive() {
  const reduceMotion = useReducedMotion();

  return (
    <figure className={styles.figure} aria-labelledby="time-archive-caption">
      <div className={styles.card}>
        <div className={styles.cardTop}>
          <span>ASTROLABE ID #2026-ARCH</span>
          <span>实时天时刻度</span>
        </div>

        <div className={styles.instrument} aria-hidden="true">
          <motion.div
            className={styles.outerRing}
            initial={reduceMotion ? false : { opacity: 0, rotate: -10, scale: 0.94 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            transition={{ duration: motionDurations.focal, ease: easeOutExpo }}
          />
          <div
            className={styles.outerRingSpin}
            data-reduced={reduceMotion ? "true" : "false"}
          />
          <motion.div
            className={styles.innerRing}
            initial={reduceMotion ? false : { opacity: 0, rotate: 18, scale: 0.9 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            transition={{ duration: 0.84, delay: 0.08, ease: easeOutExpo }}
          />
          <div className={styles.centerSeal}>
            <strong>八字</strong>
          </div>
        </div>

        <div className={styles.cardCopy}>
          <h3>四柱干支 · 十神格局图</h3>
          <p>输入精确生辰，即刻校对年柱、月柱、日柱与时柱</p>
        </div>

        <dl className={styles.meta}>
          <div>
            <dt>参考典籍</dt>
            <dd>滴天髓 / 子平真诠</dd>
          </div>
          <div>
            <dt>推算核心</dt>
            <dd>确定性 Runtime · 八字模块</dd>
          </div>
        </dl>
      </div>
      <figcaption id="time-archive-caption" className="sr-only">
        八字档案示意：先确认生辰输入，再由确定性核心排盘。
      </figcaption>
    </figure>
  );
}
