# 八字结果页开发规格 — 2026-08-17

状态：**历史决策留档；有效规则已并入 `DESIGN.md`，本文不再是有效合同。**

> 2026-08-18 收口：本文保留 2026-08-17 的需求形成过程，不再描述当前实现状态，也不得作为施工入口。页面结构、红线与验收门只读 `../../DESIGN.md`；字段只读版本化 Presentation Contract；范围和进度只读 `../CHECKLIST.md`。下文“只改前端”“后端输出已完整”及规则数量等均是当时快照，已经被后续 G1/G3 纵链开发取代。

上位合同：`../../DESIGN.md`（**冲突时以它为准**）、`./2026-08-14-direction-c-decision.md`、ADR 0011。

本文曾是字段级实施草案。三条红线的权威表述已在 2026-08-17 并入 DESIGN.md：
禁令见 §17，证据层呈现规格见 §19，能力分层见 §20，交互质量见 §21，差异化验收六道门见 §22。
本文 §3 与 DESIGN.md §17/§19 若有措辞差异，以 DESIGN.md 为准。
数据契约来源：`backend/app/charts/contracts.py` 的 `BaziCoreFacts` 及其子模型（已核实，无需新增后端输出）。

---

## 0. 为什么做这个

P0 正式上线以八字完整闭环为唯一主线，P0 商品是「八字深度解读 ¥29.90」。八字是全部入口里
唯一同时满足两个条件的：

- **唯一有已核验古法断法依据的主入口** —《穷通宝鉴》18 条已核验调候规则；紫微、六爻、七政
  当前各 0 条。
- **唯一有「候选链」的主入口** — `interpretive_candidates` 提供强弱证据、结构候选、从格/合化
  候选、推理工具，是事实与断语之间的中间层。其余入口只有盘面事实。

竞品的结果页信息密度和可视化明显更强，但它们的「格局/用神/评分」建立在无来源的自研权重上，
引用的古籍出处经核验存在虚假（详见 §3 的红线说明）。本页的目标不是复制它们的结论层，
而是把**我方已有的事实与候选**做成同等密度、同等可读性的呈现。

---

## 1. 任务边界

### 只改前端

```
web/src/components/readings/bazi-chart.tsx           主要改动对象（现 436 行）
web/src/components/readings/bazi-chart.module.css    配套样式
web/src/components/readings/<新增子组件>              按需拆分
web/src/components/readings/*.test.*                 新增/更新测试
```

### 不要碰

| 路径 | 原因 |
|---|---|
| `backend/**` | 数据契约已完整，本任务零后端改动。若你认为缺字段，停下来在交付说明里提出，不要自行加 |
| `core/mingli-master/**` | 算法源码树，且当前缺少签名清单与 Git 历史（见 §8 已知问题），任何改动都不可追溯 |
| `contracts/schemas/**` | 输出合同冻结 |
| `ui/tokens.css`、`ui/base.css` | ADR 0011：`ui/` 只放样式基元。可以**读取**并使用其 token，不要为本页新增或改名 token |
| `web/src/view-models/registry.ts` | 类型来源，只读 |

### 视觉语言

服从 **Direction C · 现代 SaaS 锐感**：浅灰 `#fafafa` 底、纯白面、单蓝 `#2563eb` 点缀、
8px 圆角、紧字距、细线分层。

**首页的「动态水墨 + 液态玻璃」是首页专属例外，不适用于本页。**结果页需要的是信息密度和
长时间阅读的舒适度，玻璃拟态与常驻装饰动画在此页禁止。

技术栈沿用现状：CSS Modules + Lucide 图标 + `motion/react`。不引入 Tailwind、GSAP、
Phosphor。滚动行为走既有 `RouteScrollPolicy`，不要自建滚动容器。

---

## 2. 数据来源

全部数据来自 `BaziCoreFacts`（`web/src/view-models/registry.ts` 导出类型，后端
`backend/app/charts/contracts.py` 定义）。**20 个字段已全部投影完成**，直接读，不需要
任何新增后端工作。

