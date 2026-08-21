---
slug: taiyi-shenshu
file: validation
---

# 太乙金镜式经 — Validation

> D2 evidence-chain validation. 本文件只证明 reference pack 对本地规范化文本的覆盖与可追溯性，不证明太乙术现实有效性。

## Source State

- **manifest**：`sources/manifests/taiyi-shenshu.yaml`
- **normalized_status**：ready
- **normalized_source_path**：`references/fulltext/san-shi/taiyi-shenshu/fulltext.md`
- **source_text_lines**：1199
- **base_text**：《钦定四库全书》本《太乙金镜式经》维基文库整理文本
- **verified_against_image**：false

## D2 Coverage

- **chapter_units_total**：12（四库提要 1 + 序 1 + 正文十卷 10）
- **chapter_units_done**：12
- **chapter_units_partial**：0
- **chapter_units_pending**：0
- **chapter_units_unavailable**：0
- **strict_coverage**：100%
- **quote_index_entries**：173
- **quote_policy**：每条短引来自本地 `fulltext.md` exact-match，压缩后不超过 80 字。

## Ready Candidate Decision

- **D2 ready_candidate**：yes
- **reason**：本地 normalized source 为 ready；十卷正文和序/提要均为 `done`；quote-index 为 exact-match 原文短引；无 pending / unavailable 章节。
- **scope_limit**：ready_candidate 表示材料层可用；年计事实仍须由 V5.1 provider 计算，不允许 LLM 手算，也不允许把兵占、国家占、灾异占作现代事实预测。

## Remaining Verification

1. 对四库影印逐页校勘维基文库文本，尤其异体字、缺字、卷内表格和立成钤。
2. 与《太乙统宗宝鉴》《御制太乙》《景祐太乙福应集要》对比后世口径差异。
3. 持续增加不同版本的独立影印校勘，不改变已声明的 profile 边界。
4. 卷四、卷九、卷十的国家/兵占内容保持在非计算范围，禁止由固定话术模板代替基于最新问题的复核。

## Output Safety

- 古代国家占法、兵占、灾异占只能说“原书载某法 / 某类占”，不得作现实预测。
- 必须附 caveat：“文化参考，非事实判断”。
- 年计起局、局数、太乙所在、五将和卷五诸神位必须由 V5.1 确定性 provider 计算；七术不在本发布计算范围。

## last_updated

2026-06-16 (Batch D2)
