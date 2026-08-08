"use client";

import { motion, useReducedMotion } from "motion/react";

import styles from "./time-archive.module.css";


const ledger = [
  { code: "INPUT", label: "输入确认" },
  { code: "FACT", label: "事实成形" },
  { code: "LIMIT", label: "边界标注" },
  { code: "CHECK", label: "现实核对" },
] as const;

export function TimeArchive() {
  const reduceMotion = useReducedMotion();

  return (
    <figure className={styles.figure} aria-labelledby="time-archive-caption">
      <div className={styles.instrument} aria-hidden="true">
        <motion.div
          className={styles.outerRing}
          initial={reduceMotion ? false : { opacity: 0, rotate: -10, scale: 0.94 }}
          animate={{ opacity: 1, rotate: 0, scale: 1 }}
          transition={{ duration: 0.72, ease: [0.16, 1, 0.3, 1] }}
        />
        <motion.div
          className={styles.innerRing}
          initial={reduceMotion ? false : { opacity: 0, rotate: 18, scale: 0.9 }}
          animate={{ opacity: 1, rotate: 0, scale: 1 }}
          transition={{ duration: 0.84, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
        />
        <motion.div
          className={styles.hand}
          initial={reduceMotion ? false : { opacity: 0, rotate: -42 }}
          animate={{ opacity: 1, rotate: -18 }}
          transition={{ duration: 0.78, delay: 0.22, ease: [0.16, 1, 0.3, 1] }}
        />
        <div className={styles.axis} />
        <div className={styles.center}>
          <span>TIME / 归档</span>
          <strong>可复现</strong>
          <small>不是随机对话</small>
        </div>
      </div>
      <motion.ol
        className={styles.ledger}
        initial={reduceMotion ? false : "hidden"}
        animate="shown"
        variants={{
          hidden: {},
          shown: { transition: { staggerChildren: 0.075, delayChildren: 0.34 } },
        }}
      >
        {ledger.map((item) => (
          <motion.li
            key={item.code}
            variants={{
              hidden: { opacity: 0, y: 10 },
              shown: { opacity: 1, y: 0 },
            }}
            transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
          >
            <span>{item.code}</span>
            <strong>{item.label}</strong>
          </motion.li>
        ))}
      </motion.ol>
      <figcaption id="time-archive-caption">
        时间被拆成输入、事实、边界与核对，逐层可读。
      </figcaption>
    </figure>
  );
}
