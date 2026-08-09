---
name: FateRadar
description: 东方编辑档案：把时间变成私密、可核对的个人档案。
colors:
  ink-950: "#0a2823"
  ink-900: "#123a32"
  ink-800: "#1b4b41"
  ink-700: "#345f55"
  ivory-50: "#fffdf7"
  ivory-100: "#f8f3e7"
  ivory-200: "#eee5d3"
  gold-500: "#a9853f"
  gold-400: "#c1a263"
  terracotta-500: "#a85e46"
  terracotta-600: "#884532"
  moss-100: "#dfe9df"
  moss-700: "#2d6253"
  amber-100: "#f2e6c8"
  white: "#ffffff"
  border-subtle: "rgb(18 58 50 / 12%)"
  border-control: "rgb(18 58 50 / 20%)"
  border-emphasis: "rgb(18 58 50 / 25%)"
  border-on-dark: "rgb(248 243 231 / 14%)"
  surface-card-translucent: "rgb(255 255 255 / 64%)"
  surface-ivory-translucent: "rgb(255 253 247 / 72%)"
  text-on-dark-secondary: "rgb(248 243 231 / 78%)"
  text-on-dark-muted: "rgb(248 243 231 / 68%)"
typography:
  display:
    fontFamily: '"Noto Serif SC Variable", ui-serif, "Songti SC", "STSong", "Noto Serif CJK SC", serif'
    fontSize: "clamp(3.25rem, 10.5vw, 6rem)"
    fontWeight: 560
    lineHeight: 0.98
    letterSpacing: "-0.04em"
  headline:
    fontFamily: '"Noto Serif SC Variable", ui-serif, "Songti SC", "STSong", "Noto Serif CJK SC", serif'
    fontSize: "clamp(2.45rem, 7vw, 4.8rem)"
    fontWeight: 580
    lineHeight: 1.04
    letterSpacing: "-0.04em"
  title:
    fontFamily: '"Noto Serif SC Variable", ui-serif, "Songti SC", "STSong", "Noto Serif CJK SC", serif'
    fontSize: "clamp(1.45rem, 4vw, 2.15rem)"
    fontWeight: 600
    lineHeight: 1.16
    letterSpacing: "-0.025em"
  body:
    fontFamily: '"Noto Sans SC Variable", ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.65
    letterSpacing: "normal"
  label:
    fontFamily: '"Noto Sans SC Variable", ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif'
    fontSize: "0.72rem"
    fontWeight: 730
    lineHeight: 1.65
    letterSpacing: "0.08em"
rounded:
  sm: "0.75rem"
  md: "1.25rem"
  lg: "2rem"
components:
  button-primary:
    backgroundColor: "{colors.ink-900}"
    textColor: "{colors.ivory-50}"
    rounded: "{rounded.sm}"
    padding: "0.72rem 1.15rem"
  button-primary-hover:
    backgroundColor: "{colors.ink-800}"
    textColor: "{colors.ivory-50}"
    rounded: "{rounded.sm}"
    padding: "0.72rem 1.15rem"
  button-secondary:
    backgroundColor: "{colors.surface-ivory-translucent}"
    textColor: "{colors.ink-900}"
    rounded: "{rounded.sm}"
    padding: "0.72rem 1.15rem"
  button-secondary-hover:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink-900}"
    rounded: "{rounded.sm}"
    padding: "0.72rem 1.15rem"
  input-field:
    backgroundColor: "{colors.ivory-50}"
    textColor: "{colors.ink-950}"
    rounded: "{rounded.sm}"
    padding: "0.7rem 0.8rem"
  choice-card:
    backgroundColor: "{colors.ivory-50}"
    textColor: "{colors.ink-950}"
    rounded: "{rounded.sm}"
    padding: "0.75rem"
  choice-card-selected:
    backgroundColor: "{colors.moss-100}"
    textColor: "{colors.ink-950}"
    rounded: "{rounded.sm}"
    padding: "0.75rem"
  task-card-paper:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink-950}"
    rounded: "{rounded.md}"
    padding: "clamp(1.45rem, 4vw, 2.2rem)"
  status-panel:
    backgroundColor: "{colors.surface-card-translucent}"
    textColor: "{colors.ink-950}"
    rounded: "{rounded.md}"
    padding: "clamp(1.25rem, 5vw, 2rem)"
  state-tag-processing:
    backgroundColor: "{colors.amber-100}"
    textColor: "{colors.ink-950}"
    rounded: "999px"
    padding: "0 0.55rem"
  state-tag-success:
    backgroundColor: "{colors.moss-100}"
    textColor: "{colors.ink-950}"
    rounded: "999px"
    padding: "0 0.55rem"
  state-tag-error:
    backgroundColor: "{colors.ivory-100}"
    textColor: "{colors.terracotta-600}"
    rounded: "999px"
    padding: "0 0.55rem"
  time-archive:
    backgroundColor: "rgb(255 253 247 / 4%)"
    textColor: "{colors.ivory-50}"
    rounded: "{rounded.lg}"
    padding: "clamp(1.25rem, 4vw, 2rem)"
