---
name: 梅花 UT 返工交接（游客盘面 + S3 文案）
date: 2026-08-22
task: T-0821-UIUX-9
status: ui-ux-handoff
authority: 承接 T-0821-UT-1 UI_REWORK；纸墨语言见 DESIGN.md；逐屏合同以 docs/redesign/2026-08-21-meihua-flow-spec.md 为本，本文只补游客旅程与文案映射
evidence: docs/releases/evidence/2026-08-22-ut-meihua-bazi-timelayer/
not-in-scope: 八字时间层 chips（已达标）；互卦 null 空位（本轮未测到，规格保留「null 不占位」）；不写产品代码
---

# 梅花 UT 返工 · 前端可照做交接

复测入口 `http://106.14.10.235:18080`。八字时间层不要重开。本单只修梅花两处。

## 证据成立（已复核）

| 问题 | 证据 | 规格/纸墨对照 |
|---|---|---|
| 游客起卦被登录墙吃掉 | `1440/00-meihua-guest-login-wall.png`：`/meihua` 点「立即起卦」后落到 `/account/history/:id`，标题「历史详情」，墙文「需要登录 / 登录后才能查看历史。」盘面 0。 | DESIGN §7.1：游客能完成免费输入和盘面；登录只为保存/跨设备/深读。规格：S3 是 `/meihua` 上的状态，不是账户历史。 |
| S3 露出内部键与半成品英文 | `1440/13-meihua-s3-waited.png`、`1440/meihua-waited-text.txt` | DESIGN §7.2 / §17：用户可见区域禁止 snake_case、内部 ref、调试句。规格 M4/M5：状态句必须人话，未知键不得原值上屏。 |

`00-bazi-guest-processing.png` 对照：八字游客提交后留在 `/bazi` 看盘。梅花必须对齐这条路径，不要发明新壳。

---

## 1. 游客旅程（先看见盘，再谈登录）

### 目标

游客填完时间起卦、点「立即起卦」后，**第一眼是 S3 三卦盘面**。登录只在要保存、打开历史、深读/购买时出现。

### 现行错误路径（预览）

```text
游客 /meihua 提交
  → POST /api/v1/readings/meihua 201（游客会话已能起卦）
  → router.push /app/readings/:id
  → 重定向 /account/history/:id
  → AccountHistorySurface 见 signedOut → 登录墙
  → 盘面从未渲染
```

### 规定路径

```text
游客 /meihua S1 提交
  → 同路由切到 S3（loading：三卦骨架，不跳走）
  → 盘面 ready：本/互/变 + 体用 + 可核验起卦 + 旺衰 + 古籍极性
  → 工作条「更多」里有安静入口「登录后可保存这次起卦」（不挡盘）
  → 点保存 / 历史 / 深读 才出登录
  → 登录成功原地接管当前 reading_id，不重填、不起第二次卦
```

**不要做：** 游客提交后进 `/account/history/:id`。那条路由的登录墙对「浏览我的历史」仍然正确，不要拆掉列表墙去凑游客盘面。

### 布局与组件

- **主路径**：`/meihua` 同一路由状态机（已写在梅花规格 S0–S3）。提交后 `stage=workbench`，在本页挂结果，对齐八字 `setBaziPreviewReadingId` + 留在 `/bazi`。
- **结果组件**：复用现有 `ReadingResult readingId=…` 或等价盘面，不要新做游客专用盘。
- **工作条**：返回（回 S1，表单保留）/ 问题摘要 / 更多。游客「更多」可见项：登录以保存、导出（若能力允许）、说明。不可见：完整历史列表。
- **登录形态**：Radix Dialog/Drawer，纸面、墨钮。标题「保存这次起卦需要登录」。说明「盘面已经排出，登录只为写入你的历史，不会重新起卦。」主钮「前往登录」，次钮「先看盘」（关层，盘仍在）。
- **账户历史**：`/account/history` 列表、未持有的详情继续 `signedOut` 墙。不要为了游客把整段账户壳改成公开。

### 状态

| 状态 | 游客看见什么 |
|---|---|
| S1 填写 | 现有入口，可提交 |
| 提交中 | 留在 `/meihua`；三卦骨架 + 「正在起卦」；URL 不换成历史 |
| S3 ready | 满血盘面；判断区按 §3 |
| 盘面 error | 诚实失败，可改时间再起；不进登录墙 |
| 点保存/历史/深读 | 登录层；取消后盘仍在 |
| 登录成功 | 仍在这张盘；「更多」出现保存完成/已写入历史 |
| 直接打开 `/account/history` | 登录墙（正确） |

### 响应式

1440 / 768 / 360 都留在 `/meihua`。登录层：≥768 居中纸卡；360 底部抽屉，主钮 48px。不要把登录做成整页替换把盘卸掉。

