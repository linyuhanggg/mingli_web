/** /meihua S0/S1 文案。逐字取自 2026-08-21-meihua-flow-spec，对照 DESIGN §2.3/§2.4/§7。 */
export const MEIHUA_ENTRY_SUITABILITY = "以一事一问起卦，看本互变三卦与体用";
export const MEIHUA_ENTRY_SILHOUETTE_CAPTION = "提交后由服务端生成，可核验";
export const MEIHUA_ENTRY_CASTING_HINT =
  "支持按时间、数字、声数、观察或已有卦象五种起法，按你实际用的方式提交";

export const MEIHUA_S1_ISSUE_HELP = "一事一卦";
export const MEIHUA_S1_EVENT_TIME_HELP = "时间起卦以此推卦；其他起法用于月令旺衰";
export const MEIHUA_S1_CASTING_METHOD_HELP =
  "按实际采用的起法提交，不会把数字、声音或观测资料改成时间起卦。";
export const MEIHUA_S1_TIME_HELP = "按事件时刻的干支数推上下卦与动爻，推导过程在结果页可核验";
export const MEIHUA_S1_NUMBER_SOURCE_HELP = "只记录来源，不让系统从自然语言自行猜卦。";
export const MEIHUA_S1_NUMBER_SOURCE_PLACEHOLDER = "例如：用户现场报数";
export const MEIHUA_S1_SOUND_SOURCE_PLACEHOLDER = "例如：现场声音计数";
export const MEIHUA_S1_OBSERVATION_HELP =
  "你观察到的物象对应的卦由你判定并录入；动爻由服务端按事件时间求得，不在此页推算";
export const MEIHUA_S1_HEXAGRAM_HELP = "用于已有卦象的复盘核验";

export const MEIHUA_S6_NUMBER = "请输入正整数起卦数字";
export const MEIHUA_S6_COUNT = "请输入正整数声数";
export const MEIHUA_S6_UPPER = "请选择上卦";
export const MEIHUA_S6_LOWER = "请选择下卦";
export const MEIHUA_S6_MOVING = "请选择 1 到 6 的动爻";
export const MEIHUA_S6_NUMBER_SOURCE = "请说明数字资料来源";
export const MEIHUA_S6_SOUND_SOURCE = "请说明声数观察来源";
export const MEIHUA_S6_OBSERVATION_SOURCE = "请说明观察来源";
export const MEIHUA_S6_HEXAGRAM_SOURCE = "请说明卦象资料来源";
export const MEIHUA_S6_METHOD = "请选择五种起法之一";

export const MEIHUA_CASTING_LABELS = {
  time: "按时间起卦",
  supplied_number: "按数字起卦",
  sound_count: "按声数起卦",
  observation: "按观察起卦",
  supplied_hexagram: "提供完整卦象",
} as const;

export const MEIHUA_TRIGRAM_OPTION_MARK = {
  乾: "☰",
  兑: "☱",
  离: "☲",
  震: "☳",
  巽: "☴",
  坎: "☵",
  艮: "☶",
  坤: "☷",
} as const;