---

# FateRadar Design System

> Status: Accepted
> Updated: 2026-08-09
> Scope: responsive website first; future native iOS should preserve the same brand language

## 1. Design thesis

The creative north star is **Eastern Editorial Archive** / **东方编辑档案**: a contemporary personal archive shaped by time, evidence, traditional calculation, and restrained Chinese editorial design.

The product should feel calm, precise, private, and premium. It must not look like an enterprise dashboard, a neon astrology SaaS, a fortune-teller stall, or a chat interface with a decorative skin.

The existing brand image and website tokens are the starting point:

- deep ink green carries trust, depth, and privacy;
- warm ivory provides a paper-like reading surface;
- muted gold marks hierarchy and important evidence;
- terracotta is reserved for focus, warning, and small warm accents;
- generous negative space and clear typography create the premium feeling.

FateRadar 把时间变成一份私密、可核对的个人档案。视觉系统像一册正在整理的东方编辑档案：深墨绿承担封面与权威，暖象牙承担长时间阅读，克制金线标出层级，少量陶土色只在焦点、错误与需要谨慎的地方出现。它拒绝把首页做成聊天框，也不借神秘装饰掩盖事实、条件和不确定性。

公共入口先让访客看懂确定性核心、可核对依据、表达边界和三个 P0 任务，再决定是否登录保存。当前首屏是深色编辑扉页：一个大承诺、两项行动、时间刻度仪表和三项可信事实共同完成叙事。私人区域则收起表现性装饰，让输入、状态、证据和版本成为主角。

深墨段落是封面、价格账簿和证据侧栏的局部材料，不是全站暗色模式。FORM 为 `Eastern Editorial Archive`，方向合同 key 为 `FATERADAR-EASTERN-ARCHIVE-V1`；任何新页面都应保留这套纸张、墨色、细金线与可核对层级。

Key characteristics:

- 深墨封面与暖象牙纸张形成明确的阅读层次。
- 宋体/衬线负责标题、结论与档案感，无衬线负责操作、表单与说明。
- 细边界、轻圆角和节制阴影建立结构，不堆叠浮卡。
- 金色只标层级与证据，陶土色只标焦点、错误和有限提醒。
- 状态、边界和门禁用直白文字说明，不靠颜色或装饰暗示成功。
- 时间刻度、编号和账簿式分隔是可复用的档案语汇。

## 2. What we take from Metis

Metis is a structural and interaction reference, not a brand template.

Adopt:

- an editorial landing page rather than an empty chat box;
- a large typographic hero with one clear promise;
- large scene cards for real user tasks;
- numbered modules only when order or sequence is meaningful;
- trial before forced login;
- clear Free versus paid-result comparison;
- restrained fixed navigation and direct payment-status feedback.

Do not copy:

- the Metis wordmark, imagery, copy, exact composition, or private APIs;
- its black-and-white identity as our default palette;
- permanent-unlimited AI promises or browser-local sensitive history;
- any layout whose only purpose is to imitate the reference site.

## 3. Visual language

### Color

Use the semantic tokens already defined in `web/src/app/globals.css`. The frontmatter at the top of this file is the machine-readable source of truth for every token value; the table below is the canonical role mapping.

