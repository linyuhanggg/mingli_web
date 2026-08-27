# 方向 C 决策记录 — 2026-08-14

> **SUPERSEDED（2026-08-27，MING-29 权威收敛）**：方向 C（含本记录第 1 条的 `#fafafa` / `#2563eb` token 值）及其前身 A（现代书院）/B（深墨东方）样板，已被用户最终选型的**玄序 Xuan Order** 整体替代。本文件只保留历史引用，不得与玄序并列为现行权威，不得作为施工、验收或测试钉值依据；后续不存在 A/B/C 方向比较。现行视觉基线与三态表见 `../product-authority.md` §3.1 / §4.1。

状态：用户已批准（grilling 会话逐题确认）。
前置审计：`./2026-08-14-visual-audit.md`（56 张四视口截图 + 客观指标，`web/e2e/screenshots/audit-2026-08-14/`）。
样板证据：`/_ui-lab/redesign-a|b|c`（dev-only），截图 `web/e2e/screenshots/audit-2026-08-14/redesign-{a,b,c}/`。

## 决策

1. **视觉方向：C · 现代 SaaS 锐感**，推翻 2026-08-13 冻结的中性合同表现层。基底：浅灰 `#fafafa` 底、纯白面、单蓝 `#2563eb` 点缀、8px 圆角、紧字距、细线分层。A（现代书院）与 B（深墨东方）样板落选。
2. **推广范围：一期全站换皮**（公共页 + 录入流 + 工作台 + 账户 + Admin），不留新旧并存期。
3. **IA 大改，痛点三条**：
   - 首页不像产品首页 → 改「价值主张 + 任务入口」混合结构；
   - 三跨术入口概念重叠 → **保留两个：命盘合参（吸收多盘问答）+ 问事合参**；
   - 账户页简陋 → 重建为**消费 App「我的」页**（身份卡 + 宫格入口 + 最近交付，移动优先）。
4. **首页 Hero 文案（版①，体系规模感）**：主标「十三术同根，五十五部古籍为证」；副标基于真实事实：13 Provider、55 古籍 reference pack、1328 条 evidence index（来源 `docs/MINGLI_V51_WEB_INTEGRATION.md` §2.1/§3.3）。合规红线：不讲准不准、不做效果承诺、不伪造社会证明。
5. **文档策略**：修改现有合同（DESIGN.md/CHECKLIST.md/CONTEXT.md 原地修订），不新建第二份合同；决策与审计证据归档 `docs/redesign/`。
6. **taste skill 使用边界**：只借其审计/反套路纪律；其 Tailwind/GSAP/Phosphor 默认不进入项目（CSS Modules + Lucide + motion/react 维持）。

## 执行阶段

0. 文档解冻（本记录 + DESIGN.md/CHECKLIST.md/CONTEXT.md 修订）
1. 基础层：`ui/tokens.css`、`ui/base.css` 重写；字阶漂移收口；`web/src/components/` 域分组（合并 reading/readings）
2. 公共壳 + 新首页 + 营销页族
3. 账户区重建（消费 App 我的页）
4. 产品流/工作台换皮 + 合参 IA 合并（路由 + 重定向）
5. Admin token 对齐

每阶段：360/768/1024/1440 真实浏览器证据 + 用户亲自批准；`npm test / typecheck / lint / build` 全绿。样板页 redesign-a/b/c 在阶段 2 验收后删除。
