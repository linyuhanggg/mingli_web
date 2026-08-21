# 太微赋 — D2 蒸馏验证

## D2 状态

- d2_status: ready_candidate
- batch: D2-evidence-repair
- scope: 本地规范化全文 `references/fulltext/ziwei/taiwei-fu/fulltext.md`
- source_status: partial
- source_basis:
  - preferred_source: 维基文库《太微賦》
  - local_text: 本地 normalized fulltext
  - collation_target: 《紫微斗数全书》卷一所载文本
- verified: false

## 覆盖率审计

- chapter_count_total: 32
- chapter_status:
  - done: 32
  - partial: 0
  - pending: 0
  - skipped: 0
  - unavailable: 0
- strict_fulltext_coverage: 100%
  - 单篇赋文按内容逻辑拆为 32 个分段
  - 总论、入庙失度、著名格局、凶象告诫均进入 `chapter-map.md`
- quote_exact_match:
  - total: 38
  - exact_hits: 38
  - hit_ratio: 100%
  - repair_note: D2 已将简体/通行字形改为本地繁体原文，如 `祿/禄`、`廟/庙`、`輔弼/辅弼`、`泡漚/泡沤`

## 抽取覆盖审计

- terms: 61 条
- rules: 21 条
- procedures: 4 条
- extraction_scope:
  - 分段均进入术语、规则、流程或短引层
  - 赋文短句作为证据，不直接升级为现代断语
  - 星曜庙旺利陷、宫位具体计算必须依赖紫微排盘工具，不让 LLM 手算

## 敏感断语 reframe

- 寿夭/死亡:
  - 七杀廉贞同位，路上埋尸
  - 破军暗曜同乡，水中作冢
  - 杀居绝地，天年夭似颜回
  - 七杀临身命加恶杀，必定死亡
  - 童子限、老人限相关比喻
- 刑戮/灾祸:
  - 铃羊合命宫遇白虎，须当刑戮
  - 刑囚夹印，刑杖惟司
- policy:
  - 以上条文只作紫微赋文史料与术语源流参考
  - 不得铁口断寿、断死、断刑灾
  - 不替代医学、法律、心理或安全建议

## 仍需复核

- 与《紫微斗数全书》卷一逐句互校
- 与《增补太微赋》文本差异厘清
- 入庙失度具体配位与《全书》卷二庙旺利陷表对照
- 桃花、淫、刑戮、寿夭等词的现代输出包装统一

## 结论

该 pack 可作为 D2 ready candidate：32 个分段全部完成证据图谱，38/38 短引 exact-match，通过单书证据链审计。它仍不应升级为最终权威 skill，因为尚未完成《紫微斗数全书》卷一校勘和庙旺利陷表对照。
