"use client";

import {
  BookOpenCheck,
  CheckCircle2,
  FileText,
  ShieldCheck,
} from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";

import styles from "./reading-anatomy.module.css";


const layers = [
  {
    id: "conclusion",
    label: "结论",
    title: "先把当前判断说清楚。",
    text: "结构示例：结论会标明主题与适用范围，不写成必然发生的预言。",
    icon: FileText,
  },
  {
    id: "evidence",
    label: "依据",
    title: "关键判断逐条回到事实简报。",
    text: "只有真正命中的事实与来源才能展示；没有古籍命中时，来源区保持为空。",
    icon: BookOpenCheck,
  },
  {
    id: "boundary",
    label: "边界",
    title: "条件和不确定之处不会藏起来。",
    text: "资料口径、时间范围和不能替代的专业判断，会与结论一起出现。",
    icon: ShieldCheck,
  },
  {
    id: "verification",
    label: "核对",
    title: "现实反馈独立保存，不会暗改盘面。",
    text: "符合、部分符合、不符合与暂不清楚都能记录，并保留原始解读版本。",
    icon: CheckCircle2,
  },
] as const;

export function ReadingAnatomy() {
  const [activeId, setActiveId] = useState<(typeof layers)[number]["id"]>("conclusion");
  const reduceMotion = useReducedMotion();
  const active = layers.find((layer) => layer.id === activeId) ?? layers[0];

  return (
    <div className={styles.shell}>
      <div className={styles.controls} role="group" aria-label="解读结构">
        {layers.map(({ id, label, icon: Icon }) => (
          <button
            type="button"
            aria-pressed={activeId === id}
            onClick={() => setActiveId(id)}
            key={id}
          >
            <Icon aria-hidden="true" size={18} strokeWidth={1.7} />
            <span>{label}</span>
          </button>
        ))}
      </div>
      <div className={styles.paper} aria-live="polite">
        <div className={styles.meta}>
          <span>脱敏结构示例</span>
          <span>非真实排盘</span>
        </div>
        <AnimatePresence mode="wait" initial={false}>
          <motion.article
            className={styles.layer}
            key={active.id}
            initial={reduceMotion ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
            transition={{ duration: 0.26, ease: [0.16, 1, 0.3, 1] }}
          >
            <span className={styles.folio}>{String(layers.indexOf(active) + 1).padStart(2, "0")}</span>
            <div>
              <h3>{active.title}</h3>
              <p>{active.text}</p>
            </div>
          </motion.article>
        </AnimatePresence>
        <div className={styles.digest} aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  );
}
