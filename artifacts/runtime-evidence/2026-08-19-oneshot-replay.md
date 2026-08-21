# P10-001 八字 one-shot 复跑清单（2026-08-19）

给测试工程师。只复跑现行签名 V53，不重签、不改 config。`claim_unit_id` 是 runtime 输出，**不是 CHECKLIST 准入**。

机器：Mac mini + Lexar。cwd：`/Volumes/Lexar/code/mingli_web`。三盘 store 仍在，命令取自盘上 JSON。

## 公共环境

```bash
RELEASE=/Volumes/Lexar/code/mingli_web/.runtime/v53-time-check-release
export MINGLI_PYTHON=/Users/yuhanglin/.local/share/mingli-master/venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
# isolated MINGLI_STORE_ROOT per run
export MINGLI_STORE_ROOT=/tmp/mingli-oneshot-replay-$USER-$(date +%Y%m%d-%H%M%S)

printf '%s\n' '{"kind":"describe"}' | "$RELEASE/scripts/run_reading_transaction.sh"
# expect kind=described，digest 3403992cb31aebea19e69ec3b1280a5ef02718c5f9ca3e3f94448ef7b039facc

"$RELEASE/scripts/run_reading_transaction.sh" < prepare.command.json
# expect kind=prepared

"$RELEASE/scripts/run_reading_transaction.sh" < complete.command.json
# expect kind=accepted；terminal=true；completion_committed=true
```

`complete.command.json` 的 `state_token` **必须来自当次 prepare**。下面历史 token 只证明当时跑通，复跑时不要照抄。

release-bound（对本 prepare 抽出的 evidence 数组，例如 `prepare-evidence.json`）：

```bash
python3 -B /Volumes/Lexar/code/mingli_web/scripts/verify_citation.py \
  --mode release-bound \
  --release-root "$RELEASE" \
  --file <prepare-evidence.json>
```

制品内三个 unit：`month-order-state-v1` / `ziping-pattern-entry-v1` / `tiaohou-priority-v1`。`day-master-root-support-v1` 三盘都不应出现。ziping 随盘。

---

## 夹具 1 — public-core-synthetic / 1994-04-30

Store 仍在：`/tmp/mingli-oneshot-v53-time-check-20260819`（命令取自 `out/prepare.command.json`、`out/complete.command.json`）。

| 字段 | 值 |
|---|---|
| subject_ref | `profile-version:public-core-synthetic` |
| birth / pillars | `1994-04-30T05:55:00+08:00` |
| timezone | `Asia/Shanghai` |
| location | `福建省福州市` |
| gender | `male` |
| time_basis_policy | `local_apparent_solar-v1` |
| zi_hour_policy | `midnight` |
| latitude / longitude | `26.0745` / `119.2965` |
| coordinate_source | `synthetic-fixture` |
| query / object / dimension / horizon | `验证八字核心盘面` / `natal` / `career` / `life` |
| expected prepare kind | `prepared`（当时 facts=28, evidence=5, findings=4） |
| expected complete kind | `accepted` |
| claim units 有 | `bazi.month-order-state-v1`、`bazi.ziping-pattern-entry-v1`、`bazi.tiaohou-priority-v1` |
| claim units 无 | `bazi.day-master-root-support-v1` |
| evidence ids | `sanming-tonghui#R-01-02`、`sanming-tonghui#R-02-04`、`ziping-zhenquan#ZPR-01`、`qiongtong-baojian#QR-02-01`、`qiongtong-baojian#QTB-M01` |
| DR-01-01 | pattern 命中，`evidence_ref` 缺失；不在公共 evidence 数组 |

`out/prepare.command.json`（原文）：

```json
{
  "kind": "prepare",
  "query": "验证八字核心盘面",
  "intent": {
    "subject_refs": ["profile-version:public-core-synthetic"],
    "object_id": "natal",
    "dimension_ids": ["career"],
    "horizon": {"kind_id": "life", "start": null, "end": null},
    "capability_id": "bazi",
    "comparisons": []
  },
  "facts": {
    "profile-version:public-core-synthetic": {
      "birth_datetime_or_four_pillars": "1994-04-30T05:55:00+08:00",
      "timezone": "Asia/Shanghai",
      "location": "福建省福州市",
      "gender": "male",
      "time_basis_policy": "local_apparent_solar-v1",
      "zi_hour_policy": "midnight",
      "longitude": 119.2965,
      "latitude": 26.0745,
      "coordinate_source": "synthetic-fixture"
    }
  },
  "state_token": null,
  "transition": null
}
```

