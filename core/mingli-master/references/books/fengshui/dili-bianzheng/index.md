---
title: 地理辨正
slug: dili-bianzheng
system: fengshui
school:
  - 玄空理气
  - 蒋大鸿地理
  - 青囊天玉注解
source_layer: primary
source_status: normalized_ready
source_links:
  - https://ctext.org/wiki.pl?chapter=205668&if=gb&remap=gb
version_notes: |
  《地理辨正》清蒋大鸿传/注，含《青囊经》《青囊序》《青囊奥语》《天玉经》及辨伪诸论。
  本 pack 以 CTP Wiki 文本页为 normalized 底本，保留 CTP 行号；经文与蒋注暂不拆层。
depends_on:
  - qingnang-jing
  - qingnang-xu
  - tianyu-jing
  - dutian-baozhao-jing
informs:
  - fengshui-master-skill
core_use_cases:
  - 玄空理气、雌雄、金龙、血脉、三叉、天元/人元/地元等概念索引
  - 与《青囊经》《青囊序》《天玉经》对读，辨蒋大鸿注解层
  - 风水理气派与形势派冲突时的理气侧证据
not_for:
  - 直接替代罗盘坐向计算
  - 对具体阴宅阳宅作吉凶承诺
  - 不拆经注层时回答精确版本校勘问题
extraction_targets:
  - chapter_map
  - terms
  - rules
  - procedures
  - quote_index
conflict_policy: |
  与形势法冲突时，应说明本书是蒋氏玄空/理气立场；实际判断需同时读取《葬书》《雪心赋》《撼龙经》等形势层。
  与《青囊经》《青囊序》独立 pack 冲突时，先区分“原经白文”和“蒋注解释”。
validation_notes: |
  CTP 行表 301 行已抽取；quote-index 短引 exact-ish 命中。
modern_notes: |
  现代应用需专业罗盘与现场资料；LLM 只负责术语路由与原典解释。
---

# 地理辨正 Reference Pack

- 本地全文：`references/fulltext/fengshui/dili-bianzheng/fulltext.md`
- 文本锚点：https://ctext.org/wiki.pl?chapter=205668&if=gb&remap=gb
- 注记：经文与蒋注混排，后续可拆成 `text_layer` / `commentary_layer`。
