export type SecondarySurfaceState = "unavailable" | "need-login" | "empty";

export type SecondarySurfaceLink = {
  readonly href: string;
  readonly label: string;
};

export type SecondarySurfaceSection = {
  readonly title: string;
  readonly description: string;
  readonly items?: readonly string[];
};

export type SecondarySurfaceEntry = {
  readonly href: string;
  readonly title: string;
  readonly description: string;
  readonly status: string;
};

type SecondarySurfaceBase = {
  readonly eyebrow: string;
  readonly title: string;
  readonly intro: string;
  readonly state: SecondarySurfaceState;
  readonly statusTitle: string;
  readonly statusDescription: string;
  readonly action?: SecondarySurfaceLink;
  readonly sections?: readonly SecondarySurfaceSection[];
};

export type ContentFilterSpec = {
  readonly searchLabel: string;
  readonly topicLabel: string;
  readonly topics: readonly string[];
  readonly disabledReason: string;
};

export type PublicContentSource =
  | {
      readonly kind: "index";
      readonly prefix: string;
      readonly hrefBase?: string;
    }
  | {
      readonly kind: "item";
      readonly contentKey: string;
    };

export type PublicContentSurfaceSpec = SecondarySurfaceBase & {
  readonly entries?: readonly SecondarySurfaceEntry[];
  readonly contentFilters?: ContentFilterSpec;
  readonly form?: ToolInputFormSpec;
  readonly projectionTitle?: string;
  readonly projectionIntro?: string;
  readonly projectionHeading?: string;
};

export type ToolInputFieldSpec = {
  readonly id: string;
  readonly label: string;
  readonly type: "text" | "textarea";
  readonly hint: string;
};

export type ToolInputFormSpec = {
  readonly fields: readonly ToolInputFieldSpec[];
  readonly submitLabel: string;
  readonly disabledReason: string;
};

export type AuthFieldSpec = {
  readonly id: string;
  readonly label: string;
  readonly type: "email" | "password" | "tel" | "text";
  readonly autoComplete: string;
  readonly hint: string;
};

export type AuthSurfaceSpec = SecondarySurfaceBase & {
  readonly fields: readonly AuthFieldSpec[];
  readonly submitLabel: string;
  readonly links: readonly SecondarySurfaceLink[];
};

export type AccountSurfaceSpec = SecondarySurfaceBase & {
  readonly relatedLinks?: readonly SecondarySurfaceLink[];
};

export type CommerceSurfaceSpec = SecondarySurfaceBase & {
  readonly facts: readonly string[];
  readonly relatedLinks?: readonly SecondarySurfaceLink[];
};