当时 `out/complete.command.json`（token 已失效，只作形态）：

```json
{
  "kind": "complete",
  "state_token": "qI-sXu7BKn_q2jK1updERcfOTj4aesd0dY1fV7xP8XI",
  "public_copy": "出生时间或四柱：1994-04-30T05:55:00+08:00\n\n坐标来源：synthetic-fixture\n\n性别：male"
}
```

---

## 夹具 2 — 乙酉/辛巳/丙午/癸巳

Store 仍在：`/Volumes/Lexar/code/mingli_web/.runtime/oneshot-20260819-claim-unit/`（命令取自 `prepare.json`、`complete.json`）。

| 字段 | 值 |
|---|---|
| subject_ref | `profile-version:claim-unit-yiyou-xinsi` |
| birth / pillars | `["乙酉","辛巳","丙午","癸巳"]` |
| timezone | `Asia/Shanghai` |
| location | `合成测试地点` |
| gender | `male` |
| time_basis_policy | `local_apparent_solar-v1` |
| zi_hour_policy | `midnight` |
| latitude / longitude | `31.0` / `121.0` |
| coordinate_source | `synthetic-fixture` |
| query / object / dimension / horizon | `请排出本命四柱。` / `natal` / `overview` / `life` |
| expected prepare kind | `prepared`（当时 facts=28, evidence=6） |
| expected complete kind | `accepted` |
| claim units 有 | `bazi.month-order-state-v1`、`bazi.tiaohou-priority-v1` |
| claim units 无 | `bazi.ziping-pattern-entry-v1`（本盘 overview 未出，仍在制品）、`bazi.day-master-root-support-v1` |
| evidence ids | `sanming-tonghui#R-01-02`、`sanming-tonghui#R-02-04`、`yuanhai-ziping#YR-M01`、`ditiansui-chanwei#DR-01-01`、`qiongtong-baojian#QR-02-02`、`qiongtong-baojian#QTB-M01` |
| DR-01-01 | 公共 evidence 有；pattern 仍无 `evidence_ref` |

`prepare.json`（原文）：

```json
{
  "kind": "prepare",
  "query": "请排出本命四柱。",
  "intent": {
    "subject_refs": ["profile-version:claim-unit-yiyou-xinsi"],
    "object_id": "natal",
    "dimension_ids": ["overview"],
    "horizon": {"kind_id": "life", "start": null, "end": null},
    "capability_id": "bazi",
    "comparisons": []
  },
  "facts": {
    "profile-version:claim-unit-yiyou-xinsi": {
      "birth_datetime_or_four_pillars": ["乙酉", "辛巳", "丙午", "癸巳"],
      "timezone": "Asia/Shanghai",
      "location": "合成测试地点",
      "gender": "male",
      "time_basis_policy": "local_apparent_solar-v1",
      "zi_hour_policy": "midnight",
      "longitude": 121.0,
      "latitude": 31.0,
      "coordinate_source": "synthetic-fixture"
    }
  },
  "state_token": null,
  "transition": null
}
```

当时 `complete.json`（token 已失效，只作形态）：

```json
{
  "kind": "complete",
  "state_token": "_hpJSgZcSwOdP4hu2YbGvEfOskEYpqzR0nGmycqYeTo",
  "public_copy": "four_pillars：{\"day\":\"丙午\",\"hour\":\"癸巳\",\"month\":\"辛巳\",\"year\":\"乙酉\"}"
}
```

四柱直供：`calendar_normalization.status=unavailable_from_supplied_four_pillars`。

---

## 夹具 3 — 1992-08-17 / answer-bazi-correction

Store 仍在：`/tmp/mingli-oneshot-v53-fixture2-20260819/out/`（命令取自 `prepare.command.json`、`complete.command.json`；身份见 `fixture-identity.json`）。

