# Codex Goal 模式任务提示词 — 差异化六道门收口（G4/G5）+ 提交治理

> 用法：把本文件全文粘贴给 Codex，以 goal 模式（长时自动续轮）执行。目标仓库：`/Volumes/Lexar/code/mingli_web`。
> 编制日期：2026-08-18，依据是 codex 停机后对同一未提交工作树的独立门禁复核（记录见 `docs/CHECKLIST.md` 第 15 节 2026-08-18 三行）。
> 本文是**执行提示词，不是权威合同**。判据只在 `DESIGN.md` §17/§19/§20/§21/§22 与 `docs/CHECKLIST.md`；两者与本文冲突时以两者为准。

---

## 0. 动手前必读（按序，不得跳读）

1. `DESIGN.md` — 本轮判据全在 §17（明确禁止）、§19（证据层呈现）、§20（能力分层三档）、§21（交互质量）、§22（差异化六道门 G1–G6）
2. `docs/CHECKLIST.md` — 第 0 节变更纪律、第 14 节当前断点、第 15 节变更记录（尤其末尾三行）
3. `CONTEXT.md` — 统一名词，特别是「逐字核验引文」「有效排盘时刻」「分享隐私投影」
4. `docs/MINGLI_V51_WEB_INTEGRATION.md` — Runtime/Provider/模型边界
5. `docs/predicate-authoring/DEV-core-algorithm-direction.md` — 核心算法方向与 1328/192/394 规则库存事实
6. `web/AGENTS.md` — web 工作规则与 Next 16 破变化提示

## 1. 已完成，先验证不要重做

以下已由独立复核实测确认，直接在其上继续：

- **G1 逐字引文**：Core 只从全部 `verified_exact` 的古籍来源生成公开 evidence，rule assertion/摘要不再冒充原文；backend / JSON Schema / OpenAPI / TS / Web 原子闭合，冲突 legacy `excerpt` fail closed
- **G2 零合成断语**：`evidence_only` / `predicate_matched_not_verdict` / `hard_verdict=None` 在类型层写死，前后端测试双锁
- **G3 时间口径**：owner 结果页投影 `effective_datetime` / `day_boundary` / `changed_pillars` / 前后节气；Bearer 分享已收窄为 `SharedReadingDocumentV1`，不含 `view_model` / `subject_summaries` / `effective_datetime`
- **八字深读 P0 合同**：`bazi-deep-output-v1` 每 block 逐字等于所引 `fact.display_text` / `finding.public_text` / `limit.public_text`；游客被拒、checkout 只收 `reading_version_id`、confirmed payment 才 bind
- **§21.1 联动雏形**：`FactMark` / `selection` / 「聚焦详情」已在 `web/src/components/readings/bazi-chart.tsx` 落地

实测门禁基线（复核当时）：Backend `1054 passed / 131 skipped`、Web `78 files / 491 passed`、Admin `33 files / 123 passed`、两端 ESLint 与 tsc、两端 production build、`git diff --check` 全通过。

---

## 阶段 A · 收尾与提交治理（最高优先级，必须先做完再进 B）

### A1 修掉当前红的两处

```bash
uv run --project backend ruff check --config backend/pyproject.toml backend tests --fix
```

11 个全部是 I001，集中在本轮新增的 `backend/tests/test_*_adjudication_runtime.py`、
`test_reading_share_privacy_projection.py`、`test_runtime_contracts.py`、
`test_runtime_worker_document_matrix.py`、`test_time_check_*.py` 等文件（新引入
`mingli_paths` 导致导入块未排序）。

mypy 2 个错要**按语义修，不要加 `# type: ignore` 糊过去**：

- `backend/app/readings/narrative_guard.py:127` — `no-any-return`，该函数声明返回 `bool`，末尾比较链的操作数来自 `dict[str, Any]`
- `backend/app/readings/service.py:496` — `union-attr`，`product: ProductVersion | None` 在 `product.id` 处未收窄；`family is None` 分支已 raise，但 `product is None` 没有独立分支

### A2 工作区卫生

