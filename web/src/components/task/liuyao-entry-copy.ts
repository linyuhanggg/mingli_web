/** /liuyao S0/S1 文案。逐字取自 2026-08-21-liuyao-flow-spec，不发明 GAP-LY。 */
export const LIUYAO_ENTRY_SUITABILITY = "就一个具体问题起卦，逐爻核验事实";
export const LIUYAO_ENTRY_SILHOUETTE_CAPTION = "提交后由服务端生成，可核验";
export const LIUYAO_ENTRY_CASTING_HINT =
  "需要你先用真实硬币（或既有记录）完成六次起卦，系统不代掷、不补数";
export const LIUYAO_LINE_PROCESS_HINT =
  "按实际起卦顺序记录初爻到上爻；六次全部完成后才能继续，不会随机补数。";
export const LIUYAO_COIN_KEY =
  "三背=老阳 9 · 二背一字=少阳 7 · 一背二字=少阴 8 · 三字=老阴 6";
export const LIUYAO_LINE_OPTIONS = [
  { value: "old-yin", label: "老阴（6 · 动）", yang: false, moving: true },
  { value: "young-yang", label: "少阳（7）", yang: true, moving: false },
  { value: "young-yin", label: "少阴（8）", yang: false, moving: false },
  { value: "old-yang", label: "老阳（9 · 动）", yang: true, moving: true },
] as const;
export const LIUYAO_LINE_NAMES = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"] as const;

export function liuyaoS6IncompleteMessage(index: number): string {
  const clamped = Math.min(Math.max(index, 0), LIUYAO_LINE_NAMES.length - 1);
  return `起卦记录不完整，请补全${LIUYAO_LINE_NAMES[clamped]} · 第 ${clamped + 1} 次`;
}