| 字段 | 值 |
|---|---|
| subject_ref | `subject:synthetic` |
| birth / pillars | `1992-08-17T14:30:00` |
| timezone | `Asia/Shanghai` |
| location | `上海` |
| gender | `female` |
| time_basis_policy | `civil` |
| zi_hour_policy | `midnight` |
| latitude / longitude | `31.2304` / `121.4737` |
| coordinate_source | `synthetic-fixture` |
| query / object / dimension / horizon | `验证八字核心盘面` / `natal` / `career` / `life` |
| expected prepare kind | `prepared`（当时 facts=28, evidence=5） |
| expected complete kind | `accepted` |
| claim units 有 | `bazi.month-order-state-v1`、`bazi.ziping-pattern-entry-v1`、`bazi.tiaohou-priority-v1` |
| claim units 无 | `bazi.day-master-root-support-v1` |
| evidence ids | `sanming-tonghui#R-01-02`、`sanming-tonghui#R-02-04`、`ziping-zhenquan#ZPR-01`、`qiongtong-baojian#QR-01-07`、`qiongtong-baojian#QTB-M01` |
| DR-01-01 | pattern 命中，`evidence_ref` 缺失；不在公共 evidence 数组 |

相对夹具 1：调候规则从 `QR-02-01` 换成 `QR-01-07`；时间口径是 `civil` 不是真太阳时。

`out/prepare.command.json`（原文）：

```json
{
  "kind": "prepare",
  "query": "验证八字核心盘面",
  "intent": {
    "subject_refs": ["subject:synthetic"],
    "object_id": "natal",
    "dimension_ids": ["career"],
    "horizon": {"kind_id": "life", "start": null, "end": null},
    "capability_id": "bazi",
    "comparisons": []
  },
  "facts": {
    "subject:synthetic": {
      "birth_datetime_or_four_pillars": "1992-08-17T14:30:00",
      "timezone": "Asia/Shanghai",
      "location": "上海",
      "gender": "female",
      "time_basis_policy": "civil",
      "zi_hour_policy": "midnight",
      "longitude": 121.4737,
      "latitude": 31.2304,
      "coordinate_source": "synthetic-fixture"
    }
  },
  "state_token": null,
  "transition": null
}
```

当时 `out/complete.command.json`（token 已失效，只作形态）：

```json
{
  "kind": "complete",
  "state_token": "WkVmFNea9T3WHVauedBGhVcDrBacrQVNrjSWLK_oEZA",
  "public_copy": "出生时间或四柱：1992-08-17T14:30:00\n\n坐标来源：synthetic-fixture\n\n性别：female"
}
```

---

不要把 `claim_unit_ids` 写成 CHECKLIST 准入。不要 resign / push / 上传 / 改 backend config。

---

## 夹具 3 补：盘上权威 `answer-bazi-correction` 第二步（必收）

上面夹具 3 已跑的是简化 first-prepare。盘上 `export_v51_answer_cases.py` 的 exact 命令是先 1994 Prepare→Complete，再：

`artifacts/runtime-evidence/2026-08-19-v53-resign-impact/command-answer-bazi-correction-1992-08-17.json`

```json
{
  "kind": "prepare",
  "query": "出生时间更正了，请按更正后的资料重新说主结论。",
  "intent": {
    "subject_refs": ["subject:synthetic"],
    "object_id": "natal",
    "dimension_ids": ["career"],
    "horizon": {"kind_id": "year", "start": null, "end": null},
    "capability_id": "bazi",
    "comparisons": []
  },
  "facts": {
    "subject:synthetic": {
      "birth_datetime": "1992-08-17T14:30:00",
      "birth_datetime_or_four_pillars": "1992-08-17T14:30:00",
      "timezone": "Asia/Shanghai",
      "location": "上海",
      "gender": "female",
      "time_basis_policy": "civil",
      "zi_hour_policy": "midnight",
      "longitude": 121.4737,
      "latitude": 31.2304,
      "coordinate_source": "synthetic-fixture"
    }
  },
  "state_token": "<from first Prepare>",
  "transition": "correct"
}
```

`state_token` 必须来自当次第一轮，不要抄历史 token。第 4 个 unit 仍不应出现。

夹具 1 另锁定：`DR-01-01` 在 `source_conditioned_patterns` 投影上 `evidence_ref=null`（`backend/tests/test_runtime_public_core_process.py`）。
