# SS-B1 八字 / 禄命高频神煞二次精修矩阵

generated_at: 2026-07-05
matrix_version: v0.1
batch_id: SS-B1
source_status: distilled_from_ready_local_packs_and_qoder_manifests

本文件是 `shensha-distillation-backlog.md` 的第一批落地产物。它不替代单书 reference pack，也不把神煞提升为独立判断体系；它只回答：八字/禄命高频神煞在 `mingli-master` 里应怎样加载、怎样降权、怎样避免串台。

## 来源状态

SS-B1 只使用已经有完整本地文本和 D2 pack 的来源：

| Pack | 角色 | 当前口径 |
|---|---|---|
| `bazi/sanming-tonghui` | 八字神煞一线索引 | Qoder manifest 为 normalized ready；Codex pack validation 为 D2 ready |
| `luming-nayin/wuxing-jingji` | 早期禄命神煞汇编 | Qoder manifest 为 normalized ready；Codex pack validation 为 D2 ready |
| `luming-nayin/li-xuzhong-mingshu` | 早期贵神/禄命术语支持 | Qoder manifest 为 normalized ready；Codex pack validation 为 D2 ready candidate |
| `luming-nayin/luoluzi-sanming` | 禄命赋文、行运神煞源流 | Qoder manifest 为 normalized ready；Codex pack validation 标明原赋/注文需分层 |
| `luming-nayin/yuzhao-shenying` | 早期断语与神将取象 | Qoder manifest 为 normalized ready；Codex pack validation 为 D2 ready candidate |

## 使用总则

1. 八字答案中，SS-B1 神煞只能位于 `bazi-core-decision-stack` 的 `BZ-07 auxiliary_only` 层。
2. 神煞不得覆盖月令、格局、旺衰、调候、十神、大运流年。
3. 禄命来源只作源流与互证，不能直接覆盖现代子平主线。
4. 白虎、丧门/吊客、伏吟/反吟在本批中主要是禄命/六壬/紫微等跨系统高危词，不能因为名字常见就塞进八字神煞清单。
5. 每次调用必须先有事实层：八字要有四柱、藏干、十神、月令/调候、是否使用大运流年；禄命源流研究要说明只做 source-history。

## 条目精修

| Entry | 八字一线 | 禄命源流 | 操作意义 | 禁止外推 |
|---|---|---|---|---|
| `shensha-tianyi-guiren` 天乙贵人 | `sanming-tonghui` | `wuxing-jingji`, `li-xuzhong-mingshu` | 贵人/解厄/助力类辅证 | 不等于六壬天乙天将；不能单凭天乙断富贵 |
| `shensha-jinyu` 金舆 | `sanming-tonghui` | `wuxing-jingji`, `li-xuzhong-mingshu` | 车舆、礼遇、迁动资源类辅证 | 不能单凭金舆断豪车、资产等级 |
| `shensha-lushen-lucun` 禄/禄神/禄存/化禄 | `sanming-tonghui` | `wuxing-jingji`, `li-xuzhong-mingshu`, `luoluzi-sanming` | 八字干禄/禄马/福神辅助 | 不等于紫微禄存/化禄；不等于星命禄神 |
| `shensha-yima-tianma` 驿马/天马 | `sanming-tonghui` | `wuxing-jingji`, `li-xuzhong-mingshu` | 动迁、出行、远动、职业流动辅证 | 不等于择日天马；不等于紫微天马；不能无事实层择日 |
| `shensha-xianchi-taohua` 咸池/桃花 | `sanming-tonghui` | 无一线禄命 profile | 社交、审美、情欲/关系吸引力辅证 | 不输出古文道德标签；必须合参十神、夫妻宫、运年 |
| `shensha-kongwang` 空亡 | `sanming-tonghui` | `wuxing-jingji`, `li-xuzhong-mingshu`, `luoluzi-sanming` | 虚位、落空、减力、待填实辅证 | 不作“一切皆空”的绝对断语 |
| `shensha-luowang` 天罗/地网 | `sanming-tonghui` | `luoluzi-sanming`, `wuxing-jingji` | 束缚、阻滞、辰巳/戌亥类罗网辅证 | 不等于择日黄黑道；不作医学/灾病硬断 |
| `shensha-fuyin-fanyin` 伏吟/反吟 | 不升为本批八字一线 | `luoluzi-sanming`, `wuxing-jingji` | 运命重复/冲击、同位/对冲类源流 | 不等于六壬返吟/伏吟；八字聊天用法需另有事实层 |
| `shensha-baihu` 白虎 | 不升为八字一线 | `yuzhao-shenying`, `wuxing-jingji` | 禄命神将/道路/刚烈类源流 | 不等于六壬白虎天将；不进八字神煞库存 |
| `shensha-sangmen-diaoke` 丧门/吊客 | 不升为八字一线 | `luoluzi-sanming` | 宅墓丧吊源流，敏感断语只作文化研究 | 不作真人丧事硬断；不移植到八字日常运势 |

## 短引锚点

这些锚点用于定位，不要求回答时全量引用：

| Entry | Bazi anchors | Luming anchors |
|---|---|---|
| 天乙贵人 | `SM-Q149`, `SM-Q150` | `WX-Q147`, `WX-Q238`, `WX-Q242` |
| 金舆 | `SM-Q144`, `SM-Q146`, `SM-Q492` | `WX-Q452`, `WX-05-06` |
| 禄/禄神 | `SM-Q148`, `SM-Q492` | `LZ-Q33`, `LZ-Q35`, `WX-Q238`, `WX-Q242` |
| 驿马/天马 | `SM-Q147`, `SM-Q148` | `WX-Q357` |
| 咸池/桃花 | `SM-Q139`, `SM-Q188`, `SM-Q762` | 无本批一线 |
| 空亡 | `SM-Q160`, `SM-Q183` | `WX-Q177`, `WX-Q190`, `WX-Q200` |
| 天罗/地网 | `SM-Q182`, `SM-Q185` | `LZ-Q40`, `WX-Q623`, `WX-Q630` |
| 伏吟/反吟 | 无本批八字一线 | `LZ-Q39`, `LZ-Q72`, `WX-10-04` |
| 白虎 | 无本批八字一线 | `YZ-Q052`, `YZ-T15`, `YZ-T37` |
| 丧门/吊客 | 无本批八字一线 | `LZ-Q66`, `LZ-T83`, `LZ-07-06` |

## 回答层融入规则

- 八字神煞盘点：只列一线八字可用条目；若用户问到白虎、丧门吊客，要说明本批不把它们作为八字一线神煞。
- 八字流年/关系/财运：神煞只能解释“象”和“触发点”，不产生最终吉凶结论。
- 源流研究：可以并读禄命 pack，但输出要标明“禄命源流，不覆盖子平主线”。
- 缺事实层：停止解释，只列需要的 adapter 输出。
