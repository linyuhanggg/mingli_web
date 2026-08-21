# 董公择日 — Validation

> D2 evidence-chain validation. 本文件只证明 reference pack 对本地规范化文本的覆盖与可追溯性，不证明版本学定本或现实择日有效性。

## Source State

- **manifest**：`sources/manifests/donggong-zeri.yaml`
- **normalized_status**：ready
- **normalized_source_path**：`references/fulltext/selection/donggong-zeri/fulltext.md`
- **primary_text_source**：维基文库 action=raw 整理文本
- **image_source_anchor**：Wikimedia Commons 国图藏本镜像
- **verified_against_image**：false

## D2 Coverage

- **chapter_count_total**：17
- **chapter_count_done**：17
- **chapter_count_partial**：0
- **chapter_count_pending**：0
- **chapter_count_skipped**：0
- **chapter_count_unavailable**：0
- **strict_coverage**：100% (`done / total = 17 / 17`)
- **monthly_day_entries**：144 / 144（12 月 x 12 建除日）
- **quote_index_entries**：156（序跋 6 + 月日表 144 + 附录 6）
- **quote_policy**：每条短引来自本地 `fulltext.md` exact-match，压缩后不超过 80 字。

## Files

| file | status | role |
|---|---|---|
| index.md | done | 入口索引、路由、冲突裁判、文化警示 |
| chapter-map.md | done | 17 个章节条目，全部 `digest_status=done` |
| terms.md | done | 术语抽取，供择日体系词表使用 |
| rules.md | done | 10 条 D2 规则 + 月日表调用约束 |
| procedures.md | done | 工具调用流程与输出约束 |
| quote-index.md | done | 156 条 exact-match 原文短引 |
| monthly-day-table.md | done | 144 条逐月逐日建除宜忌表 |
| validation.md | done | 本文件 |

## Ready Candidate Decision

- **D2 ready_candidate**：yes
- **reason**：本地 normalized source 为 ready；章节覆盖 17/17；逐日正文 144/144 已抽取；quote-index 可 exact-match；无 pending / unavailable 章节。
- **scope_limit**：ready_candidate 只表示可作为 skill reference pack 的材料层，不表示官方择日标准，也不表示可直接下现实吉凶判断。

## Remaining Verification

1. 对 Wikimedia / 国图影印逐页校勘，确认维基文库文本无漏行、错字、错月。
2. 与《董公选秘訣要覧》《董公诹吉新书》等同源异书比对异文。
3. 与《协纪辨方书》《星历考原》交叉校验神煞起例与宜忌冲突。
4. 对 `monthly-day-table.md` 的 recommended / avoid / risk 字段做人工复核，避免关键词抽取过粗。

## Output Safety

- 所有凶验语必须重写为“原书列为某类避忌 / 民间通书认为不宜”。
- 必须附 caveat：“文化参考，非事实判断”。
- 具体日期换算不得手算，必须调用 `mingli-master.selection.v1`。

## last_updated

2026-06-16 (Batch D2)