| Role | Token | Value |
| --- | --- | --- |
| Primary text / deepest surface | `--ink-950` | `#0a2823` |
| Brand surface / primary action | `--ink-900` | `#123a32` |
| Interactive brand hover | `--ink-800` | `#1b4b41` |
| Secondary text | `--ink-700` | `#345f55` |
| Canvas | `--ivory-50` | `#fffdf7` |
| Soft surface | `--ivory-100` | `#f8f3e7` |
| Divided section / disabled surface | `--ivory-200` | `#eee5d3` |
| Primary accent | `--gold-500` | `#a9853f` |
| Soft accent | `--gold-400` | `#c1a263` |
| Focus / warning accent | `--terracotta-500` | `#a85e46` |
| Error text / required marker | `--terracotta-600` | `#884532` |
| Selected / success surface | `--moss-100` | `#dfe9df` |
| Selected / success boundary | `--moss-700` | `#2d6253` |
| Pending surface (always with status copy) | `--amber-100` | `#f2e6c8` |
| Clean sheet (paper cards, reading text) | `--white` | `#ffffff` |
| Fine rule, quiet | `--border-subtle` | `rgb(18 58 50 / 12%)` |
| Fine rule, control | `--border-control` | `rgb(18 58 50 / 20%)` |
| Fine rule, emphasis | `--border-emphasis` | `rgb(18 58 50 / 25%)` |
| Fine rule, on dark | `--border-on-dark` | `rgb(248 243 231 / 14%)` |
| Translucent paper (status panels) | `--surface-card-translucent` | `rgb(255 255 255 / 64%)` |
| Translucent paper (secondary actions) | `--surface-ivory-translucent` | `rgb(255 253 247 / 72%)` |
| Copy on dark, secondary | `--text-on-dark-secondary` | `rgb(248 243 231 / 78%)` |
| Copy on dark, muted | `--text-on-dark-muted` | `rgb(248 243 231 / 68%)` |

Role guidance:

- **Deep Archive Ink**（`ink-950`）：首屏、价格段落和最深正文色，制造私密与确定性。
- **Working Ink**（`ink-900`）：主要操作、私人侧栏与选中控件的品牌表面。
- **Active Ink**（`ink-800`）：主要操作 hover 与成功图标的互动层。
- **Archival Gold**（`gold-500`）：分隔线、编号、聚焦层级和少量证据标记。
- **Soft Archival Gold**（`gold-400`）：深墨表面上的高光、选中边和正文强调。
- **Terracotta Focus**（`terracotta-500`）：全局焦点环、无效输入边界和警示图标。
- **Deep Terracotta**（`terracotta-600`）：错误文字与必填标记；不可扩张为普通品牌色。
- **Moss Confirmation**（`moss-100` / `moss-700`）：已选择和成功状态的底色与边界。
- **Amber Pending**（`amber-100`）：处理中状态的浅底色，必须同时带状态文案。
- **Reading Ink**（`ink-700`）：正文次级文字、帮助信息和非主导导航。
- **Warm Paper**（`ivory-50`）：全站默认画布与浅色控件表面。
- **Soft Paper**（`ivory-100`）：私人应用背景、提示和次级表面。
- **Divided Paper**（`ivory-200`）：分区背景与禁用控件表面。
- **Clean Sheet**（`white`）：真正需要抬起的纸张卡片与阅读正文。
- **Fine Rules**（`border-subtle` / `border-control` / `border-emphasis` / `border-on-dark`）：从安静分隔到控件边界的 1px 层级。
- **Translucent Paper**（`surface-card-translucent` / `surface-ivory-translucent`）：状态面板和次级操作的轻透纸面。
- **Ink-Surface Copy**（`text-on-dark-secondary` / `text-on-dark-muted`）：深墨段落上的次级与弱化文字。

**The Paper-and-Ink Rule.** 默认画布是暖象牙，深墨只用于需要“封面、账簿、证据”语义的段落，不把整个产品反转成暗色界面。

**The Restrained Gold Rule.** 金色只标记层级、编号、边界和证据；一个视区通常只有一个主导金色强调。Gold is an accent, not a fill for every component.

**The Terracotta Focus Rule.** 陶土色优先服务键盘焦点与错误，不用于大面积装饰或制造紧迫感。

Never introduce generic purple-blue AI gradients.

### Typography

- Display and reading headings: `Noto Serif SC Variable`, then the existing Song-style fallbacks (`typography.display` / `headline` / `title` in the frontmatter).
- UI, forms, navigation, and body copy: `Noto Sans SC Variable`, then system sans fallbacks (`typography.body`).
- Labels and archive metadata: `typography.label`.
- Use tabular numerals for dates, prices, time, order state, 编号 and chart data.
- Use the serif face for hierarchy, conclusions, and report reading—not every label.
- Avoid fake calligraphy, excessive letter spacing in Chinese, and tiny low-contrast captions.