| 字段 | 内容 | 可空 |
|---|---|---|
| `day_master` | 日主天干、五行、阴阳 | 是 |
| `hidden_stems` | 逐柱藏干（含 `branch`、`stems`） | 是 |
| `ten_gods` | 十神 | 是 |
| `nayin` | 纳音 | 是 |
| `twelve_growth_stages` | 十二长生（逐柱） | 是 |
| `xunkong` | 旬空 | 是 |
| `san_yuan` | 胎元、命宫、身宫 | 是 |
| `month_command` | 月令 | 是 |
| `seasonal_profile` | `season` / `month_qi` / `temperature` / `moisture` | 是 |
| `tiaohou_markers` | `temperature` / `moisture` / `markers` / `day_stem` / `month_branch` / `scope` | 是 |
| `element_inventory` | 五行统计 | 是 |
| `interpretive_candidates` | 见 §4.7 | 是 |
| `source_conditioned_patterns` | 古籍规则命中，见 §4.8 | 否，默认 `()` |
| `branch_relations` | `relation_type` / `positions` / `branches` | 是 |
| `shensha_auxiliary` | 神煞 | 是 |
| `luck_cycles` | 大运，含 `status` / `direction` / `cycles` / `unavailable` | 是 |
| `calendar_normalization` | 历法归一化，含真太阳时口径 | 是 |
| `year_layers` / `month_layers` / `day_layers` | 流年/流月/流日层 | 是 |

**每个字段都可能为 `null`。**缺字段时该区块整体不渲染，不要显示「暂无数据」占位条，也不要
用零值或空字符串顶替。这是既有规约：算法暂时产不出的数据，不开放对应展示。

---

## 3. 三条红线

违反任何一条即整体打回。

### 3.1 不得合成评分或档位

`interpretive_candidates.strength` 的类型是 `BaziStrengthEvidence`，它在**类型层面**就写死了：

```
status: Literal["evidence_only"]
hard_verdict: None = None
```

它提供的是：`seasonal_state`（旺/相/休/囚/死，带 `seasonal_state_source_rule_id`）、
`same_element_occurrences`（同类出现次数）、`resource_element` + `resource_occurrences`、
`all_element_occurrences`（五行分布）、`boundary`（未裁定边界说明）。

**这些是计数和一个有来源的状态，不是分数。**

禁止：把它们加权求和成一个总分；渲染「极弱—偏弱—中和—偏强—极强」档位条；输出
「日主偏弱」这类结论标签；提供「体感不符可手动校准」之类让用户自选档位的控件。

理由：任何权重都是凭空发明的。竞品那套「得令 −16 / 得地 −19 / 综合分 −38 / 偏弱」标注
「基于《滴天髓》四层考核」，但《滴天髓阐微》全文 11493 行中既无「四层考核」这一说法，
也无任何数值系数。这是伪精确。我方的差异化正建立在不做这件事上。

**允许的呈现**：把各项证据分别列出，让读者自己看到「哪些因素支持强、哪些支持弱」，
并如实展示 `boundary` 里声明的未裁定边界。

### 3.2 不得把谓词命中写成断语

`source_conditioned_patterns` 的每一项类型为 `BaziSourcePattern`，同样在类型层面写死：

```
status: Literal["predicate_matched_not_verdict"]
```

它表达的是「这条古文的适用条件在本盘成立」，**不是**「所以结论是 X」。

文案上必须体现这个区别。可以写「此条适用」、「条件成立」；不可以写「所以你……」、
「主……」、「宜/忌……」。

### 3.3 不得虚构或改写古籍原文

原文、出处、行号锚点只能原样透传。不要润色、不要节选到改变语义、不要为了排版好看
改标点。缺原文时就不显示原文，只显示已有字段。

---

## 4. 页面结构

