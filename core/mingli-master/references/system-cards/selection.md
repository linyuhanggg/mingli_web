# 择日 (selection)

## Packs

| pack | title | best for | do not use for | caveat |
|---|---|---|---|---|
| `selection/donggong-zeri` | 董公择日 | 民间嫁娶/起造/丧葬/出行/上任择日的"通书系"对照参考; 月将吉凶日（金神七煞、煞贡、直星、人专吉日）的口诀汇总; 与官方《协纪辨方书》《星历考原》比对的民间口径参照 | 实际择日计算（必须调用 mingli-master.selection.v1）; 嫁娶/丧葬/出行吉凶的事实性断言（仅作文化参考）; 与皇历/通书系统的系统化对照（应优先 xieji-bianfang-shu） | - source_status 调整为 normalized_ready：本地维基文库整理文本已完整规范化；但尚未对国图影印逐页校勘。 - "董德彰"身份及成书年代均待考。 - 书中涉及嫁娶/丧葬/出行吉凶的"应验"语气均需 reframe 为"文化参考"。 - 月份吉凶日与四柱神煞的对应关系需与《协纪辨方书》《星历考原》交叉验证。 |
| `selection/xieji-bianfang-shu` | 协纪辨方书 | 官方择日体系的"集大成"参考（嫁娶/丧葬/起造/出行/上任/祭祀）; 全套年神 / 月神 / 日神 / 时神的考源与裁判; 建除十二神、二十八宿、黄黑道的官方取法 | 实际择日计算（必须调用 mingli-master.selection.v1）; 嫁娶/丧葬/出行的事实性吉凶断言（仅作历法参考）; 神煞起例源流考据（应优先 xingli-kaoyuan 卷一卷二） | - source_status 维持 partial（维基文库 + Internet Archive 文本未对四库本影印逐卷复核）。 - 全书 36 卷，本 pack 按"卷"作 chapter 粒度，做摘要级覆盖（不做小目级）。 - 卷十至卷三十二为"日表 / 时辰" 大型表格，本 pack 不复制原表，只声明"调用 tool.selection.l... |
| `selection/xingli-kaoyuan` | 星历考原 | 神煞起例的官方考源（"此神出于何典、起法如何"）; 年神 / 月神 / 日神 / 时神的起例口诀考证; 与《协纪辨方书》对照差异，定本源 | 实际择日计算（必须调用 mingli-master.selection.v1）; 嫁娶 / 丧葬 / 出行的事实性吉凶断言（仅作历法参考）; 用事宜忌的"定论"（应优先 xieji-bianfang-shu 卷七·八） | - source_status 维持 partial（维基文库文本未对四库本影印逐卷复核）。 - 全书 6 卷，本 pack 按"卷"作 chapter 粒度，关键神煞（每卷 5~10 条）作为 partial 引用。 - 不复制大段原文；神煞起例口诀只引题名 + 起例锚点。 |
| `selection/yuqia-ji` | 玉匣记 | 民俗禁忌日的查询入口（彭祖百忌 / 杨公忌 / 月忌日 / 十恶大败等）; 民俗杂占规则汇编（鹤神方位 / 人神所在 / 探病忌日等）; 民间出行 / 嫁娶 / 上任 / 应试等吉凶日 | 实际择日计算（必须调用 mingli-master.selection.v1）; 嫁娶 / 丧葬 / 出行的事实性吉凶断言（仅作民俗参考）; 官方择日依据（应优先 xieji-bianfang-shu / xingli-kaoyuan） | - source_status 维持 partial（维基文库文本未对国图善本影印逐条复核）。 - 全书 265 子目庞大且碎片化；本 pack 不按"子目"做章节，而按"3 大篇 + 30 个主题分组"做章节。 - 不复制大段歌诀；只引每子目题名作锚。 |

## Runtime use

This card is capability and source metadata for selecting the transaction
system before `prepare`. During a live reading, use only the bounded evidence
returned by the transaction; do not load packs or run a separate corpus search.
The caller must supply structured exact `requested_actions` within the selected
event profile; sibling actions in the same profile are comparison context and
never determine one another's eligibility.
