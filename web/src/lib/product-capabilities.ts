export type ProductCapabilityId = "bazi" | "fortune" | "liuyao";

export type ProductCapabilityIcon = "archive" | "calendar" | "question";

export type ProductTaskTone = "paper" | "ink" | "clay";

export type ProductAction = {
  readonly href: string;
  readonly label: string;
};

export type ProductCapability = {
  readonly id: ProductCapabilityId;
  readonly href: string;
  readonly navigationLabel: string;
  readonly footerLabel: string;
  readonly icon: ProductCapabilityIcon;
  readonly activePrefixes: readonly string[];
  readonly home: {
    readonly eyebrow: string;
    readonly title: string;
    readonly description: string;
    readonly action: string;
    readonly meta: string;
    readonly tone: ProductTaskTone;
    readonly secondaryAction: ProductAction | undefined;
  };
};

/**
 * The public product truth. Public navigation, home tasks and footer links are
 * derived from this registry so unfinished ideas cannot drift into the UI.
 */
export const PRODUCT_CAPABILITIES = [
  {
    id: "bazi",
    href: "/app/profile/new",
    navigationLabel: "建立档案",
    footerLabel: "建立命理档案",
    icon: "archive",
    activePrefixes: ["/app/profile", "/app/bazi"],
    home: {
      eyebrow: "TASK 01 · 先建档",
      title: "建立档案 · 八字概览",
      description:
        "输入出生资料，先形成可复现的四柱事实，再查看覆盖整体格局与状态主线的白话概览。",
      action: "建立档案并查看八字",
      meta: "出生资料 → 四柱事实 → 八字概览",
      tone: "paper",
      secondaryAction: undefined,
    },
  },
  {
    id: "fortune",
    href: "/app/fortune/today",
    navigationLabel: "今日与近七日",
    footerLabel: "今日与近七日",
    icon: "calendar",
    activePrefixes: ["/app/fortune"],
    home: {
      eyebrow: "TASK 02 · 看节奏",
      title: "今日与近七日",
      description:
        "基于已确认档案查看短周期节奏，把今天和未来七日拆成能回看、能核对的提示。",
      action: "查看今日",
      meta: "已确认档案 → 今日 / 近七日",
      tone: "ink",
      secondaryAction: {
        href: "/app/fortune/week",
        label: "查看近七日",
      },
    },
  },
  {
    id: "liuyao",
    href: "/app/ask/liuyao",
    navigationLabel: "一事一问",
    footerLabel: "一事一问 · 六爻",
    icon: "question",
    activePrefixes: ["/app/ask/liuyao"],
    home: {
      eyebrow: "TASK 03 · 问工作事",
      title: "一事一问 · 六爻",
      description:
        "把一个事业或工作问题与起卦方式说清楚，再生成对应卦象与有边界的判断，不混入八字结论。",
      action: "开始六爻起卦",
      meta: "事业问题 → 起卦 → 卦象判断",
      tone: "clay",
      secondaryAction: undefined,
    },
  },
] as const satisfies readonly ProductCapability[];

export type PublicNavigationIcon = ProductCapabilityIcon;

export type PublicNavigationItem = {
  readonly href: string;
  readonly label: string;
  readonly icon: PublicNavigationIcon;
  readonly activePrefixes: readonly string[];
};

export const PUBLIC_PRIMARY_NAVIGATION = [
  ...PRODUCT_CAPABILITIES.map((capability) => ({
    href: capability.href,
    label: capability.navigationLabel,
    icon: capability.icon,
    activePrefixes: capability.activePrefixes,
  })),
] as const satisfies readonly PublicNavigationItem[];

export const PUBLIC_UTILITY_NAVIGATION = [
  { href: "/methodology", label: "方法与边界" },
  { href: "/pricing", label: "价格与交付" },
  { href: "/account", label: "账户" },
] as const;

export function isPublicNavigationItemActive(
  pathname: string,
  item: PublicNavigationItem,
) {
  return item.activePrefixes.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export const PUBLIC_FOOTER_APPLICATIONS = PRODUCT_CAPABILITIES.map(
  (capability) => ({
    href: capability.href,
    label: capability.footerLabel,
  }),
);

export const PUBLIC_INFORMATION_LINKS = [
  { href: "/methodology", label: "方法、证据与 AI 边界" },
  { href: "/pricing", label: "价格与交付" },
  { href: "/privacy", label: "隐私与数据处理" },
  { href: "/support", label: "支持与问题反馈" },
] as const;
