# 撼龙经 — D2 蒸馏验证

## D2 状态

- d2_status: ready_candidate
- batch: D2-evidence-repair
- scope: 本地规范化全文 `references/fulltext/fengshui/hanlong-jing/fulltext.md`
- source_status: partial
- source_basis:
  - source_anchor: CTP 四库本合刊《撼龙经 疑龙经 葬法倒杖》
  - local_text: 本地 normalized fulltext
  - source_note: 该本为四库提要合刊文本；《撼龙经》主体与《疑龙经》《葬法倒杖》连续收录，蒸馏端须以章节边界限定引用范围
- verified: false

## 覆盖率审计

- chapter_count_total: 13
- chapter_status:
  - done: 13
  - partial: 0
  - pending: 0
  - skipped: 0
  - unavailable: 0
- strict_fulltext_coverage: 100%
  - 13 个章节单元全部进入 `chapter-map.md`
  - 四库提要作为版本与作者考据单元保留
  - 九星主体、右弼隐曜、九星出穴与七星歌均有章节锚点
- quote_exact_match:
  - total: 23
  - exact_hits: 23
  - hit_ratio: 100%
  - repair_note: D2 已将通行字形替换为本地四库文本字形，如 `峰/峯`、`高/髙`、`蓋/葢`、`鎖/鎻`

## 抽取覆盖审计

- extraction_scope:
  - 术语、规则、流程以形峦九星体系为主，不强制版本提要进入规则抽取
  - `tiyao` 仅作作者归属、四库删注、合刊关系说明
  - `zonglun` 至 `chuxue` 均进入术语、规则、短引或流程层
- expected_use:
  - 形峦风水九星辨体
  - 平洋龙与高山龙辨别
  - 贪狼、巨门、禄存、文曲、廉贞、武曲、破军、左辅、右弼的形象与出穴
  - 与《疑龙经》《葬法倒杖》合读时的上游形势依据

## 仍需复核

- 影印本逐字校勘，尤其异体字、阙字、疑似 OCR 字
- 杨筠松作者归属与年代考辨
- 《撼龙经》《疑龙经》《葬法倒杖》合刊边界复核
- 李国本旧注被四库删削内容是否影响后世流派理解
- “出穴篇”“七星歌”是否为后人附益，需在 master skill 中作为版本争议注明

## 结论

该 pack 可作为 D2 ready candidate：章节图谱完整，短引 23/23 exact-match，通过单书证据链审计。它仍不应升级为最终权威 skill，因为尚未完成影印本复核、版本附益考辨，以及与《疑龙经》《葬法倒杖》的合刊关系消解。
