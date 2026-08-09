---
version: 1
slug: "web-src-app-page-tsx"
primary_target: "web/src/app/page.tsx"
related_targets: ["web/src/app/pricing/page.tsx","web/src/app/methodology/page.tsx","web/src/app/support/page.tsx"]
---

# FateRadar 公共入口

## Scope and visitor mode

首页是“先体验、后登录”的公共入口，模式先 Persuade，再 Orient。它负责说明服务如何工作并把访客送入三个 P0 任务，不承担真实排盘、支付或私人解读交付。

## Audience, job, and action

面向第一次接触 FateRadar、但不接受黑箱结论的中文用户。访客应在第一屏理解确定性核心、可核对依据和私密边界；主行动是建立并核对档案，次行动是一事一问，今日与近七日作为第三个清晰任务入口。

## Proof and content

用“确认输入 → 形成事实 → 引用依据 → 现实核对”的阅读顺序证明方法。结果结构只能作为明确标注的界面示例；价格、交付与隐私区域只陈述已确认合同，未开通能力保持禁用或开发期说明。

## Chosen direction and memorable moment

首页采用东方编辑档案的长页节奏。第一视口像一张深色档案扉页：左侧大标题把“时间变得可读”，右侧时间刻度把抽象时间校准成可核对对象；随后三张任务卡按真实 P0 优先级展开。

## Constraints

首页不是聊天框，不做十三体系入口，不展示评价、销量、支付成功或真实命盘假数据。移动端保持同一阅读顺序、至少 44px 触控目标和无横向溢出；动效只辅助理解时间与层级，并尊重 reduced motion。

## Unresolved decisions

- 真实 Runtime 接入后，免费概览的结果片段与证据密度需单独验收。
- 支付能力、运营客服、备案与法律主体确认后，再决定相应 CTA 与页脚信息是否开放。
