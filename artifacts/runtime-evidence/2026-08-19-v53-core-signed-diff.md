# P10-001 tightened：career BM25 drop list（signed V53，未重签）

> **验收口径（项目经理已收下，勿扩集合）：** career never-enters 只有 `bazi/ditiansui-chanwei#DR-01-01`。判定以两盘 career prepare 的 `source_conditioned_patterns`（predicate_matched）为准，不是对全部 `runtime_active` 的 rematch。`YR-M01` 是 rematch 多出、**不在** prepare 的 6 条 SCP，不并进 never-enters。query-token BM25==0 不等于进不了 `brief.evidence[]`。


Date: 2026-08-19 (CST / UTC+8). **Same knife, no resign.** 未改 selector / FastAPI / hepan / 签名树。P10-001 仍 `IN_PROGRESS`。

现行身份仍是 `.runtime/v53-time-check-release` inspector `manifest_sha256=c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`，`source_commit=663543e65ae037843b03dca1dec9486293affc9d`，220 files。core HEAD 同 commit，dirty 5（只量、未并入制品）。

主材料：签名 `search_bm25.tokenize` / 同式 BM25 + 既有 1994/1992 career `prepare.stdout.json`。查询固定为 `tokenize("验证八字核心盘面 career")`。对照列：乙酉 overview `tokenize("请排出本命四柱。 overview")`。

## 可复跑命令

cwd=`/Volumes/Lexar/code/mingli_web`：

```bash
python3 -B artifacts/runtime-evidence/2026-08-19-v53-core-signed-diff.py
```

输入（只读，未重跑 prepare）：

- `/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json`（1994 career）
- `/tmp/mingli-oneshot-v53-fixture2-20260819/out/prepare.stdout.json`（1992 career）
- `.runtime/oneshot-20260819-claim-unit/prepare-out.json`（乙酉 overview，对照）
- 签名规则：`.runtime/v53-time-check-release/references/index/evidence-rules.jsonl`
- rematch 用盘上 `prepared/000001.json` 的 `chart_facts` + 签名 `match_rule`

原始 stdout：`artifacts/runtime-evidence/2026-08-19-v53-core-signed-diff.stdout.txt`。

## Totals（实测）

| 项 | 数 |
|---|---:|
| runtime_active bazi | 24 |
| 有谓词、可进 selector | 24 |
| 1994/1992 prepare `source_conditioned_patterns`（`predicate_matched_not_verdict`） | 6 / 6 |
| rematch 全 `runtime_active`（1994 / 1992） | 7 / 7 |
| rematch 比 prepare 多出 | `bazi/yuanhai-ziping#YR-M01`（两盘同） |
| 1994/1992 `brief.evidence[]` | 5 / 5 |
| 查询 CJK 与规则文本交集为空（制品 24 条里） | 19 |
| career 盘上 **matched 且未进** `brief.evidence[]` | **2** |

career 查询 CJK：`八 八字 字 字核 心 心盘 核 核心 盘 盘面 证 证八 面 验 验证`（另有 ascii `career`）。overview CJK：`出 出本 命 命四 四 四柱 排 排出 本 本命 柱 请 请排`。

## 主表：career 盘上每条 `runtime_active` ∩ `predicate_matched`

扫描口径：签名 `match_rule` 对盘上 `chart_facts` 重放（= prepare 6 条 + rematch 多出的 `YR-M01`）。BM25 在**本盘同 pack 的 matched 集合**内用签名公式计分（`score>0` 才会被 `_rank_rules` 留下）。`in_brief.evidence[]` 以既有 prepare stdout 为准。

### 1994-04-30 career（query=`验证八字核心盘面`，dims=`career`）

