import { useState } from "react";
import { Tabs } from "mingli-web";

const paragraph: React.CSSProperties = {
  margin: 0,
  color: "var(--color-text-secondary)",
  fontSize: "var(--font-size-body)",
  lineHeight: "var(--line-height-body, 1.7)",
};

export function ReadingSections() {
  const [value, setValue] = useState("chart");
  return (
    <Tabs
      aria-label="解读分区"
      value={value}
      onValueChange={setValue}
      items={[
        {
          value: "chart",
          label: "盘面",
          panel: (
            <p style={paragraph}>
              四柱：癸酉 丙辰 己丑 甲子。日主己土生于辰月，土旺秉令，透甲木为正官。
            </p>
          ),
        },
        {
          value: "report",
          label: "报告",
          panel: <p style={paragraph}>官星得地而不透杀，宜守成、忌躁进；本年利文书与考核。</p>,
        },
        {
          value: "check",
          label: "核对",
          panel: <p style={paragraph}>出生时刻按真太阳时校正 −14 分钟，时柱未跨界，定盘可用。</p>,
        },
      ]}
    />
  );
}

export function TwoPanels() {
  const [value, setValue] = useState("evidence");
  return (
    <Tabs
      aria-label="证据视图"
      value={value}
      onValueChange={setValue}
      items={[
        {
          value: "evidence",
          label: "古籍原文",
          panel: <p style={paragraph}>《渊海子平》：官星者，克我而有情者也，最忌刑冲破害。</p>,
        },
        {
          value: "note",
          label: "释读",
          panel: <p style={paragraph}>此处只取“忌刑冲”一义，用于解释本命辰丑相刑的影响面。</p>,
        },
      ]}
    />
  );
}
