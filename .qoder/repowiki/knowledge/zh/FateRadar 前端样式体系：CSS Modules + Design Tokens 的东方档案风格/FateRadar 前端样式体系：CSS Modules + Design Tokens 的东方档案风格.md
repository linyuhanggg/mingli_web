---
kind: frontend_style
name: FateRadar 前端样式体系：CSS Modules + Design Tokens 的东方档案风格
category: frontend_style
scope:
    - '**'
source_files:
    - design-system/mingli-web/MASTER.md
    - design-system/mingli-web/pages/home.md
    - web/src/app/globals.css
    - web/src/components/ui.module.css
    - web/src/components/site-chrome.module.css
    - web/src/components/private-shell.module.css
    - web/src/components/public-page-shell.module.css
    - web/src/components/editorial-page.module.css
    - web/src/components/readings/bazi-chart.module.css
    - web/src/components/readings/liuyao-hexagram.module.css
    - web/src/components/readings/reading-result.module.css
    - web/src/components/readings/evidence-list.module.css
    - web/src/components/readings/time-layer-tabs.module.css
    - admin/src/components/ui.module.css
    - admin/src/components/admin-shell.module.css
    - web/package.json
    - admin/package.json
---

## 1. 系统/方法

FateRadar 的前端（`web/` 与 `admin/`）统一采用 **Next.js App Router + CSS Modules** 的样式方案，不依赖 Tailwind、shadcn 运行时或任何 UI 组件库。设计决策由 `design-system/mingli-web/MASTER.md` 作为权威规范约束，并通过 `web/src/app/globals.css` 中的 CSS 自定义属性（Design Tokens）集中声明颜色、字体、间距、动效时长等全局变量，所有组件通过 `.module.css` 文件引用这些 token。

- 交互基础：`radix-ui`（无样式原子类，仅行为），图标使用 `lucide-react`。
- 动效：`motion/react`（即 framer-motion 的 v13 包），禁止引入 GSAP/Lenis/Lottie 等其他动画库。
- 表单：React Hook Form + Zod 校验，样式仍走 CSS Modules。
- 字体：通过 `@fontsource-variable/noto-sans-sc` 与 `@fontsource-variable/noto-serif-sc` 加载 Noto Sans SC / Noto Serif SC Variable，分别用于正文 UI 与标题展示。

## 2. 关键文件

- `design-system/mingli-web/MASTER.md`：设计系统总纲，定义色板、排版、间距、动效 token、栈契约与反模式清单。
- `design-system/mingli-web/pages/*.md`：页面级覆盖规则（如 `home.md`），当某页存在同名 md 时其规则优先于 Master。
- `web/src/app/globals.css`：全局 CSS 变量根节点，声明 `--ink-*`、`--ivory-*`、`--gold-*`、`--terracotta-*`、`--moss-*`、`--amber-*`、`--border-*`、`--surface-*`、`--shadow-*`、`--radius-*`、`--space-*`、`--duration-*`、`--ease-out-expo`、字体族与 `:root` 默认背景/文字。
- `web/src/components/ui.module.css`：公共按钮、容器、文本等基础样式，复用全局 token。
- `web/src/components/site-chrome.module.css`、`private-shell.module.css`、`public-page-shell.module.css`、`editorial-page.module.css` 等：页面壳层样式。
- `web/src/components/readings/*.module.css`：解读结果、八字盘、六爻卦、证据列表、时间轴等复杂业务组件的局部样式。
- `admin/src/components/ui.module.css`：管理后台共享按钮、字段、KPI 卡片、标签、登录卡片等样式。
- `admin/src/components/admin-shell.module.css`：后台整体布局壳。
- `web/package.json` / `admin/package.json`：声明 Next.js、React、Radix、Motion、Lucide、Noto 字体等依赖。

## 3. 架构与约定

### 设计令牌（Design Tokens）
所有视觉语义通过 CSS 变量暴露，组件只消费 token 而不硬编码颜色值。token 分为四类：
- 色彩角色：`--ink-950/900/800/700/500`（深墨）、`--ivory-50/100/200`（暖纸）、`--gold-400/500`（归档金）、`--terracotta-500/600`（陶土焦点/错误）、`--moss-100/700`（苔藓确认/边界）、`--amber-100`（琥珀待办）、`--white`。
- 边框/表面：`--border-subtle/control/emphasis/on-dark`、`--surface-card-translucent`、`--surface-ivory-translucent`、`--surface-header-translucent`。
- 阴影与圆角：`--shadow-hero-orbit/action/card/soft`、`--radius-sm/md/lg`。
- 动效：`--ease-out-expo`、`--duration-feedback/state/entrance/focal`。