const plannedTools = [
  {
    slug: "time-check",
    title: "寻时定盘",
    description: "围绕未知时辰生成十二个候选事实；提供结构化事件后可生成有界候选证据排序。",
    form: {
      fields: [
        { id: "time-check-range", label: "已知时间范围", type: "text", hint: "进入专用流程后由 Runtime 生成十二候选并标记范围命中。" },
        { id: "time-check-events", label: "可核对事件", type: "textarea", hint: "自由文本只记录事件条数；结构化事件输入可进入有界候选证据比较。" },
        { id: "time-check-event-facts", label: "结构化事件证据", type: "textarea", hint: "格式为日期、领域和事件标识；只生成候选证据排序，不生成古法校时结论。" },
      ],
    },
  },
  {
    slug: "chart-similarity",
    title: "同盘匹配",
    description: "只比较两份服务端确认命盘的八字四柱原值；不生成百分比、合婚或缘分结论。",
    form: {
      fields: [
        { id: "chart-similarity-chart", label: "左侧已确认盘面", type: "text", hint: "只接受服务端确认的档案，不在 URL 中放出生资料。" },
        { id: "chart-similarity-focus", label: "右侧已确认盘面", type: "text", hint: "结果只比较 Runtime 四柱原值，不计算相似度分数。" },
      ],
    },
  },
  {
    slug: "rhythm",
    title: "本命音律",
    description: "展示服务端确认的四柱纳音音律事实；不生成姓名学、吉凶或性格结论。",
    form: {
      fields: [
        { id: "rhythm-subject", label: "本命资料", type: "text", hint: "只展示资料入口，不读取或推断个人信息。" },
        { id: "rhythm-focus", label: "音律侧重", type: "text", hint: "当前结果只展示服务端四柱纳音事实，不生成音色或吉凶解释。" },
      ],
    },
  },
  {
    slug: "five-elements",
    title: "五行事实与调候",
    description: "展示服务端五行库存与调候适用性事实。旺衰、喜忌、用神没有可展示的结论。",
    form: {
      fields: [
        { id: "five-elements-chart", label: "已确认盘面", type: "text", hint: "必须绑定服务端确认的版本化盘面。" },
        { id: "five-elements-focus", label: "关注主题", type: "text", hint: "输入结构预制；当前不会输出喜忌结论。" },
      ],
    },
  },
  {
    slug: "dream",
    title: "解梦",
    description: "尚未开放。没有可展示的解梦结论。",
    form: {
      fields: [
        { id: "dream-content", label: "梦境内容", type: "textarea", hint: "尚未开放，当前不会生成解释。" },
        { id: "dream-context", label: "现实背景", type: "textarea", hint: "尚未开放，当前不会提交或保存。" },
      ],
    },
  },
  {
    slug: "name",
    title: "姓名分析",
    description: "尚未开放。没有可展示的姓名结论。",
    form: {
      fields: [
        { id: "name-value", label: "姓名", type: "text", hint: "尚未开放，当前不会保存或输出分析。" },
        { id: "name-context", label: "使用场景", type: "text", hint: "尚未开放，当前不会输出姓名结论。" },
      ],
    },
  },
] as const;

  const toolEntries = plannedTools.map((tool) => ({
  href: `/tools/${tool.slug}`,
  title: tool.title,
  description: tool.description,
  status:
    tool.slug === "time-check"
      ? "已接候选事实"
      : tool.slug === "rhythm"
      ? "已接事实"
      : tool.slug === "five-elements"
        ? "已接有界事实"
        : tool.slug === "chart-similarity"
          ? "已接有界事实"
        : "适配中",
}));

export const publicContentSurfaces = {
  tools: {
    eyebrow: "工具",
    title: "六项辅助工具，逐项说明能力边界。",
    intro: "入口已经保留。每项工具只会展示服务端确认的输入与结果，不在浏览器里补算或编造内容。",
    state: "unavailable",
    statusTitle: "工具能力暂不可用",
    statusDescription: "本命音律、五行事实、同盘比较和寻时定盘已接入有界 Runtime 事实；结构化事件可生成候选证据排序，但完整古法校时、候选淘汰和结论仍未启用，解梦和姓名分析仍只展示范围。",
    entries: toolEntries,
  },
  library: {
    eyebrow: "知识内容",
    title: "公开内容会标明来源、整理方式和更新时间。",
    intro: "内容索引只收录已经发布的真实文章与公开来源，不用演示标题填满页面。",
    state: "empty",
    statusTitle: "还没有已发布内容",
    statusDescription: "内容库当前为空。CMS 发布真实内容后，文章会出现在这里。",
    contentFilters: {
      searchLabel: "搜索内容",
      topicLabel: "按主题筛选",
      topics: ["全部主题", "术数基础", "现实核对", "方法与边界"],
      disabledReason: "当前没有已发布内容；发布内容后可用。",
    },
    sections: [
      {
        title: "发布规则",
        description: "每篇内容都要说明来源、整理方式、更新时间和适用边界。",
      },
    ],
  },
  article: {
    eyebrow: "知识内容",
    title: "这篇内容目前不可查看。",
    intro: "页面不会根据网址片段猜标题、作者或引文，也不会展示尚未发布的 CMS 草稿。",
    projectionTitle: "公开知识文章",
    projectionIntro: "以下正文来自已发布的 CMS 内容投影。",
    state: "empty",
    statusTitle: "没有可公开的文章",
    statusDescription: "文章尚未发布、已撤下，或内容服务尚未返回公开投影。",
    action: { href: "/library", label: "返回内容索引" },
  },
  daily: {
    eyebrow: "每日",
    title: "每日信息只展示当天真实可用的内容。",
    intro: "日期口径、确定性数据与运营内容都由服务端确认；当前不会根据浏览器时间拼出临时结论。",
    projectionTitle: "每日",
    projectionIntro: "以下内容来自当天已发布的 CMS 投影。",
    projectionHeading: "今日内容",
    state: "unavailable",
    statusTitle: "每日能力暂不可用",
    statusDescription: "每日数据源和展示合同尚未接通。可用前不会显示假日期、假宜忌或假解读。",
  },
} satisfies Record<string, PublicContentSurfaceSpec>;