- 删掉 exFAT 盘产生的 AppleDouble 垃圾（本仓与 `core/mingli-master` 下都有）：
  `./._DESIGN.md`、`scripts/._verify_predicates.py`、`snapshots/._*.json`、
  `docs/redesign/._2026-08-17-*.md`、`docs/predicate-authoring/._SPEC.md` 等
- 在 `.gitignore` 增加 `._*`，避免复发
- 给 `snapshots/` 与 `artifacts/binding-manifest-baselines/` 定去向：属于可复验证据就移进
  `docs/releases/evidence/**` 并在 CHECKLIST 第 13 节登记；属于可再生中间产物就加 `.gitignore`。
  **不允许继续半挂在仓库根目录**

### A3 分层提交（本轮已获用户授权 commit；**禁止 push**）

**严禁 `git add -A` / `git checkout .` / `git reset --hard`。** 工作树里有大量跨轮次改动，
逐条 `git add <path>`，每次 commit 前用 `git diff --cached --stat` 复核范围。

按下列分组提交，Conventional Commits，每组一个 commit：

| # | 仓库 | 范围 |
|---|---|---|
| 1 | `core/mingli-master`（独立 Git 历史，单独提交） | 58 个文件的逐字证据投影、规则绑定、来源表与 G3 日历语义改动 |
| 2 | 本仓 | G1 链：`contracts/schemas/**`、`contracts/openapi/v1.yaml`、backend 证据投影、`web` 证据渲染与对应测试 |
| 3 | 本仓 | G3 时间透明 + 分享隐私：`backend/app/readings/share_contracts.py`、`SharedReadingDocumentV1`、时间面板与相关测试 |
| 4 | 本仓 | 八字深读 P0 与 checkout：`bazi-deep-*`、`commerce_public*`、`delivery_state`、`web/src/components/task/bazi-deep-task-flow.*` |
| 5 | 本仓 | 文档与证据：`DESIGN.md`、`CONTEXT.md`、`docs/CHECKLIST.md`、`docs/predicate-authoring/**`、`docs/adr/0012-*`、`docs/releases/evidence/**`、本文件 |

每个 commit 前跑该组的定向测试；5 个 commit 全部落地后跑一次全量 `make check` 并把结果写进
CHECKLIST 第 15 节。**不 push、不部署、不重签 Runtime、不动测试机。**

---

## 阶段 B · G4 能力分层（DESIGN §20 + §22 G4）

当前七术走同一个结果模板，紫微/六爻/七政的已激活判断规则为 0，却仍占着断法槽位——G4 不通过。

### B1 分层来源必须是 Runtime 实测，不是前端常量表

`DESIGN.md` §20.1 已在 2026-08-18 更正，给了「判断规则」的唯一机器定义：已签名 release 的
`references/index/evidence-rules.jsonl` 中 `runtime_active == true` **且**
`evidence_role == "issue_specific_judgment_rule"` 的条数。`methodology_rule`、`casting_rule`、
`timing_rule`、`imagery_correspondence`、`terminology_only` **都不算判断规则**，不得用来把一术抬进 A 档。

实测值（`.runtime/v53-time-check-release`，1328 条 / 192 条 `runtime_active`，复核命令见 §20.1）：

```
luming-nayin 56   qimen 40   bazi 19   taiyi 15   liuren 5
divination 5      fengshui 1  selection 1
ziwei 0           xingming 0  physiognomy 0
```

**在后端做只读投影**，随能力策略或 ViewModel 下发 A/B/C 档；不要在 web 里硬编码分档表——
硬编码必然与 Runtime 漂移。参考 `backend/app/readings/capability_policy.py` 的既有版本化策略结构，
不要另起一套并行机制。

### B2 页面形态

按 §20.1 / §20.2：

- **A 档**：盘面 + 候选/证据 + 古籍命中抽屉 + 深读 Offer
- **B 档**（紫微 0 / 七政四余 0）：盘面 + 明示边界，**不出现断法区块，也不留空槽、不放占位卡**；
  B 档是「只做前两层的完整页」，盘面槽位仍要按 §8.1 做满