### 组件样式组织
- 每个 React 组件与其 `.module.css` 同目录放置，通过 `import styles from './xxx.module.css'` 使用，避免全局命名冲突。
- 公共可复用样式集中在 `web/src/components/ui.module.css` 与 `admin/src/components/ui.module.css`；页面级 chrome 样式放在对应 shell 模块中。
- 业务组件（如 `readings/`）各自维护独立样式模块，体现“组件即单元”的模块化思路。

### 响应式策略
- 基于 CSS `@media (min-width: 48rem)` 等断点调整容器宽度（`--content: 74rem` 最大内容宽）。
- 设计系统要求支持 360 / 768 / 1024 / 1440 四档视口。
- 移动端通过 `touch-action: manipulation`、`-webkit-tap-highlight-color` 与 ≥44×44px 触控目标提升触摸体验。

### 无障碍与动效
- 全局 `:focus-visible` 使用 3px terracotta 描边 + 3px offset。
- `prefers-reduced-motion: reduce` 下禁用滚动平滑、动画与过渡（`globals.css` 与 `ui.module.css` 均有覆盖）。
- 头部包含 skip link（`.skipLink`）与 `aria-label` 导航区域。

### 主题/品牌约束
- 明确禁止“霓虹占星 SaaS / 算命庸俗风 / 紫色粉色 AI 渐变 / 聊天框首页”。
- 禁止随意引入 Tailwind、shadcn 运行时、MUI、AntD、第二套动效库——需先更新 `DESIGN.md`。
- 字体严格限定为 Noto Sans SC / Noto Serif SC Variable，不得切换 Lora/Raleway 或装饰书法体。

## 4. 约定与约束

| 类别 | 约定（描述性） | 来源/依据 |
|------|---------------|-----------|
| 样式技术栈 | 使用 CSS Modules + CSS 自定义属性，不使用 Tailwind/shadcn/MUI/AntD | `design-system/mingli-web/MASTER.md` “Stack Contract” |
| 动效库 | 仅允许 `motion/react`，禁止 GSAP/Lenis/Lottie | `MASTER.md` “Stack Contract” |
| 图标 | 仅 `lucide-react` 用于功能控制图标 | `MASTER.md` “Stack Contract” |
| 表单 | React Hook Form + Zod 校验 | `MASTER.md` “Stack Contract” |
| 颜色 | 必须使用 `--ink-*` / `--ivory-*` / `--gold-*` / `--terracotta-*` / `--moss-*` / `--amber-*` 等 token，禁止硬编码十六进制 | `web/src/app/globals.css` 与 `MASTER.md` 色板表 |
| 字体 | 标题用 Noto Serif SC Variable，正文/UI 用 Noto Sans SC Variable | `MASTER.md` “Typography” |
| 间距 | 使用 `--space-xs/sm/md/lg/xl/2xl/3xl` | `MASTER.md` “Spacing Variables” |
| 动效时长 | 反馈 ≤180ms，状态切换 260ms，入场 450ms，焦点场景 720ms | `MASTER.md` “Motion Tokens” |
| 响应式 | 至少适配 360/768/1024/1440 四档 | `MASTER.md` “Pre-Delivery Checklist” |
| 可访问性 | 键盘焦点可见、`prefers-reduced-motion` 生效、触控目标 ≥44×44px | `globals.css` + `MASTER.md` |
| 页面级覆盖 | 若 `design-system/mingli-web/pages/[page].md` 存在，则覆盖 Master 规则 | `MASTER.md` “LOGIC” |
| 反模式 | 禁止霓虹占星风、聊天框首页、紫粉渐变、布局属性动画、大面积持续模糊/发光、隐藏内容的运动 | `MASTER.md` “Avoid (Anti-patterns)” |
| 交付检查 | 无 emoji 图标、hover/press 150–300ms transform/opacity、focus 可见、reduced-motion 尊重、loading/empty/error 诚实 | `MASTER.md` “Pre-Delivery Checklist” |