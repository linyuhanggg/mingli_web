# P10-013 解梦 / 姓名 只读对照

日期：2026-08-19
准入：签名 V53 inspector `c451de5e…` / source `663543e…` / 220 文件
范围：`.runtime/v53-time-check-release` vs `core/mingli-master`
约束：不改仓库合同、不覆盖 `.runtime`、不 resign、不发明 CU、不把 V52 关系混进 V53。
`xingming` 是七政四余（P10-003），不是姓名学。

## 复跑

```bash
python3 /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-dream-name-golden.py
```

## 三个问题

1. **签名制品里有什么？** 没有解梦 / 姓名 provider、没有 `dream.*` / `name.*` Claim Unit、没有解梦或姓名学规则包、没有黄金夹具。14 个已签名 provider 里没有 `dream` / `name` / `jiemeng`。`catalog-v1.json` 无命中。`evidence-rules.jsonl` 1328 条扫描命中 0。
2. **工作树有没有未进签名的实现？** 没有。`core/mingli-master` 的 14 个 provider 与制品相同，没有多出的解梦 / 姓名 provider 或 CU。`references/matrices/shensha-name-disambiguation.yaml` 是神煞名称歧义表，不是姓名学，也不在签名树。前端 `/tools/dream` `/tools/name` 只是诚实空壳（「适配中」），不在算法内核。
3. **现有 brief / evidence 会不会带上？** 不会。没有对应 provider 就不能 prepare；没有规则就不能进 `brief.evidence[]`；没有 CU 就不能进 `brief.findings[]`。已有三盘 prepare（1994 / 乙酉 / 1992）正文扫描命中 0。

## 实跑数字

见同目录 `2026-08-19-v53-dream-name-golden.stdout.txt`。脚本只读，不改签名树。