按此顺序，自上而下。每个区块的数据来源已列明，全部可从 `BaziCoreFacts` 直接取得。

### 4.1 命盘头

来源：`calendar_normalization`、`day_master`

- 公历时刻、农历、节气区间
- **真太阳时口径**：展示修正策略、修正量、修正后的有效时刻、边界状态
- 若 `calendar_normalization` 显示修正跨越了时辰或日界，明确标出「该修正改变了 X 柱」

设计要点：这是我方唯一能被用户直观感知的精度优势（真太阳时由天文引擎实算，而非多项式
近似）。但**大多数盘的修正不跨界**，此时它就是一条平静的信息行，不要硬做成戏剧性提示。
跨界时才升级视觉权重。

不要展示出生地原始坐标——公开 ViewModel 已做脱敏，前端也不要反推或回显。

### 4.2 四柱主卡

来源：`four_pillars`（经 `day_master`/`hidden_stems` 关联）、`ten_gods`、`hidden_stems`、`nayin`

四柱横排，每柱含天干、地支、十神、藏干、纳音。日柱标记「日主」。

### 4.3 干支关系图

来源：`branch_relations`（`relation_type` / `positions` / `branches`）

天干行与地支行，之间用连线标注关系类型。这是**纯事实**（画的是关系，不是判断），
形式上可以参考同类产品的成熟做法。

约束：`relation_type` 原样显示，不要翻译成吉凶色（例如不要把「冲」自动染成红色警示）。
用中性色区分关系类别即可。

### 4.4 盘面明细

来源：`twelve_growth_stages`、`xunkong`、`san_yuan`、`shensha_auxiliary`、`month_command`、`seasonal_profile`

- 十二长生（逐柱）
- 旬空
- 三垣：胎元 / 命宫 / 身宫
- 神煞
- 月令 + `seasonal_profile` 的 `season` / `month_qi` / `temperature` / `moisture`

**术语可以加定义型说明，不可以加吉凶型说明。**

- ✅ 「旬空：日柱所属那一旬中缺位的两个地支」
- ❌ 「旬空主虚耗」

### 4.5 五行分布

来源：`element_inventory`

五行计数的可视化。柱状或雷达皆可，读得清即可。

不要在图上叠加「缺某行 → 需补某行」这类推断——那是用神层，不在本页范围。

### 4.6 大运

来源：`luck_cycles`

注意 `status` 三态：

| status | 呈现 |
|---|---|
| `calculated` | 完整大运序列 + 起运信息（`direction`、`start_age_years`、`boundary_term`） |
| `sequence_only` | 只展示序列，明确说明起运年龄未计算 |
| `not_calculated_missing_gender` | 说明因缺性别未能计算，给出补充入口 |

`unavailable` 数组里列出的项目要如实说明未能计算，不要静默省略。

流年/流月/流日走 `year_layers` / `month_layers` / `day_layers`，同样按可空处理。

### 4.7 强弱证据（本页最需谨慎的区块）

来源：`interpretive_candidates`

`BaziInterpretiveCandidates` 含五部分：

```
strength                      BaziStrengthEvidence        强弱证据（非结论）
structure                     BaziStructureCandidate      结构候选
following_and_transformation  从格/合化候选
salience_signals              显著性信号
reasoning_tools               推理工具（dict，可空）
```

**呈现方式：证据清单，不是结论。**

`strength` 至少展示：
- `seasonal_state`（旺/相/休/囚/死）**并显示 `seasonal_state_source_rule_id`** — 这一项
  有来源规则，是本区块里唯一带古籍锚点的状态
- `same_element_occurrences`、`resource_element` + `resource_occurrences`
- `all_element_occurrences`
- `boundary` — 未裁定边界，必须显示，不能折叠隐藏

`structure` 与 `following_and_transformation` 均为**候选**，UI 文案必须带候选语义
（「候选」/「待裁定」），不得渲染成已确定的格局名。

