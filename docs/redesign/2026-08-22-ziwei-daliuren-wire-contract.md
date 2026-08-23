---
name: 紫微 / 大六壬 runtime-chart 接线合同
date: 2026-08-22
task: WUSHU-WIRE-CONTRACT
status: ready-for-frontend-after-authorization
role: 只读接线合同；本文件不授权改产品代码
authority: 对照 web/src/components/readings/runtime-chart.tsx 六爻/梅花挂载；字段形状以 web/src/view-models/registry.ts 为准；逐屏规格见 2026-08-21-ziwei-flow-spec.md / 2026-08-21-daliuren-flow-spec.md
---

# 紫微 / 大六壬 runtime-chart 接线合同

本轮尚未授权改实现。授权后 Owner = `front-develop`，一次一把刀，先紫微后大六壬。

真实接线点是 `web/src/components/readings/runtime-chart.tsx`（不是 `web/src/components/task/`）。提交后的用户路径已经是：

```text
/ziwei 或 /daliuren 提交
  → product-task-experience router.push(`/app/readings/${id}`)
  → 重定向 /account/history/:id
  → ReadingResult
  → RuntimeChart(viewModel)
```

`ReadingResult` 已经按 schema 把 `ziwei-chart/v1`、`daliuren-chart/v1` 交给 `RuntimeChart`。缺的不是新挂载点，是把 `RuntimeChart` 里的旧表渲染换成已隔离的纸墨盘。

对照范本：

| 术 | RuntimeChart 现状 | 范本 |
|---|---|---|
| 六爻 | `case "liuyao-chart/v1"` → `LiuyaoChart` → `<LiuyaoLineTower view offer s4Phase reportClaims />` 外加遗留结构表 | 杂交；本刀不要学遗留表 |
| 梅花 | `case "meihua-chart/v1"` → `MeihuaChart` → 只返回 `<MeihuaS3Board view showInterpretiveSections reportClaims />` | **本刀照这个清挂** |
| 八字 | 不进 RuntimeChart；`reading-result.tsx` 约 L1212 直接挂 `BaziChart` | **不要学** |
| 紫微 | `case "ziwei-chart/v1"` → 本地 `ZiweiChart` 旧表（十二宫与主星 / 本命四化事实 / …） | 换成 `ZiweiPalaceBoard` |
| 大六壬 | `case "daliuren-chart/v1"` → 本地 `DaliurenChart` 旧表（四课 / 三传 / 有界应期候选） | 换成 `DaliurenBoard` |

`product-task-experience.tsx` **不要动**。紫微/大六壬提交已经 `router.push`；梅花才留页挂 `ReadingResult`。S0 剪影组件已存在但未挂录入页，本刀不做 S0。

---

## 1. 紫微接线

### 改哪些文件

只改：

- `web/src/components/readings/runtime-chart.tsx`
- `web/src/test/runtime-chart.test.tsx`
- `web/src/test/runtime-capability-gate.test.tsx`
- `web/src/test/ziwei-qizheng-result-shell.test.tsx`（只改会被旧表 caption 绊倒的断言，不改 ReadingResult 壳）

### import 哪几个组件

在 `runtime-chart.tsx` 增加且只增加：

```ts
import { ZiweiPalaceBoard } from "./ziwei-palace-board";
```

禁止再 import：`ziwei-caliber-bar`、`ziwei-transformation-table`、`ziwei-major-limit-track`、`ziwei-star-fact-list`、`ziwei-source-pattern-drawer`、`ziwei-free-summary`。这些已经挂在 `ZiweiPalaceBoard` 内部。隔离测断言 `runtime-chart.tsx` 源码不含这些文件名；直接 import 会红。

保留本地包装名 `function ZiweiChart`。`ziwei-qizheng-result-shell.test.tsx` 用

`natal.slice(indexOf("function ZiweiChart"), indexOf("function LiuyaoChart"))`

做源码切片，改名会红。

### props 从哪来

`export function RuntimeChart` 的 `switch` 已有：

```ts
case "ziwei-chart/v1":
  return <ZiweiChart view={viewModel} showInterpretiveSections={showInterpretiveSections} />;
```

改成梅花清挂：

```ts
function ZiweiChart({ view }: Readonly<{ view: ZiweiChartViewModel }>) {
  return <ZiweiPalaceBoard view={view} />;
}

case "ziwei-chart/v1":
  return <ZiweiChart view={viewModel} />;
```

| 符号 | 来源 | 规则 |
|---|---|---|
| `view` | `RuntimeChart` 入参 `viewModel`，且 `schema_version === "ziwei-chart/v1"` | 必传 |
| `mode` | 不传 | 默认 `"ready"` |
| `layout` | 不传 | 默认 `"ring"`；360 列表是盘面内建，不在接线层切 |
| `offer` | 不传 | 默认 `null` → M8「测试期未开放」 |
| `s4Phase` | 不传 | 默认 `"entry"` |
| `showInterpretiveSections` | **丢掉** | 旧表用它藏「古籍来源条件候选」；纸墨 M7 是 S3 事实抽屉，B 档也要上。断语门禁仍在 `ReadingResult`（capability C 不上盘） |

