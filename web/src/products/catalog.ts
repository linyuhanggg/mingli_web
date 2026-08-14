export type ProductId =
  | "bazi"
  | "ziwei"
  | "qizheng"
  | "liuyao"
  | "meihua"
  | "qimen"
  | "daliuren"
  | "jianxiang"
  | "hecan"
  | "canwen"
  | "wenshi";

export type ProductGroup = "natal" | "event" | "observation" | "cross";

export type ProductDefinition = {
  id: ProductId;
  name: string;
  href: `/${string}`;
  group: ProductGroup;
  headline: string;
  summary: string;
  suitableFor: string;
  inputLead: string;
  moduleTitle: string;
  modules: readonly string[];
  unavailableReason: string;
};

export const PRODUCT_CATALOG = {
  bazi: {
    id: "bazi",
    name: "八字",
    href: "/bazi",
    group: "natal",
    headline: "从出生资料建立四柱",
    summary: "确认历法、时间与地点口径，查看四柱、五行与可用时间层。",
    suitableFor: "长期结构、阶段节奏与个人资料建档",
    inputLead: "出生日期",
    moduleTitle: "四柱与五行力量",
    modules: [
      "时间口径与四柱摘要",
      "年月日时四柱",
      "十神、藏干、纳音、空亡、地势与自坐",
      "神煞与特殊宫位",
      "旺衰贡献",
      "格局、喜忌与病药依据",
      "大运、流年与关键流月",
      "四柱图与五行力量",
    ],
    unavailableReason: "八字深读、追问和导出仍在接入；确定性四柱盘面已由 Runtime 生成。",
  },
  ziwei: {
    id: "ziwei",
    name: "紫微",
    href: "/ziwei",
    group: "natal",
    headline: "从命宫进入十二宫",
    summary: "确认出生资料与时间口径，查看十二宫、星曜、四化和时间层。",
    suitableFor: "角色结构、宫位主题与阶段观察",
    inputLead: "出生资料",
    moduleTitle: "十二宫与四化",
    modules: [
      "十二宫盘与宫位交互",
      "主星、辅星与杂曜",
      "三方四正",
      "四化",
      "格局与命宫摘要",
      "大限、流年与可用时间层",
    ],
    unavailableReason: "紫微深读、时间层和导出仍在接入；确定性十二宫盘面已由 Runtime 生成。",
  },
  qizheng: {
    id: "qizheng",
    name: "七政",
    href: "/qizheng",
    group: "natal",
    headline: "用时间与地点建立星盘",
    summary: "校准出生地点和时间口径，查看星盘、宿度、十二宫和限法。",
    suitableFor: "星曜位置、宫位结构与时限观察",
    inputLead: "出生地点",
    moduleTitle: "星盘与十一曜",
    modules: [
      "星盘",
      "命度与身度",
      "命盘格局",
      "功能十二宫",
      "十一曜宿度",
      "恩用仇难",
      "大限、小限与神煞落宫",
    ],
    unavailableReason: "七政深读、时间层和导出仍在接入；确定性星体位置已由 Runtime 生成。",
  },
  liuyao: {
    id: "liuyao",
    name: "六爻",
    href: "/liuyao",
    group: "event",
    headline: "围绕一件事记录起卦过程",
    summary: "写清问题与场景，保留六次过程，再进入本卦、变卦和事实摘要。",
    suitableFor: "边界清楚、时间明确的一事一问",
    inputLead: "起卦方式",
    moduleTitle: "六次过程与本卦变卦",
    modules: [
      "问题与起卦依据",
      "六次起卦过程",
      "本卦与变卦",
      "六爻、六亲与世应",
      "动静、旬空、月日等事实",
      "基础摘要与适用边界",
    ],
    unavailableReason: "六爻事件深读、追问和导出仍在接入；卦盘事实已由 Runtime 生成。",
  },
  meihua: {
    id: "meihua",
    name: "梅花易数",
    href: "/meihua",
    group: "event",
    headline: "按五种方式起一卦",
    summary: "写清一件事和起卦依据，先查看本卦、互卦、变卦与体用结构。",
    suitableFor: "具体事件、状态变化与行动观察",
    inputLead: "事件时间",
    moduleTitle: "本卦、互卦与体用",
    modules: [
      "问题与起卦时空",
      "本卦、互卦与变卦",
      "动爻",
      "体卦与用卦",
      "五行生克关系事实",
      "起卦方式与适用边界",
    ],
    unavailableReason: "梅花深读、追问和导出仍在接入；五种起法的确定性盘面已由 Runtime 生成。",
  },
  qimen: {
    id: "qimen",
    name: "奇门",
    href: "/qimen",
    group: "event",
    headline: "用问题与事件时空起局",
    summary: "先确定场景侧重和发生时空，再进入九宫、星门神与用神锚点。",
    suitableFor: "行动选择、局势判断与具体事件",
    inputLead: "场景侧重",
    moduleTitle: "九宫与值符值使",
    modules: [
      "阴遁、阳遁与局式",
      "九宫",
      "九星、八门与八神",
      "值符与值使",
      "用神锚点",
      "关键格局与大局基调",
    ],
    unavailableReason: "奇门事件深读、追问和导出仍在接入；九宫局式已由 Runtime 生成。",
  },
  daliuren: {
    id: "daliuren",
    name: "大六壬",
    href: "/daliuren",
    group: "event",
    headline: "围绕明确问题建立课盘",
    summary: "确认判断侧重与事件时空，再查看天地盘、四课三传和课体候选。",
    suitableFor: "人事进展、关系变化与事件推演",
    inputLead: "判断侧重",
    moduleTitle: "四课三传",
    modules: [
      "天地盘",
      "四课",
      "三传",
      "九宗门",
      "天将",
      "课体候选",
      "关键神煞与盘面综览",
    ],
    unavailableReason: "大六壬事件深读、追问和导出仍在接入；四课三传已由 Runtime 生成。",
  },
  jianxiang: {
    id: "jianxiang",
    name: "见相",
    href: "/jianxiang",
    group: "observation",
    headline: "先授权，再采集可核对观察",
    summary: "选择面相、手相、体态或综合观照，独立同意后拍摄或上传。",
    suitableFor: "结构化视觉观察与用户补充信息",
    inputLead: "独立同意",
    moduleTitle: "结构化观察与证据充足度",
    modules: [
      "原图采集与质量检查",
      "版本化结构化观察",
      "部位、区域与置信度",
      "质量与证据充足度",
      "用户补充信息",
      "基础摘要与分享排除项",
    ],
    unavailableReason: "照片质量检查与视觉适配器尚未接入；现在不会上传或保存照片。",
  },
  hecan: {
    id: "hecan",
    name: "命盘合参",
    href: "/hecan",
    group: "cross",
    headline: "八字、紫微、七政至少选两术",
    summary: "先立命，再按主理与参证选择术数，分开呈现互证、分歧和缺失；可带着具体问题进入（原多盘问答）。",
    suitableFor: "同一人的长期结构交叉核对",
    inputLead: "至少选择两术",
    moduleTitle: "互证、分歧与缺失",
    modules: ["各术精简盘面", "主理与参证信号", "共同印证", "分歧与适用边界", "缺失能力", "整合深读"],
    unavailableReason: "结构化合参已接通；实质互证、深读和追问仍在接入。",
  },
  canwen: {
    id: "canwen",
    name: "多盘问答",
    href: "/canwen",
    group: "cross",
    headline: "一个问题，选择需要的命盘",
    summary: "先立命和选术，再设定深度与表达方式；追问始终绑定同一报告根。",
    suitableFor: "需要跨命盘回答并保留同根追问的问题",
    inputLead: "表达偏好",
    moduleTitle: "一问多盘与同根追问",
    modules: ["问题与立命版本", "八字、紫微、七政选术", "深度与表达偏好", "一问多盘判断", "同根追问", "越界 Recast"],
    unavailableReason: "多盘问答的共同事实范围已接通；七政跨术范围、实质互证、深读和追问仍在接入。",
  },
  wenshi: {
    id: "wenshi",
    name: "问事合参",
    href: "/wenshi",
    group: "cross",
    headline: "同一问题、同一时刻比较三盘",
    summary: "先完成六爻起卦，再生成大六壬与奇门，最后才做整合判断。",
    suitableFor: "需要三种事件术数交叉核对的同一问题",
    inputLead: "同一问题与时空",
    moduleTitle: "六爻、大六壬与奇门",
    modules: ["同一问题与时空", "六爻先行起卦", "六爻、大六壬与奇门三盘", "三盘生成状态", "共同信号与分歧", "免费概览与整合深读"],
    unavailableReason: "三术事件盘已接入；当前只展示各术结构事实，不生成未经 Runtime 声明的实质性互证结论。",
  },
} as const satisfies Record<ProductId, ProductDefinition>;

export const NATAL_PRODUCTS = [PRODUCT_CATALOG.bazi, PRODUCT_CATALOG.ziwei, PRODUCT_CATALOG.qizheng] as const;
export const EVENT_PRODUCTS = [PRODUCT_CATALOG.liuyao, PRODUCT_CATALOG.meihua, PRODUCT_CATALOG.qimen, PRODUCT_CATALOG.daliuren] as const;
// 2026-08-14 起多盘问答并入命盘合参（DESIGN §8.5）：
// canwen 仍是 PRODUCT_CATALOG 成员（历史任务与 ViewModel 保留），但不再是顶级产品入口。
export const CROSS_PRODUCTS = [PRODUCT_CATALOG.hecan, PRODUCT_CATALOG.wenshi] as const;

export function getProductDefinition(id: ProductId): ProductDefinition {
  return PRODUCT_CATALOG[id];
}