const unknownToolSurface: PublicContentSurfaceSpec = {
  eyebrow: "工具",
  title: "这个工具入口尚未开放。",
  intro: "只有已冻结的六项工具会进入公开产品地图；页面不会根据网址片段猜测功能。",
  state: "unavailable",
  statusTitle: "工具暂不可用",
  statusDescription: "请返回工具总览查看已经登记的入口。",
  action: { href: "/tools", label: "返回工具总览" },
};

export function getToolSurface(slug: string): PublicContentSurfaceSpec {
  const tool = plannedTools.find((candidate) => candidate.slug === slug);
  if (!tool) return unknownToolSurface;

  return {
    eyebrow: "工具",
    title: tool.title,
    intro: tool.description,
    projectionTitle: tool.title,
    projectionIntro: "以下说明来自已发布的 CMS 内容投影。",
    projectionHeading: "已发布说明",
    state: "unavailable",
    statusTitle: `${tool.title}暂不可用`,
    statusDescription: "确定性合同和真实服务尚未接通；当前不会收集输入或生成结果。",
    form: {
      fields: tool.form.fields,
      submitLabel: "提交暂未开放",
      disabledReason: "尚未开放。当前不会提交或保存资料。",
    },
    action: { href: "/tools", label: "返回工具总览" },
  };
}

export function getToolContentSource(slug: string): PublicContentSource | undefined {
  const tool = plannedTools.find((candidate) => candidate.slug === slug);
  return tool ? { kind: "item", contentKey: `tools.${tool.slug}` } : undefined;
}

const identityField: AuthFieldSpec = {
  id: "login-identity",
  label: "手机或邮箱",
  type: "text",
  autoComplete: "username",
  hint: "当前只展示字段结构，不会发送、验证或保存联系方式。",
};

const passwordField: AuthFieldSpec = {
  id: "login-password",
  label: "密码",
  type: "password",
  autoComplete: "current-password",
  hint: "密码登录服务接通前，此字段保持只读。",
};

const policyLinks = [
  { href: "/privacy", label: "查看隐私政策" },
  { href: "/terms", label: "查看服务条款" },
] as const;

