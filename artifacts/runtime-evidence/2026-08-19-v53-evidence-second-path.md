# P10-001 Path B：`_semantic_terms` extra-token injection（signed V53，未重签）

> 同刀、只量。未改 selector / FastAPI / hepan / 签名树。未跑 `release_deploy.py`。P10-001 仍 `IN_PROGRESS`。
>
> 本文件是 **新文件**，不覆盖 `2026-08-19-v53-core-signed-diff.md` / `.py`。
> Path A 已在那份主表量过：`tokenize("验证八字核心盘面 career")` 对 `R-01-02` / `R-02-04` / `QR-02-01` 的 CJK ∩ 都是 ∅，但三条都进了 1994 `brief.evidence[]`。这里只交代 **为什么零查询分还能进**。

Date: 2026-08-19 (CST / UTC+8).

现行身份仍是 `.runtime/v53-time-check-release` inspector `manifest_sha256=c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`，`source_commit=663543e65ae037843b03dca1dec9486293affc9d`，220 files。core HEAD 同 commit。

## 两条检索路径

| 路径 | 名称 | 签名位点 | 1994 career 实际 query tokens |
|---|---|---|---|
| **Path A** | query + dimension BM25 | `search_bm25.tokenize` | `tokenize("验证八字核心盘面 career")` → `career` + `验 证 八 字 核 心 盘 面 验证 证八 八字 字核 核心 心盘 盘面`（16） |
| **Path B** | `_semantic_terms` extra-token injection | **`reading_evidence_bundle.py:_semantic_terms`**（signed `.runtime/v53-time-check-release/scripts/reading_evidence_bundle.py:96`，调用点 L410） | `tokenize(" ".join(_semantic_terms(goal, plan, fact_index)))`：Path A 那 16 个 **再加** 1994 `fact_index` 盘面投影注入的 extra tokens |

选择器真正拿去打 `_rank_rules` 的是 Path B，不是 Path A。`_rank_rules`（同文件 L165）对每个 pack 做 `search_bm25.bm25(tokenize(" ".join(terms)), docs)`，`score>0` 才留下，再截 `MAX_RULES_PER_PACK=2`。

`_semantic_terms` 往 terms 里追加（L107–153）：

1. `goal.evidence_questions`（1994 = `验证八字核心盘面`）
2. `plan.question_dimensions` / `requested_dimensions`（1994 = `career`）
3. **每个** `fact_index` 的 `fact_id`（`fact:{path}`）← 本盘的额外注入
4. `/named_patterns/` 或 `/board_predicates/` 叶子 `id`/`name`（本盘 **0**）
5. `plan.semantic_term_projections` 命中的盘面叶子值（`BaziProvider.SOURCE_ROUTE`，signed `providers.py:2749`，**没有** projections，本盘 []）

1994 非 fact 的 terms 只有 `['验证八字核心盘面', 'career']`，与 Path A 同源。额外 CJK **全部**来自第 3 步：盘面 dict key 写进 path，再被 `tokenize` 拆成单字/二字。`tokenize` 先抽全部 CJK 再做相邻 bigram，空格不切断，所以还会出现跨 fact_id 的 `面土` `土木` `木火` 等。

## 1994 盘面注入的 extra tokens（实测）

`fact_index_n=1225`，`semantic_terms_n=1227`，Path B 全量 token 9579 / unique 414，比 Path A 多 **398** 个 unique。其中 extra CJK：

`土 木 水 火 金 偏 印 正 官 财 食 神` + 跨项 bigram `面土 土木 木水 水火 火金 金土 木火 金偏 偏印 印正 正印 正官 官正 正财 财食 食神 神土`

来源（canonical 盘面叶子，domain_work 副本略）：

| extra token | 1994 fact_index path（盘面投影） |
|---|---|
| 土 / 木 / 水 / 火 / 金 | `/chart_facts/output/element_inventory/hidden_stem_occurrence_counts/{五行}`，`visible_stem_branch_counts/{五行}`，`interpretive_candidates/strength/all_element_occurrences/{五行}`，`reasoning_tools/strength_evidence/output/seasonal_state_table/{五行}` |
| 正 | `.../domain_work/output/role_counts/正印` `正官` `正财` |
| 神 | `.../domain_work/output/role_counts/食神` |
| 偏 印 官 财 食 + 十神 bigram | 同上 `role_counts/{偏印,正印,正官,正财,食神}` |

`木火` 不是单条 path 的 token，是 CJK 流把 `木` 和后面的 `火` 拼成的跨项 bigram；它刚好打中 `R-01-02` 引文「木→火」。

## 焦点表：R-01-02 / R-02-04 / QR-02-01（+ DR-01-01 对照）

BM25 按选择器同式：本盘 `source_conditioned_patterns` 里 `predicate_matched*` 的规则，**按 pack 分组** 计分。`in 1994 evidence[]` 以既有 `/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json` 为准，未重跑 prepare。