`reasoning_tools` 是 `dict[str, BaziReasoningTool]`，键名不固定。渲染时按键遍历，
**遇到未知键保留原值原样显示，不要猜测它的含义、不要丢弃**。

再次强调 §3.1：此区块不得出现总分、档位条、强弱结论标签。

### 4.8 古籍命中（折叠抽屉）

来源：`source_conditioned_patterns`

默认折叠，收起态只显示计数，例如「命中古法 4 条 · 可核验」。

展开后每条一卡，含：

```
《来源书名》· <title>
「<原文>」                                    ← 若 ViewModel 未携带原文则省略此行
  为什么适用：<predicate_audit 的可读化>
  出处：<source_pack> <source_anchor>
```

`predicate_audit` 是形如 `/day_master/stem:eq:甲` 的审计串。可以做可读化映射
（例如「日主为甲」），但**映射表必须是显式常量，不得用模型或启发式规则猜测**；
未覆盖的审计串原样显示。

`fact_paths` 不面向普通用户，放在开发者视图或 `title` 属性里即可，不要占据正文。

设计定位：这是差异化护城河，但它对多数用户是噪音、对怀疑者才有价值。**所以是抽屉，
不是主视觉。**

---

## 5. 响应式与可访问性

- 断点验收固定 **360 / 768 / 1024 / 1440**
- 767 及以下：四柱允许两行两列；关系图允许横向滚动，但**页面级不得横向溢出**
- 768 起：完整桌面布局
- 装饰层（若有）必须 `aria-hidden="true"` 且 `pointer-events: none`
- `prefers-reduced-motion: reduce` 下所有动效静态降级，内容不得缺失或延迟
- 表格类内容用语义化 `<table>` 或带 `role` 的等价结构，不要用纯 `<div>` 拼
- 折叠抽屉必须键盘可达，展开状态用 `aria-expanded` 正确标注

---

## 6. 验收标准

### 机器可判定

```
cd web && npm test && npm run typecheck && npm run lint && npm run build
```

全绿。另需新增/更新测试断言：

1. **可空处理**：`BaziCoreFacts` 每个字段为 `null` 时对应区块不渲染，且不出现占位文案
2. **红线 3.1**：断言页面不存在总分数值、不存在档位条组件、不存在强弱结论文案
3. **红线 3.2**：断言 `source_conditioned_patterns` 渲染出的文案不含断语式措辞
4. **`luck_cycles` 三态**：三种 `status` 各有一个用例
5. **`reasoning_tools` 未知键**：断言未知键被保留展示而非丢弃
6. **真太阳时**：断言 `calendar_normalization` 的修正量与边界状态出现在页面上
7. **响应式**：四档断点无页面级横向溢出

测试固件用 `web/src/fixtures/`，不要在测试里编造超出 `BaziCoreFacts` 类型的字段。

### 需要人工验收

四档视口真实浏览器截图，用户逐屏批准。截图归档到
`web/e2e/screenshots/audit-<日期>/bazi-result/`。

---

## 7. 交付要求

每批交付附说明，逐条写：

- 改了哪些文件
- 每个区块用了哪些 `BaziCoreFacts` 字段
- 新增测试覆盖了哪条验收项
- **你认为缺失但没有自行添加的数据**（如果有）
- 未完成项及原因

不要写「应该」「预计」「大概」。测试结果必须是实际跑出来的。

---

## 8. 已知问题（与本任务不冲突，但不要试图修）

`core/mingli-master` 当前缺少 `.mingli-release-manifest.json` 与 `.git`（该目录被
某次复制操作跳过了全部隐藏文件），因此算法源码树当前不可运行、不可追溯。

这**不阻塞本任务**——本任务是纯前端，数据契约已在 `backend/app/charts/contracts.py`
完整定义，读类型即可开发，用固件测试即可验收。

但也**不要试图修它**，也不要因为跑不起来 Runtime 就改用其他数据来源或自己造数据。
该问题由算法侧单独处理。
