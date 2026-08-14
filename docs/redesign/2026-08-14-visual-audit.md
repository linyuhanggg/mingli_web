# 视觉与体验审计 — 2026-08-14（redesign 前置）

触发：用户反馈「整体廉价/乱，UI 与架构不合理，想推翻重来」。
方法：dev server（http://127.0.0.1:3000）+ Playwright 系统 Chrome，14 路由 × 4 视口（360/768/1024/1440）截图 + DOM 客观指标。截图：`web/e2e/screenshots/audit-2026-08-14/`。脚本：`web/scripts/audit-screenshots.mjs`、`web/scripts/audit-metrics.mjs`。
限制：本次审计主模型无视觉能力，结论基于客观指标 + 代码/CSS 精读；截图已存档供人工复核。

## A. 合同底线（客观指标）— 全部达标
- 四视口 8 条抽样路由均无页面级横向滚动（scrollWidth == innerWidth）。
- 抽样文本节点对比度全部过 WCAG AA（0 违规）。
- 无小于 44px 的交互目标。
- 断点行为符合 DESIGN.md §5。

## B. 「廉价/乱」的客观来源
1. **字阶漂移**：DESIGN.md §4 冻结字阶为 12/14/16/18/20/24/32/40–48。实测 pricing 出现 23/28/35/39/46/54/72/77px，auth 出现 15/19px，tools 出现 13px —— 页面级 CSS 各自为政，是「乱」的直接证据。
2. **首页无视觉焦点**：intro 一句话 + 三组等宽卡片 + 辅助区，三档 tone（paper/ink/clay）只是白/黑/灰换色，无品牌记忆点、无视觉签名，接近线框图。
3. **无品牌资产**：品牌名/Logo/强调色在合同里本就「未冻结」，当前用 Lucide Compass 占位，全站唯一「图形语言」是 1px 灰边。
4. **视觉签名缺失**：分层全靠 1px 灰边 + 白/灰面，hover 仅 translateY(-2px)，无任何可识别的工艺细节。

## C. 代码架构问题（web/src）
1. `components/` 下 60+ 文件平铺，且 `reading/` 与 `readings/` 两个易混目录并存；`surfaces/`、`task/`、`workbench/` 边界无文档。
2. 页面级 module.css（home/editorial-page）与组件级 module.css 模式不统一，字阶漂移即由此产生（B1）。
3. `app/` 路由 30+，公开营销页（about/pricing/methodology）与产品页混排，无 route group 分层。

## D. 方向稿（taste skill dials 描述）

### 方向 A — 现代书院 / Editorial（推荐）
- Dials: VARIANCE 6 / MOTION 3 / DENSITY 4。
- 排版驱动：标题层级开放 Noto Serif SC（现为盘面专用），大字阶对比、细分隔线、宽松留白；保持中性黑白灰，加 1 个低饱和墨色系强调。
- 参照：读库 / Kinfolk / Stripe Press 的中文化。
- 与冻结合同兼容度最高：只解冻 DESIGN.md §2/§4（品牌、字体），IA 不动。

### 方向 B — 深墨东方 / Dark Premium
- Dials: VARIANCE 7 / MOTION 5 / DENSITY 4。
- 深墨底 + 单一点缀（朱砂或金），盘面 Songti 大字有仪式感；公共页最有「命理气质」。
- 代价：DESIGN.md §17 明禁的旧皮肤（墨绿金）需明确区分；暗色可读性/对比度成本高；工作台与 Admin 全量暗色化工作量大。

### 方向 C — 现代 SaaS 锐感 / Linear-style
- Dials: VARIANCE 6 / MOTION 4 / DENSITY 5。
- 保持黑白灰，加精度：紧凑网格、tabular numerals、细腻 hover、单蓝强调（复用 --color-focus）。
- 最「贵」但命理气质最弱，与品类识别度有张力。

## E. 建议顺序
1. 先定方向（A/B/C）→ 2. 解冻 DESIGN.md 对应章节 → 3. tokens.css + base.css 收口字阶 → 4. 首页 + 1 条产品流做样板 → 5. 四视口真实浏览器验收（用户亲自批准）。