| rule_id | pack | career CJK ∩ | career BM25 | 进 `brief.evidence[]` | overview CJK ∩ |
|---|---|---|---:|---|---|
| `bazi/ditiansui-chanwei#DR-01-01` | ditiansui-chanwei | ∅ | 0.000000 | **NO** | `命` |
| `bazi/qiongtong-baojian#QR-02-01` | qiongtong-baojian | ∅ | 0.000000 | YES | ∅ |
| `bazi/qiongtong-baojian#QTB-M01` | qiongtong-baojian | `盘` | 0.706392 | YES | `四 四柱 柱` |
| `bazi/sanming-tonghui#R-01-02` | sanming-tonghui | ∅ | 0.000000 | YES | `命` |
| `bazi/sanming-tonghui#R-02-04` | sanming-tonghui | ∅ | 0.000000 | YES | `命 本` |
| `bazi/yuanhai-ziping#YR-M01` | yuanhai-ziping | ∅ | 0.000000 | **NO** | `四 四柱 本 柱` |
| `bazi/ziping-zhenquan#ZPR-01` | ziping-zhenquan | `八 八字 字` | 0.863046 | YES | ∅ |

1994 `brief.evidence[]` 5 条：`R-01-02` `R-02-04` `ZPR-01` `QR-02-01` `QTB-M01`。无 DR-01-01，无 YR-M01。

### 1992-08-17 career（同 query / career）

| rule_id | pack | career CJK ∩ | career BM25 | 进 `brief.evidence[]` | overview CJK ∩ |
|---|---|---|---:|---|---|
| `bazi/ditiansui-chanwei#DR-01-01` | ditiansui-chanwei | ∅ | 0.000000 | **NO** | `命` |
| `bazi/qiongtong-baojian#QR-01-07` | qiongtong-baojian | `八` | 0.673437 | YES | ∅ |
| `bazi/qiongtong-baojian#QTB-M01` | qiongtong-baojian | `盘` | 0.714046 | YES | `四 四柱 柱` |
| `bazi/sanming-tonghui#R-01-02` | sanming-tonghui | ∅ | 0.000000 | YES | `命` |
| `bazi/sanming-tonghui#R-02-04` | sanming-tonghui | ∅ | 0.000000 | YES | `命 本` |
| `bazi/yuanhai-ziping#YR-M01` | yuanhai-ziping | ∅ | 0.000000 | **NO** | `四 四柱 本 柱` |
| `bazi/ziping-zhenquan#ZPR-01` | ziping-zhenquan | `八 八字 字` | 0.863046 | YES | ∅ |

1992 `brief.evidence[]` 5 条：`R-01-02` `R-02-04` `ZPR-01` `QR-01-07` `QTB-M01`。无 DR-01-01，无 YR-M01。调候规则从 `QR-02-01` 换成 `QR-01-07`（`八` 能打中 career）。

## 集合「制品里有、career 永远进不了 evidence[]」

**成员（本刀实证，2 条；DR-01-01 不是唯一）：**

1. `bazi/ditiansui-chanwei#DR-01-01` — 制品有、`runtime_active`、两盘 prepare pattern 均 `predicate_matched_not_verdict`；career CJK ∩ = ∅、pack 内 BM25 = 0；1994/1992 `brief.evidence[]` 均无。乙酉 overview 因重叠「命」进了 evidence（score≈0.287682）。
2. `bazi/yuanhai-ziping#YR-M01` — 制品有、`runtime_active`；签名 `match_rule` 两盘都 matched，但 **不在** prepare 的 6 条 `source_conditioned_patterns`；career CJK ∩ = ∅、BM25 = 0；1994/1992 evidence 均无。乙酉 overview 因「四/四柱/本/柱」进了 evidence。

两包当时 matched 各只有这一条，查询零分 = 整包空，`_rank_rules` 不选。不要改 FastAPI 补造。

**不要把下面 19 条查询零重叠表误标成「永远进不了 evidence[]」。** 其中 `R-01-02` / `R-02-04` / `QR-02-01` 在 1994 career **已经进了** `brief.evidence[]`：选择器 `_semantic_terms` 还会注入 fact_id / 盘面投影，查询零分不是充分条件。19 条只证明「`验证八字核心盘面`+`career` 这组 token **本身**打不中」：