export const authSurfaces = {
  login: {
    eyebrow: "登录",
    title: "登录",
    intro: "登录后进入账户",
    state: "unavailable",
    statusTitle: "登录暂不可用",
    statusDescription: "身份服务接通前，登录表单只展示永久标签和流程边界，不会创建会话。",
    fields: [identityField, passwordField],
    submitLabel: "登录暂未开放",
    links: [
      { href: "/auth/register", label: "创建账号" },
      { href: "/auth/recover", label: "找回账号" },
      ...policyLinks,
    ],
  },
  register: {
    eyebrow: "注册",
    title: "注册",
    intro: "先验证手机或邮箱，再设密码并同意政策。",
    state: "unavailable",
    statusTitle: "注册暂不可用",
    statusDescription: "OTP、密码设置、政策版本和身份冲突处理接通后再开放。",
    fields: [
      { ...identityField, id: "register-identity" },
      {
        id: "register-code",
        label: "验证码",
        type: "text",
        autoComplete: "one-time-code",
        hint: "当前不会发送或验证验证码。",
      },
      {
        ...passwordField,
        id: "register-password",
        autoComplete: "new-password",
        hint: "密码服务接通前，此字段保持只读。",
      },
    ],
    submitLabel: "注册暂未开放",
    links: [{ href: "/auth/login", label: "返回登录" }, ...policyLinks],
  },
  verify: {
    eyebrow: "验证身份",
    title: "验证身份",
    intro: "验证后进入账户",
    state: "unavailable",
    statusTitle: "验证暂不可用",
    statusDescription: "请等待验证码服务接通，并从登录或注册入口开始。",
    fields: [
      {
        id: "verification-code",
        label: "验证码",
        type: "text",
        autoComplete: "one-time-code",
        hint: "当前不会发送、读取或验证验证码。",
      },
    ],
    submitLabel: "验证暂未开放",
    links: [{ href: "/auth/login", label: "返回登录" }],
  },
  setPassword: {
    eyebrow: "设置密码",
    title: "设置密码",
    intro: "为当前账户设置密码。",
    state: "unavailable",
    statusTitle: "密码设置暂不可用",
    statusDescription: "身份验证、密码哈希和会话撤销能力接通后再开放。",
    fields: [
      {
        ...passwordField,
        id: "new-password",
        label: "新密码",
        autoComplete: "new-password",
        hint: "当前不会读取或保存新密码。",
      },
      {
        ...passwordField,
        id: "confirm-password",
        label: "确认新密码",
        autoComplete: "new-password",
        hint: "两次密码核对能力接通前，此字段保持只读。",
      },
    ],
    submitLabel: "设置密码暂未开放",
    links: [{ href: "/auth/login", label: "返回登录" }],
  },
  recover: {
    eyebrow: "找回账号",
    title: "找回账号",
    intro: "用已验证的手机或邮箱重设密码。成功后其他已登录设备会退出。",
    state: "unavailable",
    statusTitle: "账号找回暂不可用",
    statusDescription: "身份恢复服务接通后再开放。",
    fields: [{ ...identityField, id: "recover-identity" }],
    submitLabel: "找回账号暂未开放",
    links: [{ href: "/auth/login", label: "返回登录" }],
  },
  consent: {
    eyebrow: "政策同意",
    title: "政策同意",
    intro: "请分别确认隐私政策和服务条款。",
    state: "unavailable",
    statusTitle: "政策确认暂不可用",
    statusDescription: "政策版本与服务端同意记录接通后再开放。",
    fields: [],
    submitLabel: "确认暂未开放",
    links: [
      { href: "/privacy", label: "查看隐私政策" },
      { href: "/terms", label: "查看服务条款" },
      { href: "/auth/login", label: "返回登录" },
    ],
    sections: [
      {
        title: "不会默认勾选",
        description: "隐私政策、服务条款和活动确认会分别呈现，不用一个模糊选项覆盖全部事实。",
      },
    ],
  },
} satisfies Record<string, AuthSurfaceSpec>;

const loginAction = { href: "/auth/login", label: "前往登录" } as const;