| rule_id | Path A overlap | Path A BM25 | Path B overlap | Path B BM25 | in 1994 `evidence[]` | why |
|---|---|---:|---|---:|---|---|
| `bazi/sanming-tonghui#R-01-02` | ∅ | 0.000000 | `土 木 木火 水 火 金` | **47.057852** | **YES** | 引文是五行生克（木→火→土→金→水）。Path A 的「验证八字核心盘面 career」一个字都打不中；Path B 把盘面五行 key 注进 query，pack 内分 > 0，和 `R-02-04` 一起占满 sanming 的 2 席。 |
| `bazi/sanming-tonghui#R-02-04` | ∅ | 0.000000 | `神` | **0.657969** | **YES** | 引文「扶抑用神」。Path A 无「神」；Path B 从 `role_counts/食神` 注入 `神`，分 > 0，进 evidence。 |
| `bazi/qiongtong-baojian#QR-02-01` | ∅ | 0.000000 | `土 正 水 火` | **17.505201** | **YES** | 引文「正月丙火…壬水…土重」。Path A 无这些字；Path B 注入 `正`（正印/正官/正财）+ `土水火`，分 > 0，和已能打中「盘」的 `QTB-M01` 一起占满 qiongtong 的 2 席。 |
| `bazi/ditiansui-chanwei#DR-01-01` | ∅ | 0.000000 | ∅ | **0.000000** | **NO** | 见下一节。 |

1994 `brief.evidence[]` 5 条仍是：`R-01-02` `R-02-04` `ZPR-01` `QR-02-01` `QTB-M01`。无 DR-01-01。

## 为什么 DR-01-01 连 Path B 也过不了（career）

DR-01-01 引文（签名 `_rule_text`）：

`滴天髓阐微 tongshen/01-tiandao 三元一统 … 干为天元，支为地元，支中所藏为人元；论命三元一统，以日干为我，旁参支藏。`

Path A 的 career 查询 token 与它无交集（overview 才能靠「命」打中，已在 signed-diff 主表）。Path B 多注入的 extra CJK 是 **五行 / 十神 key**（`土 木 水 火 金 偏 印 正 官 财 食 神` 及跨项 bigram）。这段三元一统引文里 **同样没有** 这些字：没有五行，没有十神，也没有「命/本/四/柱」。所以 Path B overlap 仍是 ∅，pack 内 BM25 仍是 0。`ditiansui-chanwei` 本盘 matched 只有这一条，`_rank_rules` 整包空，不进 `brief.evidence[]`。

这不是「没进 predicate」——1994 SCP 里它是 `predicate_matched_not_verdict`。是两条检索路径都打不中 career 查询+盘面投影。

## 可复跑命令（一条）

cwd=`/Volumes/Lexar/code/mingli_web`：

```bash
python3 -B artifacts/runtime-evidence/2026-08-19-v53-evidence-second-path.py
```

只读输入：1994 `prepared/000001.json` + 既有 `prepare.stdout.json` + 签名 `evidence-rules.jsonl` / `search_bm25` / `_semantic_terms`。不重跑 prepare，不重签。

原始 stdout：`artifacts/runtime-evidence/2026-08-19-v53-evidence-second-path.stdout.txt`。

## 命令 stdout（2026-08-19 CST，原样粘贴）