Scale (values in the frontmatter):

| Token | Size | Weight | Line height | Tracking |
| --- | --- | --- | --- | --- |
| `display` | `clamp(3.25rem, 10.5vw, 6rem)` | 560 | 0.98 | `-0.04em` |
| `headline` | `clamp(2.45rem, 7vw, 4.8rem)` | 580 | 1.04 | `-0.04em` |
| `title` | `clamp(1.45rem, 4vw, 2.15rem)` | 600 | 1.16 | `-0.025em` |
| `body` | `1rem` | 400 | 1.65 | normal |
| `label` | `0.72rem` | 730 | 1.65 | `0.08em` |

Hierarchy:

- **Display**：只用于首页主承诺等最高层标题，当前首屏控制在约 11ch。
- **Headline**：公共页面章节标题，负责建立大段落节奏。
- **Title**：私人页面、纸张区块和阅读章节标题。
- **Body**：说明、正文和表单帮助；正文行长通常控制在 62–68ch。
- **Label**：folio、编号和档案元信息；英文可使用克制字距，中文不额外拉开。

**The Two-Voice Rule.** 衬线负责“读什么”，无衬线负责“做什么”；表单标签、按钮和导航不得改成装饰性书法字。

**The Legible Archive Rule.** 小号标签只承载短元信息；条件、边界和错误必须回到正常正文尺寸与对比度。

### Layout

- Mobile first from 360px; all purchase and reading flows must remain complete on mobile.
- 公共容器最大宽度为 74rem；默认两侧总留白为 2.25rem，48rem 以上增至 4rem。核心验收宽度为 360、768、1024 和 1440px。
- 当前实现按内容需要在 34、40、42、48、64 和 68rem 渐进增强，不把设备型号当布局依据。
- 章节垂直留白使用 `clamp(4.5rem, 9vw, 8rem)`，常规网格 gap 为 1rem。
- Public pages may use asymmetry, large type, full-bleed dark sections, and spacious scene cards. 首页先以深色扉页承诺价值，再用三张任务卡交付建档、今日/近七日和一事一问三个入口；方法、阅读结构、价格与隐私依次展开。
- Private application pages prioritize the task and result; decoration must not compete with inputs or evidence. 64rem 起出现侧栏导航，68rem 起阅读正文与证据栏并排，证据栏可 sticky；手机使用五项底部导航并预留 safe-area。
- Desktop reading pages may use navigation / main reading / evidence columns, but must collapse explicitly on mobile.
- Cards exist only when they express a real grouping or hierarchy. 能用留白、1px 分隔线或纸色变化说明关系时，不再套一层卡。Prefer whitespace, dividers, and section contrast over nested cards.

**The Task-Before-Decoration Rule.** 私人表单与阅读页先保证任务、证据和状态顺序，装饰不得挤占输入宽度或正文行长。

### Elevation & Depth

这是以色调和边界为主、阴影为辅的系统。`shadow-card` 只把白色纸张从象牙画布中轻轻抬起，`shadow-soft` 用于独立私人面板，`shadow-action` 只服务主要操作，`shadow-hero-orbit` 只服务首屏时间仪表。账簿、列表和嵌套内容默认保持平面，以纸色差、1px 规则线和深浅墨色建立纵深。

Shadow vocabulary:

- **Hero Orbit**（`shadow-hero-orbit`）：首屏时间刻度仪表的唯一环境阴影。
- **Action Lift**（`shadow-action`）：主要按钮的低幅动作反馈。
- **Soft Panel**（`shadow-soft`）：需要从私人背景中独立出来的单一面板。
- **Paper Card**（`shadow-card`）：白纸卡片、阅读正文和状态面板的轻抬升。

**The Flat-by-Default Rule.** 同层内容默认不投影；只有主行动、独立纸张或签名仪表获得阴影。

**The One-Sheet Rule.** 阅读正文是一张连续纸，不把结论、依据、边界和核对拆成四张互相竞争的浮卡。

### Shapes

形状像装订良好的现代档案：控件使用轻柔小圆角（`rounded.sm`），纸张和主要容器使用更舒展的中圆角（`rounded.md`），只有时间仪表使用大圆角（`rounded.lg`）。大多数边界为 1px；轮廓细、转角温和，避免玻璃胶囊和过度柔软的 SaaS 卡片感。