### 可访问性

- 提交后焦点落到盘面标题或三卦区域，不落到账户导航「推演历史」。
- 登录层 `role="dialog"`，Esc 关闭回到盘。
- 骨架 `aria-busy="true"`；ready 后去掉。

### 验收

1. 无痕窗口打开 `/meihua` → 时间起卦 →「立即起卦」→ URL 仍是 `/meihua`（或仅 query `reading=`，**不是** `/account/history/…`）。
2. 未登录也能看见本卦/互卦/变卦（本轮样本有互卦）。
3. 顶栏仍是「游客 登录或注册」，没有「需要登录才能看历史」整页墙。
4. 点「登录以保存」才出登录；关层后盘还在。
5. 八字游客路径不被这次改动破坏。

### 给前端的文件

| 文件 | 做什么 |
|---|---|
| `web/src/components/task/product-task-experience.tsx` | 梅花分支对齐八字：收下 `reading_version_id`，`setStage("workbench")`，**禁止** `router.push(/app/readings/…)` |
| `web/src/app/meihua/page.tsx`（若只转发表单） | 允许本页挂 `ReadingResult` |
| `web/src/app/app/readings/[readingId]/page.tsx` | 保持重定向到历史；游客根本不该被送到这里 |
| `web/src/components/surfaces/account-history-surface.tsx` | 列表墙保留。不要把详情墙拆掉当游客盘面容器 |
| 测试 | 补游客提交仍停在 `/meihua` 的断言；现有历史页「需要登录」测试继续绿 |

---

## 2. S3 文案映射（内部键 → 中文或隐藏）

### 目标

用户看见的全是中文、能懂的术词。没有的判断用诚实空态。内部 enum、英文键、半成品英文句一律不上屏。旺衰同一事实只出现一次。

### 现行错误（登录后等待盘，`meihua-waited-text.txt`）

- 判断：「服务端尚未返回已接纳正文。」
- 旺衰表「状态句」列多行重复 `calculated_strength_not_verdict`（坎体出现三次、坤用出现三次）
- 月令夹英文季节：`申月 · autumn`
- 古籍极性标题下直接写 `facts_only`
- 模块尾英文：`body/use relation polarity is source-adjudicated; multiple relations, seasonal strength and question scope still require synthesis before 吉凶、成败、应期 or any final conclusion`

根因在渲染，不在缺盘：`meihua-chart.tsx` 对未登记的 `status` **回退成原字符串**；`candidates.boundary` 原文透传；`ReadingResult` 的「判断」在 `accepted_copy == null` 时走 `AcceptedCopy` 工程空句。规格旧句「状态句行内透传 / boundary 原样透传」被实现成了把内部键倒给用户——本单作废这条透传。

### 映射表（照表实现，禁止 else 回退原值）

未列入、或看起来像 `snake_case` / 拉丁长句 / `body/use` 技术句 → **整段不渲染**。不要猜译成长文。

#### A. 体用 `body_use.status`

| 内部值 | 上屏 | 位置 |
|---|---|---|
| `calculated_relation_not_verdict` | 已计算的五行关系，不是吉凶 | 体用卡一句说明，关系大字下面 |
| 未知 | 隐藏该句，保留「体／用／关系」 |

#### B. 旺衰 `seasonal_strength.*.status` 与季节

| 内部值 | 上屏 |
|---|---|
| `calculated_strength_not_verdict`（预览文本；实现时对 `calculated_strength_not_verdict` 等同处理） | **不上行内**。模块题下只放一次：「月令旺衰是按时令算出的事实，不是吉凶。」 |
| `calculated` | 同上，不写「已计算」这种工序词 |
| `spring` / `summer` / `autumn` / `winter` | 春 / 夏 / 秋 / 冬 |
| 已是「春夏秋冬」 | 原样 |
| `旺` `相` `休` `囚` `死` 或 `平` `衰` | 原样，中性墨色，不染色 |

旺衰表列只留：**卦**（体/用标注）｜**月令**（`申月 · 秋`）｜**状态**（平/衰/旺…）。删除「状态句」列。

**去重**：按 `trigram + 体用角色 + month_branch + state` 各一行。同一卦同一月同一状态只留一行。题注那句全表只出现一次，禁止跟进每行。

#### C. 古籍极性 `interpretation_status` / 候选 `status` / `boundary`

| 内部值 | 上屏 |
|---|---|
| `facts_only` | **不写进标题**。模块名保持「古籍极性」。可选一句淡墨：「下面是古籍已经裁定的关系，不是断这件事成不成。」 |
| `source_adjudicated_relations` | 古籍已裁定关系极性 |
| `source_adjudicated_relation_polarity` / `relation_polarity_adjudicated` | 关系极性已裁定（chip 内，每条一次即可） |
| 极性 enum `supportive` 等 | 沿用规格：生扶体 / 泄耗体 / 克制体 / 体所生克 / 比和 |
| `candidates.boundary` 含英文、`body/use`、`source-adjudicated`、snake_case | **丢弃**，改用固定中文页脚 |
| `candidates.boundary` 已是通顺中文且不与页脚重复 | 可显示一次 |