`DR-01-01`, `QR-01-01`, `QR-01-02`, `QR-01-05`, `QR-02-01`, `QR-02-02`, `QR-02-04`, `QR-03-01`, `QR-03-04`, `QR-03-06`, `QR-03-07`, `QR-04-01`, `QR-04-02`, `QR-05-02`, `QR-05-04`, `QR-05-08`, `R-01-02`, `R-02-04`, `YR-M01`。

查询能打中（career CJK 非空）的制品规则只有 5 条：`QR-01-03` `QR-01-07` `QR-04-07` `QTB-M01` `ZPR-01`。

## 乙酉 overview 对照（`请排出本命四柱。` / overview）

`brief.evidence[]` 6 条：`R-01-02` `R-02-04` **`YR-M01`** **`DR-01-01`** `QR-02-02` `QTB-M01`。同套规则、换查询，DR-01-01 与 YR-M01 都能进。ZPR-01 本盘 pattern 命中但 overview 查询 CJK ∩ = ∅，**未**进 evidence（随查询，不是「不在制品」）。

## Attachment — Claim Unit 四行

| claim | 源码有 | 制品有 | 三盘是否出现 |
|---|---|---|---|
| month-order | 有 | 有 | 1994 有 / 1992 有 / 乙酉 有 |
| ziping | 有 | 有 | 1994 有 / 1992 有 / 乙酉 **无（随盘）** |
| tiaohou | 有 | 有 | 1994 有 / 1992 有 / 乙酉 有 |
| day-master-root | 有 | **无** | **三盘皆无** |

源码 4：`month-order-state-v1` / `ziping-pattern-entry-v1` / `tiaohou-priority-v1` / `day-master-root-support-v1`。制品 3（无 root-support）。`claim_unit_id` 不是 CHECKLIST 准入。

## 命令 stdout（2026-08-19 CST，原样粘贴）