完全圆形保留给品牌印记、时间环和小状态图标；999px 胶囊只用于短状态标签。任务卡上的圆与斜线是档案测量记号，不是可随意复制的背景纹样。

**The Light-Corner Rule.** 圆角负责保护触控与纸张感，不负责把每个区块变成药丸或气泡。

**The Fine-Boundary Rule.** 优先使用单层 1px 边界；不要用双重描边、厚框或嵌套圆角模拟层级。

### Imagery and symbols

- Domain imagery may draw from celestial cycles, time rings, ink lines, paper, seals, trigrams, and archival notation.
- Use abstract, original compositions rather than literal dragons, temples, flames, fortune tellers, or wallpaper made from repeated bagua symbols.
- Lucide is for functional controls only. Important命理 concepts use custom, reviewed symbols or typography.
- Emoji must not be used as interface icons.

## 4. Component and library contract

- Styling owner: semantic CSS variables plus CSS Modules.
- Accessible interaction primitives: `radix-ui`.
- JavaScript motion: `motion`, imported from `motion/react`.
- Functional icons: `lucide-react`.
- Conditional class composition: `clsx`.
- Forms: `react-hook-form` plus `zod` and `@hookform/resolvers`.
- Chinese type: `@fontsource-variable/noto-sans-sc` and `@fontsource-variable/noto-serif-sc`.

Do not introduce Tailwind, shadcn runtime, MUI, Ant Design, another primitive system, GSAP, Lenis, Lottie, or a second motion library without an explicit design/architecture decision. shadcn/ui may be used as a component-structure reference, but copied components must be restyled through this system and use only one primitive owner per interaction.

## 5. Components

### Buttons

- **Shape:** 所有主要与次要按钮至少 44px 高，使用 `rounded.sm` 和紧凑水平内边距。
- **Primary:** Working Ink 底、Warm Paper 字，并使用 Action Lift；hover 切到 Active Ink，最多上移 2px，active 回到基线并轻微压缩。
- **Secondary:** 半透明象牙纸面、细边界和 Working Ink 文字；hover 只提高清晰度与金色边界。
- **Focus / Disabled:** 所有可交互变体使用 3px 陶土色 `:focus-visible` 外轮廓并留 3px offset。禁用态不位移、不伪装可点击，并在附近说明门禁原因。

### Cards / Containers

- **Task Cards:** paper、ink、clay 三种真实 tone 使用同一中圆角和大留白；标题靠下形成编辑海报感，整张卡只保留一个明确去向。
- **Paper / Reading Surfaces:** 白纸加轻阴影，只用于真实分组；连续内容依靠分隔线，不嵌套卡片。
- **Dark Rails:** 深墨侧栏承载证据和继续操作，不把重要表单放到低对比深色表面。

### Inputs / Fields

- **Style:** 可见 label、48px 最小控件高度、象牙底、1px 强调边和小圆角；textarea 允许垂直缩放。
- **Focus:** 继承全局陶土色焦点环；光标也使用陶土色。
- **Error / Disabled:** `aria-invalid` 同时触发陶土色边界与就近错误文本；禁用态必须给出原因，不能只降低透明度。
- **Choice Cards:** 选中时转为苔绿纸面并加深边界，原生 radio/checkbox 仍保留可见状态。

### Navigation

- **Public:** 品牌印记、三项主导航和账户入口保持 44px 触控高度；hover 用金色下划线，不用大色块抢夺首屏。
- **Private:** 桌面侧栏用左侧金线标记当前页；手机底栏用顶部金线和浅金底同时标记，状态不只靠颜色。

### Status, Reading, and Time

- **Status Panels:** loading、empty、error、processing、success、disabled 都有图标、标题和直白说明；付款、权益、生成和正文交付必须拆开表达。
- **State Tags:** 胶囊只显示短状态，并同时给出人能读懂的解释；处理中、成功和错误分别使用琥珀、苔绿和陶土语义。
- **Reading Anatomy:** 结论、依据、边界、现实核对按编号顺序展开，来源零命中时明确留空，不生成伪出处。
- **Time Archive:** 同心时间环、手针、中心印记与四段 ledger 组成首页签名仪表，表达“输入—事实—边界—核对”。

**The Honest-State Rule.** UI 只呈现服务端已经确认的状态；客户端回跳不等于到账，已付款不等于已交付，未接通能力必须明确标成演示、为空或暂不可用。