```
=== IDENTITY ===
core_head=663543e65ae037843b03dca1dec9486293affc9d
core_subject=fix(runtime): preserve bazi pattern audit
core_dirty_count=5
signed_manifest_sha256=c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b
signed_source_commit=663543e65ae037843b03dca1dec9486293affc9d
signed_n_files=220
path_b_name=_semantic_terms extra-token injection
path_b_file=/.runtime/v53-time-check-release/scripts/reading_evidence_bundle.py:_semantic_terms
path_b_cite=reading_evidence_bundle.py:96:_semantic_terms
=== PATHS ===
path_a_joined='验证八字核心盘面 career'
path_a_tokens=['career', '验', '证', '八', '字', '核', '心', '盘', '面', '验证', '证八', '八字', '字核', '核心', '心盘', '盘面']
path_a_token_n=16
goal_evidence_questions=['验证八字核心盘面']
goal_question_dimensions=['career']
plan_semantic_term_projections=[]
fact_index_n=1225
semantic_terms_n=1227
semantic_terms_non_fact=['验证八字核心盘面', 'career']
named_patterns_or_board_predicates_n=0
path_b_token_n=9579
path_b_unique_n=414
path_b_extra_unique_n=398
path_b_extra_cjk=['土', '木', '水', '火', '金', '偏', '印', '正', '官', '财', '食', '神', '面土', '土木', '木水', '水火', '火金', '金土', '木火', '金偏', '偏印', '印正', '正印', '正官', '官正', '正财', '财食', '食神', '神土']
=== 1994_PREPARE ===
prepared=/tmp/mingli-oneshot-v53-time-check-20260819/503de6c92e75c6f742aa637c2ec71dcc367b597bb69f1280fe1aefe1d58a384b/readings-v51/readings/9ecec297703f4b8f87d1373010f1ab7a/prepared/000001.json
prepare_stdout=/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json
scp_matched_n=6
scp_matched_ids=['bazi/ditiansui-chanwei#DR-01-01', 'bazi/qiongtong-baojian#QR-02-01', 'bazi/qiongtong-baojian#QTB-M01', 'bazi/sanming-tonghui#R-01-02', 'bazi/sanming-tonghui#R-02-04', 'bazi/ziping-zhenquan#ZPR-01']
evidence_n=5
evidence_ids=['bazi/sanming-tonghui#R-01-02', 'bazi/sanming-tonghui#R-02-04', 'bazi/ziping-zhenquan#ZPR-01', 'bazi/qiongtong-baojian#QR-02-01', 'bazi/qiongtong-baojian#QTB-M01']
=== FOCUS_TABLE ===
rule_id	path_a_overlap	path_a_bm25	path_b_overlap	path_b_bm25	in_1994_evidence
bazi/sanming-tonghui#R-01-02	∅	0.000000	土 木 木火 水 火 金	47.057852	YES
bazi/sanming-tonghui#R-02-04	∅	0.000000	神	0.657969	YES
bazi/qiongtong-baojian#QR-02-01	∅	0.000000	土 正 水 火	17.505201	YES
bazi/ditiansui-chanwei#DR-01-01	∅	0.000000	∅	0.000000	NO
=== CONTRIBUTING_FACT_PATHS ===
token=土 n=8
  /chart_facts/output/element_inventory/hidden_stem_occurrence_counts/土
  /chart_facts/output/element_inventory/visible_stem_branch_counts/土
  /chart_facts/output/interpretive_candidates/reasoning_tools/strength_evidence/output/seasonal_state_table/土
  /chart_facts/output/interpretive_candidates/strength/all_element_occurrences/土
token=木 n=8
  /chart_facts/output/element_inventory/hidden_stem_occurrence_counts/木
  /chart_facts/output/element_inventory/visible_stem_branch_counts/木
  /chart_facts/output/interpretive_candidates/reasoning_tools/strength_evidence/output/seasonal_state_table/木
  /chart_facts/output/interpretive_candidates/strength/all_element_occurrences/木
token=水 n=5
  /chart_facts/output/element_inventory/hidden_stem_occurrence_counts/水
  /chart_facts/output/interpretive_candidates/reasoning_tools/strength_evidence/output/seasonal_state_table/水
  /chart_facts/output/interpretive_candidates/strength/all_element_occurrences/水
token=火 n=8
  /chart_facts/output/element_inventory/hidden_stem_occurrence_counts/火
  /chart_facts/output/element_inventory/visible_stem_branch_counts/火
  /chart_facts/output/interpretive_candidates/reasoning_tools/strength_evidence/output/seasonal_state_table/火
  /chart_facts/output/interpretive_candidates/strength/all_element_occurrences/火
token=金 n=8
  /chart_facts/output/element_inventory/hidden_stem_occurrence_counts/金
  /chart_facts/output/element_inventory/visible_stem_branch_counts/金
  /chart_facts/output/interpretive_candidates/reasoning_tools/strength_evidence/output/seasonal_state_table/金
  /chart_facts/output/interpretive_candidates/strength/all_element_occurrences/金
token=正 n=3
  /chart_facts/output/interpretive_candidates/reasoning_tools/domain_work/output/role_counts/正印
  /chart_facts/output/interpretive_candidates/reasoning_tools/domain_work/output/role_counts/正官
  /chart_facts/output/interpretive_candidates/reasoning_tools/domain_work/output/role_counts/正财
token=神 n=1
  /chart_facts/output/interpretive_candidates/reasoning_tools/domain_work/output/role_counts/食神
=== WHY_DR_01_01 ===
dr_rule_text=滴天髓阐微 tongshen/01-tiandao 三元一统 tongshen/01-tiandao 基础理论 干为天元，支为地元，支中所藏为人元；论命三元一统，以日干为我，旁参支藏。
dr_path_a_overlap=∅
dr_path_b_overlap=∅
dr_path_b_bm25=0.000000
dr_reason=injected extra CJK are 五行/十神 keys (土 木 水 火 金 偏 印 正 官 财 食 神 + cross-term bigrams); DR-01-01 quote has none of those tokens, so pack BM25 stays 0 and _rank_rules drops the only ditiansui-chanwei match
```

未改 selector / FastAPI / hepan / 签名树，未跑 `release_deploy.py`。P10-001 仍 `IN_PROGRESS`。