```
=== IDENTITY ===
core_head=663543e65ae037843b03dca1dec9486293affc9d
core_subject=fix(runtime): preserve bazi pattern audit
core_dirty_count=5
signed_manifest_sha256=c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b
signed_source_commit=663543e65ae037843b03dca1dec9486293affc9d
signed_n_files=220
runtime_active_bazi=24
eligible_source_conditioned=24
career_joined='验证八字核心盘面 career'
career_tokens=['career', '验', '证', '八', '字', '核', '心', '盘', '面', '验证', '证八', '八字', '字核', '核心', '心盘', '盘面']
career_cjk=['八', '八字', '字', '字核', '心', '心盘', '核', '核心', '盘', '盘面', '证', '证八', '面', '验', '验证']
overview_joined='请排出本命四柱。 overview'
overview_tokens=['overview', '请', '排', '出', '本', '命', '四', '柱', '请排', '排出', '出本', '本命', '命四', '四柱']
overview_cjk=['出', '出本', '命', '命四', '四', '四柱', '排', '排出', '本', '本命', '柱', '请', '请排']
=== CAREER_NEVER_EVIDENCE (制品里有、career 永远进不了 evidence[]) ===
never_count=19
never_ids=
  bazi/ditiansui-chanwei#DR-01-01	bazi/ditiansui-chanwei	career_cjk=∅	career_bm25=0.000000	overview_cjk=['命']	overview_bm25=2.238598
  bazi/qiongtong-baojian#QR-01-01	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=∅	overview_bm25=0.000000
  bazi/qiongtong-baojian#QR-01-02	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=['四']	overview_bm25=1.241730
  bazi/qiongtong-baojian#QR-01-05	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=∅	overview_bm25=0.000000
  bazi/qiongtong-baojian#QR-02-01	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=∅	overview_bm25=0.000000
  bazi/qiongtong-baojian#QR-02-02	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=['四']	overview_bm25=1.313168
  bazi/qiongtong-baojian#QR-02-04	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=∅	overview_bm25=0.000000
  bazi/qiongtong-baojian#QR-03-01	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=∅	overview_bm25=0.000000
  bazi/qiongtong-baojian#QR-03-04	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=∅	overview_bm25=0.000000
  bazi/qiongtong-baojian#QR-03-06	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=∅	overview_bm25=0.000000
  bazi/qiongtong-baojian#QR-03-07	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=∅	overview_bm25=0.000000
  bazi/qiongtong-baojian#QR-04-01	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=∅	overview_bm25=0.000000
  bazi/qiongtong-baojian#QR-04-02	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=['四']	overview_bm25=1.362147
  bazi/qiongtong-baojian#QR-05-02	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=['四']	overview_bm25=1.313168
  bazi/qiongtong-baojian#QR-05-04	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=∅	overview_bm25=0.000000
  bazi/qiongtong-baojian#QR-05-08	bazi/qiongtong-baojian	career_cjk=∅	career_bm25=0.000000	overview_cjk=∅	overview_bm25=0.000000
  bazi/sanming-tonghui#R-01-02	bazi/sanming-tonghui	career_cjk=∅	career_bm25=0.000000	overview_cjk=['命']	overview_bm25=3.076188
  bazi/sanming-tonghui#R-02-04	bazi/sanming-tonghui	career_cjk=∅	career_bm25=0.000000	overview_cjk=['命', '本']	overview_bm25=5.258599
  bazi/yuanhai-ziping#YR-M01	bazi/yuanhai-ziping	career_cjk=∅	career_bm25=0.000000	overview_cjk=['四', '四柱', '本', '柱']	overview_bm25=10.954831
=== CHART 1994-career ===
prepare=/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json
facts=28
evidence_n=5
evidence_ids=['bazi/sanming-tonghui#R-01-02', 'bazi/sanming-tonghui#R-02-04', 'bazi/ziping-zhenquan#ZPR-01', 'bazi/qiongtong-baojian#QR-02-01', 'bazi/qiongtong-baojian#QTB-M01']
findings_n=4
claim_units=['bazi.month-order-state-v1', 'bazi.ziping-pattern-entry-v1', 'bazi.tiaohou-priority-v1']
predicate_matched_n=6
predicate_matched_ids=['bazi/ditiansui-chanwei#DR-01-01', 'bazi/qiongtong-baojian#QR-02-01', 'bazi/qiongtong-baojian#QTB-M01', 'bazi/sanming-tonghui#R-01-02', 'bazi/sanming-tonghui#R-02-04', 'bazi/ziping-zhenquan#ZPR-01']
rematch_runtime_active_predicate_matched_n=7
rematch_extra_vs_prepare_patterns=['bazi/yuanhai-ziping#YR-M01']
rematch_missing_vs_prepare_patterns=[]
table_header=rule_id	pack	career_cjk	career_bm25	in_brief_evidence	overview_cjk	overview_bm25
  bazi/ditiansui-chanwei#DR-01-01	bazi/ditiansui-chanwei	∅	0.000000	NO	['命']	0.287682
  bazi/qiongtong-baojian#QR-02-01	bazi/qiongtong-baojian	∅	0.000000	YES	∅	0.000000
  bazi/qiongtong-baojian#QTB-M01	bazi/qiongtong-baojian	['盘']	0.706392	YES	['四', '四柱', '柱']	2.580190
  bazi/sanming-tonghui#R-01-02	bazi/sanming-tonghui	∅	0.000000	YES	['命']	0.270801
  bazi/sanming-tonghui#R-02-04	bazi/sanming-tonghui	∅	0.000000	YES	['命', '本']	0.908847
  bazi/yuanhai-ziping#YR-M01	bazi/yuanhai-ziping	∅	0.000000	NO	['四', '四柱', '本', '柱']	1.274021
  bazi/ziping-zhenquan#ZPR-01	bazi/ziping-zhenquan	['八', '八字', '字']	0.863046	YES	∅	0.000000
career_drop_on_this_chart=['bazi/ditiansui-chanwei#DR-01-01', 'bazi/yuanhai-ziping#YR-M01']
=== CHART 1992-career ===
prepare=/tmp/mingli-oneshot-v53-fixture2-20260819/out/prepare.stdout.json
facts=28
evidence_n=5
evidence_ids=['bazi/sanming-tonghui#R-01-02', 'bazi/sanming-tonghui#R-02-04', 'bazi/ziping-zhenquan#ZPR-01', 'bazi/qiongtong-baojian#QR-01-07', 'bazi/qiongtong-baojian#QTB-M01']
findings_n=4
claim_units=['bazi.month-order-state-v1', 'bazi.ziping-pattern-entry-v1', 'bazi.tiaohou-priority-v1']
predicate_matched_n=6
predicate_matched_ids=['bazi/ditiansui-chanwei#DR-01-01', 'bazi/qiongtong-baojian#QR-01-07', 'bazi/qiongtong-baojian#QTB-M01', 'bazi/sanming-tonghui#R-01-02', 'bazi/sanming-tonghui#R-02-04', 'bazi/ziping-zhenquan#ZPR-01']
rematch_runtime_active_predicate_matched_n=7
rematch_extra_vs_prepare_patterns=['bazi/yuanhai-ziping#YR-M01']
rematch_missing_vs_prepare_patterns=[]
table_header=rule_id	pack	career_cjk	career_bm25	in_brief_evidence	overview_cjk	overview_bm25
  bazi/ditiansui-chanwei#DR-01-01	bazi/ditiansui-chanwei	∅	0.000000	NO	['命']	0.287682
  bazi/qiongtong-baojian#QR-01-07	bazi/qiongtong-baojian	['八']	0.673437	YES	∅	0.000000
  bazi/qiongtong-baojian#QTB-M01	bazi/qiongtong-baojian	['盘']	0.714046	YES	['四', '四柱', '柱']	2.602432
  bazi/sanming-tonghui#R-01-02	bazi/sanming-tonghui	∅	0.000000	YES	['命']	0.270801
  bazi/sanming-tonghui#R-02-04	bazi/sanming-tonghui	∅	0.000000	YES	['命', '本']	0.908847
  bazi/yuanhai-ziping#YR-M01	bazi/yuanhai-ziping	∅	0.000000	NO	['四', '四柱', '本', '柱']	1.274021
  bazi/ziping-zhenquan#ZPR-01	bazi/ziping-zhenquan	['八', '八字', '字']	0.863046	YES	∅	0.000000
career_drop_on_this_chart=['bazi/ditiansui-chanwei#DR-01-01', 'bazi/yuanhai-ziping#YR-M01']
=== CHART yiyou-overview ===
prepare=/Volumes/Lexar/code/mingli_web/.runtime/oneshot-20260819-claim-unit/prepare-out.json
facts=28
evidence_n=6
evidence_ids=['bazi/sanming-tonghui#R-01-02', 'bazi/sanming-tonghui#R-02-04', 'bazi/yuanhai-ziping#YR-M01', 'bazi/ditiansui-chanwei#DR-01-01', 'bazi/qiongtong-baojian#QR-02-02', 'bazi/qiongtong-baojian#QTB-M01']
findings_n=3
claim_units=['bazi.month-order-state-v1', 'bazi.tiaohou-priority-v1']
predicate_matched_n=6
predicate_matched_ids=['bazi/ditiansui-chanwei#DR-01-01', 'bazi/qiongtong-baojian#QR-02-02', 'bazi/qiongtong-baojian#QTB-M01', 'bazi/sanming-tonghui#R-01-02', 'bazi/sanming-tonghui#R-02-04', 'bazi/ziping-zhenquan#ZPR-01']
=== CLAIM_UNITS ===
core=['bazi.month-order-state-v1', 'bazi.ziping-pattern-entry-v1', 'bazi.tiaohou-priority-v1', 'bazi.day-master-root-support-v1']
signed=['bazi.month-order-state-v1', 'bazi.ziping-pattern-entry-v1', 'bazi.tiaohou-priority-v1']
  month-order	有	有	有	有	有
  ziping	有	有	有	有	无	随盘
  tiaohou	有	有	有	有	有
  day-master-root	有	无	无	无	无	三盘皆无
```

未改 selector / FastAPI / hepan / 签名树，未跑 `release_deploy.py`。P10-001 仍 `IN_PROGRESS`。