export const accountSurfaces = {
  profiles: {
    eyebrow: "个人中心 · 档案",
    title: "受测人档案",
    intro: "档案用于复用资料，不是免费起盘的前置条件。未确认当前身份前，不展示任何档案或出生资料。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "登录后才能查看自己的 ProfileVersion、授权状态和保存记录。",
    action: loginAction,
  },
  profileDetail: {
    eyebrow: "个人中心 · 档案详情",
    title: "档案版本与授权边界",
    intro: "页面不会根据网址中的不透明标识猜测或展示出生资料。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "确认身份和档案访问权后，服务端才会返回详情。",
    action: loginAction,
  },
  history: {
    eyebrow: "个人中心 · 推演历史",
    title: "任务、版本与报告历史",
    intro: "历史按 ReadingRoot 和版本组织。未登录时不加载任务、盘面或报告。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "登录后才能查看属于你的真实推演历史；当前没有演示记录。",
    action: loginAction,
  },
  historyDetail: {
    eyebrow: "个人中心 · 历史详情",
    title: "一份任务的版本与交付记录",
    intro: "网址只包含不透明标识，不会被用来推断或公开盘面与报告。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "身份与任务访问权确认后，服务端才会返回版本和正文。",
    action: loginAction,
  },
  orders: {
    eyebrow: "个人中心 · 订单",
    title: "订单、支付与权益分开记录",
    intro: "未登录时不展示金额、渠道、状态或权益，也不会放入模拟订单。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "登录后才能查看服务端确认的订单和支付事实。",
    action: loginAction,
  },
  entitlements: {
    eyebrow: "个人中心 · 权益",
    title: "权益只来自追加式账本",
    intro: "这里不是余额钱包。未登录时不展示权益数量、到期时间或使用记录。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "登录后才能查看属于你的权益投影。",
    action: loginAction,
  },
  invitations: {
    eyebrow: "个人中心 · 邀请",
    title: "只展示自己的邀请事实",
    intro: "不做公开排行榜，也不展示他人的账号、付款或命理资料。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "登录后才能查看自己的归因、进度、奖励、过期和冲正记录。",
    action: loginAction,
  },
  notifications: {
    eyebrow: "个人中心 · 通知",
    title: "重要状态保留在站内",
    intro: "未登录时不加载任务、退款、导出或账号安全通知，也不生成虚假完成提醒。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "登录后才能查看属于你的站内通知。",
    action: loginAction,
  },
  settings: {
    eyebrow: "个人中心 · 设置",
    title: "账号、偏好与数据权利集中管理",
    intro: "未确认身份前不读取或修改任何设置。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "登录后才能管理账户安全、通知偏好和隐私选择。",
    action: loginAction,
    relatedLinks: [
      { href: "/account/settings/security", label: "账户安全" },
      { href: "/account/settings/preferences", label: "通知偏好" },
      { href: "/account/settings/privacy-data", label: "隐私与数据" },
    ],
  },
  security: {
    eyebrow: "个人中心 · 安全",
    title: "密码、身份与设备会话分开管理",
    intro: "未登录时不展示已绑定身份、设备或安全事件。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "登录后才能设置密码、撤销设备会话和处理身份冲突。",
    action: loginAction,
  },
  preferences: {
    eyebrow: "个人中心 · 偏好",
    title: "通知选择不改变事实记录",
    intro: "未登录时不读取或保存邮件、短信和站内通知偏好。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "登录后才能查看和修改可选通知渠道。",
    action: loginAction,
  },
  privacyData: {
    eyebrow: "个人中心 · 隐私与数据",
    title: "导出、删除和注销都有明确状态",
    intro: "未登录时不显示请求记录，也不会执行任何导出、删除或注销。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "登录后才能进入数据权利流程。",
    action: loginAction,
  },
  dataRights: {
    eyebrow: "个人中心 · 数据权利",
    title: "查看请求、处理结果和撤销窗口",
    intro: "未确认身份时不创建导出任务、不删除数据，也不展示既有请求。",
    state: "need-login",
    statusTitle: "需要登录",
    statusDescription: "登录后才能提交和查看属于你的数据权利请求。",
    action: loginAction,
  },
} satisfies Record<string, AccountSurfaceSpec>;

export const commerceSurfaces = {
  checkout: {
    eyebrow: "结账",
    title: "结账",
    intro: "当前没有可购买的商品。",
    state: "unavailable",
    statusTitle: "测试期未开放",
    statusDescription: "购买尚未开放。",
    facts: [
      "客户端回跳不代表到账",
      "支付、权益授予、生成与交付分别确认",
      "当前不会创建或保存订单",
    ],
    relatedLinks: policyLinks,
  },
  order: {
    eyebrow: "订单",
    title: "订单",
    intro: "查看这份订单。",
    state: "unavailable",
    statusTitle: "测试期未开放",
    statusDescription: "当前不会声称订单存在或已经付款。",
    facts: [
      "没有服务端订单快照就不展示金额",
      "没有渠道确认就不展示支付成功",
      "没有账本事件就不展示权益",
    ],
    relatedLinks: policyLinks,
  },
  share: {
    eyebrow: "限时分享",
    title: "分享只展示服务端隐私投影",
    intro: "页面不会根据网址中的分享标识猜测档案、盘面或报告，也不会展示见相原图。",
    state: "unavailable",
    statusTitle: "分享内容暂不可用",
    statusDescription: "限时、可撤销的 ShareSnapshot 公开投影尚未接到此页面。",
    facts: [
      "分享默认限时并可随时撤销",
      "手机号、邮箱、精确地点和订单不会公开",
      "见相分享不包含原图或标注图",
    ],
  },
  invite: {
    eyebrow: "邀请活动",
    title: "先验证活动，再决定是否建立归因",
    intro: "当前不会根据邀请码锁定归因、占用名额或展示邀请人身份。",
    state: "unavailable",
    statusTitle: "邀请活动暂不可用",
    statusDescription: "活动版本、有效期、自邀检查、名额和注册锁定尚未接到此页面。",
    facts: [
      "只有有效活动才能建立临时归因",
      "既有账号、重复归因与自邀无效",
      "页面不展示排行榜、收益榜或虚假倒计时",
    ],
  },
} satisfies Record<string, CommerceSurfaceSpec>;
