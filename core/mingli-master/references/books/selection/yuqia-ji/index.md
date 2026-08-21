---
title: 玉匣记
slug: yuqia-ji
system: selection
school:
  - 民间通书
  - 民俗杂占
  - 吉凶日
  - 出行嫁娶
source_layer: commentary
source_status: normalized_ready
source_links:
  - https://zh.wikisource.org/zh-hans/%E7%8E%89%E5%8C%A3%E8%A8%98
  - https://ctext.org/wiki.pl?if=gb&res=618676
version_notes: |
  托名晋·许逊（许真君）、唐·李淳风、唐·袁天纲合纂的民间通书系经典。
  实际成书年代不可考；明清两代叠加扩充而成，最广泛流传的版本是清嘉庆/道光至民国坊刻本。
  与《董公择日》同为民间通书系代表，但本书更偏"杂占吉凶日"系统，
  广收"杨公忌、月忌日、彭祖百忌、十恶大败、人神所在"等民俗禁忌日。
  全书 265 子目，分三大篇：理论吉凶日篇、民俗吉凶日篇、杂占篇。
  本 pack 取维基文库电子文本为基（与中国国图善本影印对校）。
depends_on: []
informs:
  - donggong-zeri
core_use_cases:
  - 民俗禁忌日的查询入口（彭祖百忌 / 杨公忌 / 月忌日 / 十恶大败等）
  - 民俗杂占规则汇编（鹤神方位 / 人神所在 / 探病忌日等）
  - 民间出行 / 嫁娶 / 上任 / 应试等吉凶日
  - 民俗信仰中的"圣诞日"、"星辰值年命"等
not_for:
  - 实际择日计算（必须调用 mingli-master.selection.v1）
  - 嫁娶 / 丧葬 / 出行的事实性吉凶断言（仅作民俗参考）
  - 官方择日依据（应优先 xieji-bianfang-shu / xingli-kaoyuan）
  - 神煞起例考源（应优先 xingli-kaoyuan）
extraction_targets:
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  与同体系其他典籍冲突时按 matrices/conflict-policy.md §1.4 裁判：
  - 与官方典籍（协纪辨方书 / 星历考原）口径冲突 → 以官方为准；本书定位为"民俗参考"。
  - 与董公择日重合 → 互补；本书偏杂占禁忌日，董公择日偏月将吉凶日。
  - 涉及具体日子吉凶 → 一律转 mingli-master.selection.v1 计算。
validation_notes: |
  - source_status 维持 partial（维基文库文本未对国图善本影印逐条复核）。
  - 全书 265 子目庞大且碎片化；本 pack 不按"子目"做章节，而按"3 大篇 + 30 个主题分组"做章节。
  - 不复制大段歌诀；只引每子目题名作锚。
cultural_caveats: |
  本书为民间通书，全书"吉凶日 / 禁忌日 / 神煞日"性质极强；
  现代不构成事实判断；输出时必须加 caveat："文化参考，非事实判断"。
  禁忌日（如"探病忌日"、"人神所在日"）若引致用户避就医避治疗，须明确提示寻求医疗专业意见。
---

# 玉匣记 Reference Pack（index）

