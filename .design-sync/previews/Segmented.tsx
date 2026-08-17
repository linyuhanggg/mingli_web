import { useState } from "react";
import { Segmented } from "mingli-web";

export function Calendar() {
  const [value, setValue] = useState("solar");
  return (
    <Segmented
      aria-label="历法"
      value={value}
      onValueChange={setValue}
      options={[
        { value: "solar", label: "公历" },
        { value: "lunar", label: "农历" },
        { value: "unknown", label: "未知" },
      ]}
    />
  );
}

export function WithDisabledOption() {
  const [value, setValue] = useState("bazi");
  return (
    <Segmented
      aria-label="术数体系"
      value={value}
      onValueChange={setValue}
      options={[
        { value: "bazi", label: "八字" },
        { value: "ziwei", label: "紫微" },
        { value: "liuyao", label: "六爻" },
        { value: "taiyi", label: "太乙", disabled: true },
      ]}
    />
  );
}

export function TwoOptions() {
  const [value, setValue] = useState("brief");
  return (
    <Segmented
      aria-label="解读粒度"
      value={value}
      onValueChange={setValue}
      options={[
        { value: "brief", label: "精要" },
        { value: "full", label: "详解" },
      ]}
    />
  );
}