- **C 档**：「适配中/暂不可用」，**永不加载 Fixture 到正常路由**（§14）

### B3 一个必须停下来问用户的点

§20.1 旧归档记「六爻 0」。实测 `divination` 的 5 条判断规则已逐条查明：

| rule_id | 来源 | 归属 |
|---|---|---|
| `divination/huangjin-ce#HJC-R009` | 黄金策 · 求财以财福为主，兼看兄鬼父 | 六爻 |
| `divination/zengshan-buyi#ZR-04-04` | 增删卜易 · 用神两现 | 六爻 |
| `divination/meihua-yishu#MR-04-01` | 梅花易数 · 体用之分 | 梅花 |
| `divination/meihua-yishu#MR-04-02` | 梅花易数 · 体用生克吉凶 | 梅花 |
| `divination/meihua-yishu#MR-04-04` | 梅花易数 · 互变之用 | 梅花 |

即：**六爻 2 条、梅花 3 条**，两术按机器定义都已不满足 B 档的「判断规则为 0」。
这会改变 `/liuyao` 与 `/meihua` 的页面形态，属于产品决定，不是你能自行做的。

- **在用户明确批准前，`/liuyao` 与 `/meihua` 维持 B 档呈现，不得自行开出断法区块**
- 分档投影要按 `system` + `rule_id` 前缀把 `divination` 拆到六爻与梅花两术，不要把 5 条整包算给某一术
- 把这个待决问题写进本轮交付说明，等用户裁决

### B4 验收

- 逐 route 断言：`/bazi` = A、`/ziwei` `/qizheng` = B，B 档断言断法区块与占位卡都不在 DOM
- 一条测试锁死「分档值来自 Runtime 投影，不是常量」——改 Runtime 统计能让断言跟着变
- 分档实现与 §20.1 表若再出现不一致，以现算结果为准并回写 `DESIGN.md` §20.1 与 `docs/CHECKLIST.md`

---

## 阶段 C · G5 事实密度（DESIGN §22 G5、§19、§21）

这是本轮最大的实现缺口。现状：`web/src/components/readings/bazi-chart.tsx` 把关系、五行、大运
全压成了 `label / content` 单行文本——「地支关系 寅午半合（寅、午）」「五行计数 木2、火3、土2、金1、水1」
「大运 已计算 · 顺行 · 序列 丁未、戊申」。信息在，密度不在。

### C1 干支关系图

天干行 + 地支行，之间画关系连线。约束（§19.3）：`relation_type` 原样显示，**中性色区分类别，
不得把「冲」自动染成红色警示**。767 及以下允许在自身容器内横向滚动，**页面级不得横向溢出**。
必须提供语义 `<table>` 或带 `role` 的等价结构作为替代（§13 / §5）。

### C2 五行分布

柱状或雷达皆可，读得清即可，只画 `element_inventory` 的计数。
**不得叠加「缺某行 → 需补某行」**——那是用神层，不在本页范围。

### C3 大运

现在只取了 `cycles.slice(0, 3)`。要改成：

- 完整序列，不截断
- 起运信息：`direction`、`start_age_years`、`boundary_term`
- `unavailable` 数组逐项如实说明未能计算，不静默省略
- `status` 三态各有一个测试用例：`calculated` / `sequence_only` / `not_calculated_missing_gender`

### C4 时间层

`year_layers` / `month_layers` / `day_layers` 目前未渲染。按 §21.2 接上：切换时盘面容器不卸载、
不整块重绘、不改变页面几何，只对变化的标记做 120–180ms 的 opacity/transform 过渡，
不出现骨架屏闪烁，当前时间层在盘面与导航两处同时可辨。

### C5 联动扩展

把既有 `FactMark` / `selection` 联动扩到新组件：聚焦某天干/地支时，其藏干、十神、
**关系图连线、五行统计贡献**同时高亮。只用边框/底色/字重，不用位移、缩放、发光（§15）。
键盘聚焦与点击锁定等效，`Esc` 解除全部锁定（§21.1）。四柱按 §21.4 方向键可遍历，`Home`/`End` 跳首尾。