> 本文件是《玉匣记》参考包的**入口索引**，不做规则 / 术语 / 短引的详细内容。
> 详细内容分布在 `chapter-map.md / section-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。
> 主 skill 默认只加载本文件；按需加载其它文件。

## Source

- **托名**：晋·许逊（许真君）、唐·李淳风、唐·袁天纲合纂（民间托名）。
- **实际成书**：不可考；明清两代叠加扩充；最广流传版本为清嘉庆 / 道光至民国坊刻本。
- **底本系统**：
  - 维基文库电子文本（含"《玉匣记》许真君日期"、"诸葛武侯逐年出行图"等核心组）
  - 国图 / 北图善本影印（待对校）
  - CTP 文本锚点（不作下载源，TOS 限制）
- **结构**：全书 265 子目，分 3 大篇
  - **理论吉凶日篇**（约 11 个子目，L302-L1213）：玉匣记日期、法师选择记、三元五腊圣诞、十殿阎君圣诞、雕塑神像吉日、男女值年星辰、九耀星君值男女命限、二十八宿值日吉凶 / 风雨阴晴歌
  - **民俗吉凶日篇**（约 60 余子目，L1214-L3467）：彭祖百忌、杨公忌、月忌日、十恶大败、伏断日、九土鬼日、人神所在、神号鬼哭、鹤神方、上官赴任、嫁娶、出行、应试、营建、丧葬、医疗、农事、商事 等
  - **杂占篇**（约 90 余子目，L3468-L4119）：占梦、面热耳鸣眼跳、占禽鸟、占婴儿啼笑、占鼠咬衣、占蛇入宅、占灯花鸡犬等
- **复核状态**：`partial`。

## Position In Lineage

- **在择日体系中的位置**：民间通书系最广流传的"杂占禁忌日大全"。
- **上游**：
  - 唐宋《历事明原》《禄命书》中的禁忌日条目
  - 道教神祇历法（许真君 / 净明派传统）
- **下游**：
  - 民国坊刻通书 / 黄历应用直接采用
  - 现代万年历 / 黄历应用底层"忌日"模块多取材本书
  - 与《董公择日》互补构成民间通书系完整生态

## Loading Guide

主 skill 加载约定（遵循 matrices/validation-checklist.md §L.11）：

1. **默认只加载本文件** `index.md`。
2. **需要查民俗禁忌日** → 加载 `rules.md` 与 `quote-index.md`。
3. **需要查具体子目** → 加载 `chapter-map.md`。
4. **需要查术语** → 加载 `terms.md`。
5. **需要查可操作流程** → 加载 `procedures.md`（全部依赖 mingli-master.selection.v1）。
6. **需要校验覆盖率** → 加载 `validation.md`。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 3 大篇 + 30 主题分组 | 需要查具体子目 |
| [terms.md](./terms.md) | 全书术语抽取（按分组） | 需要查术语定义 |
| [rules.md](./rules.md) | 全书判断规则（民俗禁忌日通则） | 需要查判断规则 |
| [procedures.md](./procedures.md) | 全书可操作流程（工具调用） | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引索引 + 出处 | 需要引用原文 |
| [validation.md](./validation.md) | 全书覆盖率 + 版本核验 + 待办 | 需要校验覆盖率 |

## Routing

主 skill 收到择日 / 民俗杂占相关问题后：

1. 本 pack 是"民俗禁忌日 / 杂占"的代表（详见 matrices/routing-matrix.md §6）。
2. 按问题类型分流：
   - 民俗禁忌日（彭祖百忌 / 杨公忌 / 月忌日 / 十恶大败 / 人神所在 等） → 本 pack
   - 民俗杂占（梦占 / 耳鸣眼跳 / 禽鸟征兆 等） → 本 pack
   - 月将吉凶日（民间通书） → `selection/donggong-zeri`
   - 通用择日 / 嫁娶 / 丧葬 / 起造（官方裁判） → `selection/xieji-bianfang-shu`
   - 神煞起例考源 → `selection/xingli-kaoyuan`
   - 涉及具体日子吉凶 → `mingli-master.selection.v1`（必需）
3. 与官方典籍冲突时，本 pack 让位（定位为民俗参考）。

## 冲突裁判

详见 frontmatter `conflict_policy` 与 matrices/conflict-policy.md §1.4。

## 文化警示

本 pack 的禁忌日规则属古代民俗信仰；输出涉及"某日吉凶""某事宜忌""某日忌探病忌就医"等内容时，
**必须加 caveat："文化参考，非事实判断"**。
若禁忌涉及医疗（探病忌日 / 人神所在日 等），须额外明确提示"请遵从医疗专业意见，勿因民俗禁忌延误就医"。