不要给 `RuntimeChart` 新加紫微 `offer` / `s4Phase` 字段。`reading-result.tsx` 现在只传 `viewModel` + `capability`（紫微约 L1113）。本刀不改 `reading-result.tsx`。

`ZiweiPalaceBoard` 已含：M1 `ZiweiCaliberBar`（只读 `core_facts.chinese_date`）、M2 环盘、M3 中宫、M4 四化、M5 大限轨、M6 星曜明细、M7 古法命中、M8 免费摘要+深读。接线层不要再铺一层旧表。

### 缺 VM 怎么 fail-closed

接线层不造盘、不读 fixture、不把 `VIEW_MODEL_FIXTURES["ziwei-chart/v1"]` 填进页面。

| 层 | 符号 | 已有行为 | 本刀 |
|---|---|---|---|
| `ReadingResult` | `natalViewReady`（约 L1068–L1074） | `capabilityTier === "C"` → Status unavailable；`view_model == null` 或 schema 不是 `ziwei-chart/v1` → Status empty「还没有可展示的盘面」 | 不动 |
| `RuntimeChart` | `default: return null`（约 L1575） | 未识别 schema 不渲染 | 不动 |
| `ZiweiPalaceBoard` | `view?` + 各 M* 缺字段整块不渲染 | `core_facts` null 仍可用 `palaces/life_palace_id/body_palace_id`；M1/M4–M8 各自 fail-closed | 不改盘面 |

禁止在 `ZiweiChart` 里对缺字段补「—」行。旧 `displayValue` / 旧表那套不要留下来。

---

## 2. 大六壬接线

### 改哪些文件

紫微刀合入后再改（同一文件，禁止并行）：

- `web/src/components/readings/runtime-chart.tsx`
- `web/src/test/runtime-chart.test.tsx`
- `web/src/test/qimen-daliuren-result-shell.test.tsx`（只改旧表 caption 断言）

### import 哪几个组件

```ts
import { DaliurenBoard } from "./daliuren-board";
```

禁止再 import：`daliuren-caliber-bar`、`daliuren-heaven-earth-plate`、`daliuren-lesson-method`、`daliuren-dimension-evidence`、`daliuren-free-summary`。隔离测断言 runtime 源码不含这些文件名。

保留本地包装名 `function DaliurenChart`。`qimen-daliuren-result-shell.test.tsx` 用

`indexOf("function DaliurenChart")` … `indexOf("function PhysiognomyChart")`

切片。

### props 从哪来

现有：

```ts
case "daliuren-chart/v1":
  return <DaliurenChart view={viewModel} />;
```

改成：

```ts
function DaliurenChart({ view }: Readonly<{ view: DaliurenChartViewModel }>) {
  return <DaliurenBoard view={view} />;
}
```

| 符号 | 来源 | 规则 |
|---|---|---|
| `view` | `viewModel` 且 `schema_version === "daliuren-chart/v1"` | 必传 |
| `mode` | 不传 | 默认 `"ready"` |
| `offer` / `s4Phase` | 不传 | 默认无 Offer → M7「测试期未开放」 |

`DaliurenBoard` 已含：M1 `DaliurenCaliberBar`（`question` 原样；松散项只读允许键）、课传（必有 `lessons`/`transmissions`）、M4 天地盘、M5 课式与传法、M6a 维度证据、M6b 应期候选、M7 免费摘要+深读。不要保留旧「四课」「三传」「大六壬结构事实」「有界应期候选」表。不要再 import `daliuren-caliber-bar`。

`reading-result.tsx` 大六壬壳约 L936–L993 已经 `typedReady` 后挂 `RuntimeChart`。本刀不改该文件。

### 缺 VM 怎么 fail-closed

| 层 | 符号 | 已有行为 | 本刀 |
|---|---|---|---|
| `ReadingResult` | `typedReady`（约 L941–L947） | C 档 unavailable；无 `daliuren-chart/v1` → empty「还没有可展示的盘面」 | 不动 |
| `RuntimeChart` | `default: return null` | 未识别 schema 不渲染 | 不动 |
| `DaliurenBoard` | `view?`；`core_facts` null 时课传仍可读，M4–M7 不上 | 已实现 | 不改盘面 |

---

## 3. 测试要补哪几个文件 / 用例名

### 必须改断言（旧表 caption 会红）