## 6. Motion language

Motion should suggest **time becoming legible**, not spectacle.

### Approved patterns

- Page/section entrance: opacity plus `translateY(8px–12px)`, 400–550ms, ease-out.
- Related-item stagger: 60–90ms, capped at 5 visible items.
- Button and card feedback: 160–200ms; at most 2px lift or a very small press scale.
- Result reveal: 240–360ms per meaningful block, conclusion first, then evidence and boundaries. 状态面板与阅读切换按 260ms 执行。
- Dialog and mobile sheet: spring motion with low bounce; focus behavior remains owned by Radix.
- Optional ambient time/astrolabe ring: 8–12s, transform/opacity only, non-blocking, paused off-screen. 时间仪表自身的入场/状态变化为 420–840ms，最多四项 75ms stagger。
- Color state changes may reuse the existing 160–200ms transition.

### Forbidden patterns

- scroll hijacking, mandatory parallax, cursor followers, autoplay sound, or motion that delays reading;
- continuous blur, glow, gradient, or large-image animation;
- bouncing payment, privacy, destructive, or error controls;
- animating width, height, top, left, margin, or padding when transform/opacity can express the same change;
- adding animation to every section merely because the library is available.

**The Motion-Is-Legibility Rule.** 入场和位移动效只改变 `transform` 与 `opacity`。Every non-essential animation must honor `prefers-reduced-motion`; with reduced motion enabled, content appears immediately, animation and non-essential transitions stop, and no information may be lost.

## 7. Accessibility and trust floor

- Interactive targets are at least 44×44px.
- Body text contrast targets WCAG AA; focus indicators remain clearly visible (3px terracotta outline with 3px offset on interactive controls).
- Do not communicate certainty, payment state, error state, or verification state using color alone.
- Forms always have visible labels, nearby helper/error text, and keyboard-complete interaction.
- Dialogs, popovers, select controls, and tabs use tested primitives rather than hand-built focus management.
- Loading, empty, error, pending-payment, generation, disabled, and reduced-motion states are part of the component definition; disabled controls always state the reason.
- UI 只呈现服务端已经确认的状态；不伪造结果、古籍来源、成功付款、运营主体、评价、销量、备案号或支持渠道。

## 8. Do's and Don'ts

### Do:

- **Do** 让深墨封面、暖象牙纸张、细金线和少量陶土焦点形成清晰材料层级。
- **Do** 在登录前讲清确定性核心、依据、边界与三个 P0 任务，并保留两项首屏行动和三项可信事实。
- **Do** 让每个交互目标至少 44×44px，并为键盘焦点、标签、帮助和错误提供可见文本。
- **Do** 用 `transform` / `opacity` 表达位移与入场，并完整支持 `prefers-reduced-motion`。
- **Do** 把支付、权益、生成、校验与正文交付拆成诚实、可核对的状态。

### Don't:

- **Don't** 把首页改成聊天框、提示词输入框或一组尚未开放的十三体系入口。
- **Don't** 把深墨段落误写成全站暗色模式，也不要引入通用紫蓝 AI 渐变、霓虹发光或大面积金色填充。
- **Don't** 使用假书法、emoji 图标、龙庙火焰、算命摊意象或重复八卦壁纸制造“东方感”。
- **Don't** 用嵌套卡片、厚边框或夸张阴影代替留白、纸色差和细分隔线。
- **Don't** 只靠颜色表达错误、确定性、付款、验证或交付状态。
- **Don't** 伪造结果、古籍来源、成功付款、运营主体、评价、销量、备案号或支持渠道。

## 9. Required design workflow

1. Read this file and the relevant product contract before changing UI.
2. For a new surface or major redesign, invoke `ui-ux-pro-max`, then use `impeccable` to shape or critique the direction.
3. Implement with the existing tokens and approved component owners.
4. For any motion work, invoke `fixing-motion-performance` before considering the work complete.
5. Before handoff, invoke `web-design-guidelines` and `fixing-accessibility`; use `impeccable` for the final audit/polish pass on major surfaces.
6. Verify at 360, 768, 1024, and 1440px, including reduced motion and keyboard navigation.

Change tokens and shared primitives before adding page-local exceptions. If a new visual rule cannot be expressed through this contract, update this document deliberately instead of silently creating a second design system.
