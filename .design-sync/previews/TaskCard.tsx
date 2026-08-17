import { TaskCard } from "mingli-web";

const grid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(3, minmax(200px, 1fr))",
  gap: "16px",
};

export function Tones() {
  return (
    <div style={grid}>
      <TaskCard
        tone="paper"
        title="八字排盘"
        description="输入出生信息，生成四柱与十神事实。"
        label="命"
        href="/bazi"
        action="开始排盘"
      />
      <TaskCard
        tone="ink"
        title="六爻起卦"
        description="报时间或摇卦，生成卦象与用神事实。"
        label="卦"
        href="/liuyao"
        action="开始起卦"
      />
      <TaskCard
        tone="clay"
        title="命盘合参"
        description="八字、紫微、七政至少两术互证。"
        label="合参"
        href="/hecan"
        action="开始合参"
      />
    </div>
  );
}