| 文件 | 现用例名 | 改什么 |
|---|---|---|
| `web/src/test/runtime-chart.test.tsx` | `renders Runtime Ziwei core facts without adding browser-side judgments` | 去掉「本命四化事实」「TR-01 · 至玄至微」「不在浏览器追加判断」。改断言纸墨：命宫主星「紫微」、中宫「水二局」、`getByRole("region", { name: "四化" })` 见「廉贞」。无吉凶词。 |
| `web/src/test/runtime-chart.test.tsx` | `renders a bounded Daliuren timing candidate as a non-guaranteed date` | 去掉「有界应期候选」「丁卯 · 酉」「LM-R21 · san-shi/liuren-miben」「候选日期，不是现实保证」。改断言 `getByRole("region", { name: "课传" })`、初传「酉」/「朱雀」、应期区「2026-08-21」与板上原句「以下为古籍规则产生的候选日期，不是保证的应期」。 |
| `web/src/test/runtime-capability-gate.test.tsx` | `keeps B-tier facts and removes interpretive candidate blocks` | 不再找 `table` name「十二宫与主星」/「古籍来源条件候选」。B 档仍渲染 `ZiweiPalaceBoard`。夹具 `palaces: []` 时环盘可空，但不得出现断语。M7 有合法 `source_conditioned_patterns` 时允许上抽屉，这不是旧表。 |
| `web/src/test/ziwei-qizheng-result-shell.test.tsx` | `puts ziwei chart facts and a verified citation before notes, without construction copy` | 「紫微命盘」「水二局」应仍在。不要新找旧表 caption。源码切片仍要求存在 `function ZiweiChart`。 |
| `web/src/test/qimen-daliuren-result-shell.test.tsx` | `puts daliuren lessons first and does not invent a plate` | 旧断言 `getByText("四课")` / `getByText("三传")` 来自 Table caption，纸墨盘没有这两词。改成 `getByRole("region", { name: "课传" })` + 「朱雀」。源码切片仍要求存在 `function DaliurenChart`。 |

### 建议新增（挂在 runtime-chart.test.tsx，不要新开隔离测文件）

- `renders ZiweiPalaceBoard for ziwei-chart/v1 and fail-closes missing core_facts modules`
  - 有 `palaces` 无 `core_facts`：环盘/命身在，无口径条、无四化区、无「测试期未开放」以外的深读 SKU。
- `renders DaliurenBoard for daliuren-chart/v1 and fail-closes missing timing_candidates`
  - 有课传、`timing_candidates: null`：课传在，无应期表。

### 回归命令（授权后前端跑）

```text
cd web && npm test -- --run \
  src/test/runtime-chart.test.tsx \
  src/test/runtime-capability-gate.test.tsx \
  src/test/ziwei-qizheng-result-shell.test.tsx \
  src/test/qimen-daliuren-result-shell.test.tsx \
  src/test/ziwei-s3-palace-board.test.tsx \
  src/test/ziwei-entry-empty.test.tsx \
  src/test/daliuren-s3-board.test.tsx \
  src/test/daliuren-entry-empty.test.tsx
```

隔离测里「keeps * off shared pages」必须继续绿：runtime 只允许出现 `ziwei-palace-board` / `daliuren-board` 这两个新文件名。

---

## 4. 明确不要动的文件

- `web/src/components/task/product-task-experience.tsx`
- `web/src/components/readings/reading-result.tsx`
- `web/src/components/readings/bazi-chart.tsx` 以及任何八字深读文件
- `web/src/view-models/registry.ts`
- `web/src/components/workbench/workbench-shell.tsx`
- `web/src/products/product-board-placeholder.tsx`
- `DESIGN.md`、`docs/CHECKLIST.md`、两份 2026-08-21 flow-spec
- 七政 / 奇门一切实现与测试（`QizhengChart`、`QimenChart`、对应测）
- 紫微/大六壬隔离盘及其子模块（M1 已在盘内，不要返工、不要在接线层重写口径条）
- S0：`ziwei-entry-silhouette.tsx`、`daliuren-entry-silhouette.tsx` 本刀不挂录入页
- 不 commit / push；不更新 18080；不碰 P4-007

---

## 5. 推荐顺序

先紫微，再大六壬。同一文件 `runtime-chart.tsx`，禁止并行。

理由：紫微是本命结果页上信息密度最高的旧表，换掉立刻变成纸墨环盘；大六壬课传旧表同样挂着，但放第二刀避免同改 `runtime-chart.tsx`。

前置：`ZW-S3-M1` 与 `DL-S3-M1` 均已 QA_PASS。接线本身不改盘面文件。

---

## 6. 风险

| 项 | 会不会碰到 | 怎么处理 |
|---|---|---|
| P4-007 | 不碰到 | 仍 BLOCKED。本合同不代填、不拿它挡接线。 |
| 18080 | 不碰到 | 本刀只改仓库测试。QA_PASS 后若进 Release Batch，另走集成岗；接线实现本身不过 18080。 |
| `reading-result.tsx` | **会间接碰到，但不改文件** | 紫微约 L1113、大六壬约 L993 已经渲染 `RuntimeChart`。换盘后 `/account/history/:id` 从旧表变成纸墨盘，并出现 M8「测试期未开放」（与已接线八字 M13 同一现象）。不要为此改 ReadingResult，不要发明 Offer。 |
| 隔离测「off shared pages」 | 会红，若误 import 子模块 | 只 import 两个 Board。 |
| 结果壳测「四课」「三传」「十二宫与主星」 | 会红 | 按第 3 节改断言，不要为了保旧 caption 留下旧表。 |
| WorkbenchShell 占位盘 | 不修 | 成功提交已离开 `/ziwei` `/daliuren`。占位「待接入」是死路径，本刀不碰。 |

授权后下一 Owner：`front-develop`。验收 Owner：`dev-ops`。不要开子代理，不要自己接线。