### C6 G5 判据（可判定，别靠感觉）

本机有 qingnang 站点镜像 `qingnang/site`（已 gitignore）。1440 与 768 两档并排截图，
统计可见结构化事实条目数，本产品不低于参考站。**不得靠超小字、截断或页面横滚达标**（§17）。
证据落 `artifacts/browser-evidence/2026-08-18-bazi-g5-density/`，附计数方法与两边计数结果。

---

## 阶段 D · G1 真实闭环（能做多少做多少，不许伪造）

用**真实签名 Runtime 产出**（不是 Fixture）从 `/bazi` 结果页抽取全部引文清单，然后：

```bash
python3 scripts/verify_citation.py --file <引文清单>.txt   # 退出码必须为 0
```

退出码非 0 就如实记录哪几条不过、为什么，不要改脚本阈值、不要挑样本。

**重签/重建 V53 release、上传测试机、部署、push 一律需要用户另行授权，本轮一概不做。**
当前签名 V53 不含本轮新增的三个 Bazi Claim Unit，这个事实要在 CHECKLIST 里保持可见。

---

## 每阶段完成定义（缺一不可）

- [ ] `make check` 全绿：Backend pytest + Ruff + mypy、Web 与 Admin 的 test/lint/typecheck、production build
- [ ] 360 / 768 / 1024 / 1440 四视口真实浏览器证据落盘，无页面级横向溢出，字阶在 DESIGN §4 冻结刻度
- [ ] 不新增依赖（Tailwind / GSAP / Lottie / 图表库都不行）；图标仅 lucide-react、复杂交互仅 radix-ui、动画仅 motion/react 或 CSS
- [ ] 不回归 §17 禁令与 §22 各门
- [ ] `docs/CHECKLIST.md` 第 15 节追加记录（日期 / 范围 / 实测门禁数字 / 证据路径），不改写历史行
- [ ] 状态标注为「证据就绪，待用户验收」——**你没有批准权**

## 红线

1. **严禁** `git add -A`、`git checkout .`、`git reset --hard`；只 add 你明确改动的文件
2. **严禁把未实际运行的验证写成通过**。上一轮 CHECKLIST 已出现一次「Ruff/mypy 通过」误报（实测 11 + 2 个错），本轮不得再犯：写进账本的每个数字都必须是当次跑出来的
3. **不 push、不部署、不重签上线、不动测试机与生产**
4. 需要改 `DESIGN.md`、`CONTEXT.md`、`docs/MINGLI_V51_WEB_INTEGRATION.md` 的**规则本身**时，先停下写影响范围与重新验收项，交用户批准；不得先改合同再施工
5. 不得为了让页面「看起来更满」而合成评分、档位、结论标签或伪造古籍原文（§17 / §22 G1、G2）

## 环境事实（已实测，直接用）

- 根：`/Volumes/Lexar/code/mingli_web`；`web/` 与 `admin/` 各有 package.json，仓库根无 package.json，npm 命令务必 `cd` 到子目录或用 `--prefix`
- 全量门禁：`make check`；分项见 `Makefile`
- **G3 原生回归用已安装的 Runtime venv：`~/.local/share/mingli-master/venv/bin/python`。
  不要新建 venv 去 pip 装 `sxtwl==2.0.7`——该版本 PyPI sdist 缺 `src/JD.cpp`，Python 3.11/3.12 都会在收集前构建失败。**
  已实测：`cd core/mingli-master && ~/.local/share/mingli-master/venv/bin/python scripts/test_calendar_solar_semantics.py` → `Ran 36 tests OK`（该 venv 无 pytest，用 unittest 直跑）
- Playwright 无内置浏览器，统一
  `chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" })`
- 参考站本地镜像：`qingnang/site`（212MB，已 gitignore），G5 并排统计用它，不要联网抓
- 已签名 Runtime 与规则索引在 `.runtime/`，`references/index/evidence-rules.jsonl` 是 G4 分档的唯一数据源