**固定页脚（必有，中文一次）：**

> 以上是古籍已裁定的关系极性。这件事成不成、吉凶、应期，本页不断。

禁止再追加英文同义句。规则号（如 `MR-04-02`）只做金线证据徽章，点开看出处；不要当段落标题堆在正文流里。

#### D. 判断区（Reading 壳，不是卦图组件）

`accepted_copy` 对梅花 S3 经常是 null。这不是事故，不要用服务端工序句。

| 数据 | 判断区 |
|---|---|
| `accepted_copy` 有中文 | 原样呈现（G1） |
| `accepted_copy == null` 且盘面已有 | **不要**「服务端尚未返回已接纳正文。」改用空态（见下） |
| 状态仍是 generating/completing | 「正文还在生成。三卦盘面可以先看。」盘面照常 |
| 能力档 B 且无正文 | 现有「当前只提供确定性盘面与事实，不提供断语。」可保留，与空态不要两句叠在一起 |

**判断空态（必用这三行，不要改成工程腔）：**

- 标题：判断
- 正文：这一问还没有可发布的判断。上面的盘面和关系事实可以先看。
- 辅助：不是加载失败。吉凶成败本来就不在这一页。

视觉：纸面淡墨一段，不是错误 Status、不是红色、不是空卡片大插画。有盘时判断区让路——**盘面在前、判断在后**（现状 01 判断空壳压在盘面上，半成品感来自这里）。

### 旺衰不要同义重复

禁止同时出现：

1. 表里每行 `calculated_strength_not_verdict`
2. 题注「已计算的五行关系…」
3. 基础摘要再念一遍「坎平、坎平、艮平、震衰、坤平、坎平、坤平、坤平」

摘要只复述**去重后**的卦名与状态各一次，例如：「本卦地水师，互卦地雷复，变卦山水蒙；动爻上爻；体坎水、用坤土，用克体；坎平，坤平，艮平，震衰。」

### 互卦 null

本轮未测到。继续：`mutual_hexagram == null` 整列不渲染、不占空框、不写「互卦暂缺」。三列自动收成两列。

### 状态 / 响应式 / 无障碍

- 未知键：不渲染该原子，整块仍可因其他字段存在。
- 英文 boundary 被丢弃后，页脚中文仍在，模块不空死。
- 360：表三列可换「卦 + 状态」主行、月令第二行；不要为了塞「状态句」横滚。
- 旺衰表是 `<table>`，caption「月令旺衰事实」。空态判断是普通段落，不要 `role="alert"`。

### 验收（对照同一份 waited 文本）

页面可见文本 **不得出现**：

- `calculated_strength_not_verdict` / `calculated_strength_not_verdict`
- `facts_only` / `facts_only`
- `body/use`
- `source-adjudicated`
- `autumn` / `spring` / `summer` / `winter`（应用中文季节）
- 「服务端尚未返回已接纳正文」
- 同一体用卦在旺衰表出现两次以上（同月同状态）

必须出现：

- 中文三卦名与体用关系
- 旺衰题注一句中文（全模块一次）
- 判断空态三句之一套（无正文时）
- 极性页脚中文一句

### 给前端的文件

| 文件 | 做什么 |
|---|---|
| `web/src/components/readings/meihua-chart.tsx` | 映射表收口；未知 status **禁止** `return status`；旺衰去重；删状态句列；季节英→中；英文 boundary 丢弃 |
| `web/src/components/readings/meihua-chart.module.css` | 只调映射后的密度（题注一行、表三列）；不换肤 |
| 新建 `web/src/components/readings/meihua-copy.ts`（推荐） | 把 A–D 表做成唯一 copy 源，组件与测试共用 |
| `web/src/components/readings/accepted-copy.tsx` | 默认空句不要再用工序腔。允许传入 `emptyText`；梅花传入 §D 空态 |
| `web/src/components/readings/reading-result.tsx` | 梅花：判断区在盘面后；`accepted_copy == null` 用梅花空态，不挡第一眼三卦 |
| `web/src/test/meihua-s3-triad.test.tsx` 等 | 断言内部键不上屏、去重、中文空态、英文 boundary 不可见 |

不要改八字 chart、不要改 tokens、不要改账户历史列表墙。

---

## 3. 明确不改

- 八字时间层 chips 行为与文案
- 纸墨 token、字体、印章
- 互卦 null 的占位策略（保持不占位）
- 为游客开放整个 `/account/history` 列表
