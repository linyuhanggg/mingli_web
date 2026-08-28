# 六爻 / 梅花 OSS ChartProvider 候选准入核证

结论：`NO-QUALIFIED-CANDIDATE`。本轮不应创建 Adapter 实施卡；六爻与梅花继续以现有自研机械盘作为迁移期 oracle/golden，但不能把 `SELF-OWNED` 写成永久路线。只有新候选或上游新版本关闭本文列出的证据缺口后，才重开独立 evidence-only 准入卡。

本文件只记录 MING-68 的增量证据，不实现 Adapter、不修改 Golden expected、不安装依赖、不改变 Provider、生产代码、许可证清单或发布配置。机器可读同源记录见 `liuyao-meihua-candidate-admission.json`。

## 基线与裁决边界

- 复核基线：`origin/main@dd9ad426af1619dab7590e2e91ffdbacb7ef1bdd`，tree `cd952da2375244af6b2c0dce658d0590f3483211`。
- MING-65 / PR #46 将六爻、梅花都标为当前 `SELF-OWNED`；含义是“尚无合格候选的临时工程状态”，不是永久自研例外。
- MING-66 / PR #45 要求许可准入与覆盖准入彼此独立；精确版本、官方来源、LICENSE 正文、分发形态和义务必须闭合。它对 `sxtwl 2.0.7` 的一手结论仍是 `HOLD`：sdist 无许可证成员，也没有精确上游 ref 将 BSD-3-Clause 正文绑定到 2.0.7。
- 固定边界仍是：自有 Request Compiler / Time & Policy Normalizer → Runtime Provider → 锁版本且许可清晰的 OSS Chart Engine → 私有 Engine Adapter → 每术 Canonical Facts。第三方 raw 对象不得进入 Backend、Web、LLM、证据或 snapshot 合同。

复核文件及 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `provider-engine-coverage-matrix.json` | `b03660ea08a7a317b013bc385f3890393aba5ee99d6fd3f149de62ace105af88` |
| `license-notice-audit.json` | `f4b860d3778680b39c7a07bcb8a8595ec4ad7d2f32a227fc5f8cde4c862d68d9` |
| `reading_engine/liuyao.py` | `099f50428746467f6bdb1ddc911c1e46f6ba01c1a843f2a342cfcb7d545ca231` |
| `liuyao-v51.yaml` | `c0e36e39191fab1eff941058e49a4660346e0cc68dd2b7340d712dd11ca2d5d6` |
| `reading_engine/meihua.py` | `f57313665de9d7021530fe0c94255fc599791d76088ac21a3226395922ab962b` |
| `meihua-v51.yaml` | `4d791d72356a7b4d63d7f4e4083726611dc1b845d3bb5ce78fdb6efe74ad9a25` |

## 候选准入总览

| 术数 / 候选 | 精确锁定 | 许可 | 机械覆盖 | 维护/分发 | 准入 |
| --- | --- | --- | --- | --- | --- |
| 六爻 `yaomancy/liuyao-engine` | `v0.1.0` → tag object `6763d236…` → commit `562b902e…` | `HOLD` | 装卦主体较全；互卦/错卦/综卦无接口；时间与投掷 provenance 不符合现合同 | 单 tag、无 GitHub Release、PyPI 404 | `HOLD` |
| 梅花 `handsomejustin/meihua-yi` | `v0.1.1` / PyPI `0.1.1` → commit `19760a55…` | 精确包本身 `ALLOW`；Runtime 仍未准入 | 只覆盖时间/铜钱；当前 5 类方法缺 4 类；存在卦名表和静卦确定性失败 | Alpha、两个同日 tag、无后续 source push | `HOLD` |

两个候选都不值得现在进入 Adapter 实施卡。六爻是法律/供应链与必要覆盖未闭合；梅花则在许可之外已经有现有 Golden 可立即击中的机械错误。

## 六爻候选：yaomancy/liuyao-engine 0.1.0

### 精确来源与维护状态

- 官方仓库：<https://github.com/yaomancy/liuyao-engine>
- tag：<https://github.com/yaomancy/liuyao-engine/tree/v0.1.0>
- annotated tag object：`6763d2365e52a1f956b4d069e417e962fce37228`
- commit：[`562b902eb3ec47d4dadb326b6dc98e8ee09b4295`](https://github.com/yaomancy/liuyao-engine/commit/562b902eb3ec47d4dadb326b6dc98e8ee09b4295)
- tree：`48ac5f1738fdcf66743ed368e3d311dbf06b30b3`
- Python `>=3.11`，runtime dependency 为 `sxtwl>=2.0.6`。
- 2026-06-29 创建并完成最后一次 push；截至本次核证为 3 stars、0 open issue、未归档。只有一个 tag，没有 GitHub Release；官方 PyPI JSON `https://pypi.org/pypi/liuyao-engine/json` 返回 404，因此没有可复核的 wheel/sdist 发行单元。

实际接口核对了 `toss` / `toss_line` / `lines_from_tosses` / `CastResult.changed_bits`、`cast_chart` / `find_fushen`、`compute_four_pillars`、`build_reading` 以及 `tests/test_differential.py`。后者以 najia 隔离历法后随机对比 200 个装卦样本，但这不是 mingli 当前 41 qualifying + 11 boundary Canonical Facts 的替代验收。

### 许可证与分发义务

- 根许可证是 Apache-2.0，精确 commit 下 [LICENSE](https://github.com/yaomancy/liuyao-engine/blob/562b902eb3ec47d4dadb326b6dc98e8ee09b4295/LICENSE) SHA-256 为 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`。
- [NOTICE](https://github.com/yaomancy/liuyao-engine/blob/562b902eb3ec47d4dadb326b6dc98e8ee09b4295/NOTICE) SHA-256 为 `5b5231506e4daf9de323e40ea7d6858508d1f68d1e8548a79a0d5462b097cf95`。
- bundled najia MIT 文本 SHA-256 为 `041f69ab8b03575a0229e12ddd886df6452881b31422001a9df0917854cbda8e`；yigram-najia-rules MIT 文本为 `3116e1221a4447b8136fe7b6f2c093f2e1b0c79a80fae4406b3f9f9260e10958`。
- 如分发，须携带 Apache-2.0 正文与适用 NOTICE，保留 attribution / patent / trademark 条款，对修改文件作显著说明；两个 MIT 来源须保留版权、许可和免责正文。

许可结论为 `HOLD`，原因并非 Apache-2.0 本身，而是精确供应链没有闭合：

1. 没有正式 wheel/sdist，只有 tag source；当前无 approved distribution unit。
2. NOTICE 把 `sxtwl` 写成 MIT，与 MING-66 对 2.0.7 的 BSD-3-Clause/HOLD 一手证据冲突。
3. NOTICE 虽列出 najia 和 yigram-najia-rules，却没有锁定复制或派生数据对应的精确上游 commit。
4. 仓库打包了 ctext 来源古籍文本，只写“公有领域/按 ctext terms 署名”，没有精确抓取版本或已审阅的再分发条款。
5. mingli_web 内尚无候选对应的本地 LICENSE/PROVENANCE 路径；MING-68 也无权创建它。

### 覆盖矩阵

| 合同面 | 上游真实支持 | 与当前 Canonical Facts / Policy 的差距 |
| --- | --- | --- |
| 起卦输入 | CSPRNG 三钱随机，或调用方传六组 coin faces | 没有当前 `supplied_complete_cast` 的 6/7/8/9 totals + provenance 合同，也没有 `digital_coin` transaction seed commitment；candidate randomness 不得成为事实源 |
| 卦、六爻 | 64 卦、六爻、八宫、卦型 | 需以全部现有 fixtures 锁卦名、爻序、字段投影；raw dict 不可公开 |
| 动爻、变卦 | 支持 moving map 与 changed chart | 静卦返回 `changed=null`，当前 Canonical Facts 保留与本卦相同的变卦盘；只能作为显式 Adapter normalization |
| 互卦 / 错卦 / 综卦 | tag 源码与测试中均无接口 | 不得声称已覆盖，也不得在浏览器/Backend 临时补算；当前公开合同也未声明这些字段，是否要新增须另行裁决 |
| 纳甲、世应、六亲、六神 | 支持，另含伏神 | 是有价值的 comparator 面，但必须逐个 Canonical Fact 对差分 |
| 旬空、旺衰、关系 | 支持 sxtwl 四柱、旬空、旺衰/关系 helpers | candidate 用固定 UTC offset 且默认 +480；IANA timezone、location、子时政策仍必须由 owned normalizer 先行，不能双算日历 |
| 用神/assessment | 有 candidate 自带字典 | 属于自研政策、古籍证据和裁决层；不在机械引擎替换范围，必须丢弃而非接管 |

### 解锁条件

- 发布或批准一个能绑定上述 commit 的不可变发行单元。
- 纠正并锁定 `sxtwl`、派生数据和古籍 bytes 的完整许可/来源链。
- 用现有合法 fixtures 证明选定京房 profile 在静卦、单动、多动、历法边界上的所有机械事实。
- 先裁决互/错/综是否真的是新 Canonical Facts；若是，由 engine 或另一个被批准的 owned policy 层提供，不能由 Adapter 随意扩写。

## 梅花候选：handsomejustin/meihua-yi 0.1.1

### 精确来源、发行物与维护状态

- 官方仓库：<https://github.com/handsomejustin/meihua-yi>
- tag：<https://github.com/handsomejustin/meihua-yi/tree/v0.1.1>
- commit：[`19760a55814bdd53ceef9f6da34ee030b90ba1a1`](https://github.com/handsomejustin/meihua-yi/commit/19760a55814bdd53ceef9f6da34ee030b90ba1a1)
- tree：`ca01b9ec8bffffc5f5a933058df80b30a38f938d`
- PyPI：<https://pypi.org/project/meihua-yi/0.1.1/>
- `meihua_yi-0.1.1-py3-none-any.whl` SHA-256：`700706626b4d9142d70616c95c330fd4acfa66912893aa083379eeb93b89a6db`
- `meihua_yi-0.1.1.tar.gz` SHA-256：`5d5c3cb9beec101a5895a853e9e688c4f81a4d680f0a17ef90f523c5ff0d12cb`
- Python `>=3.8`；默认无依赖，`lunardate` 是可选 `lunar` extra。
- 2026-05-13 创建并完成最后一次 source push；截至本次核证为 4 stars、1 open issue、未归档。包 classifier 是 Alpha；v0.1.0 与 v0.1.1 均为同日 tag，无 GitHub Release。

实际接口核对了 `qigua_time`、`qigua_coin`、`compute_hexagrams`、`get_gua_name`、`analyze_ti_yong` 以及唯一测试文件 `tests/test_engine.py`。

### 许可证与分发义务

精确 0.1.1 的仓库、wheel 成员 `meihua_yi-0.1.1.dist-info/LICENSE`、sdist 成员 `meihua_yi-0.1.1/LICENSE` 都是同一份 MIT 文本，SHA-256 均为 `025fdb985a7c50a67dd8f795469c2b2962ac452c5afd22c3844cf7611c7d1250`。分发义务是保留版权、MIT permission notice 和免责声明。

因此“精确上游/PyPI 0.1.1 代码与发行物”的许可结论是 `ALLOW`；这不等于 Runtime 准入。若以后启用可选 `lunardate`，还需单独做依赖许可审计；并且正式 Runtime promotion 前仍须建立获批的 mingli_web 本地 LICENSE/PROVENANCE 路径。

### 覆盖矩阵

| 合同面 | 上游真实支持 | 与当前 Canonical Facts / Policy 的差距 |
| --- | --- | --- |
| 时间起卦 | 接受 naive `datetime`；有 `lunardate` 时用农历，没有时静默改用公历月日 | 没有 IANA timezone、location、子时、共享 calendar facts、闰月 provenance；缺依赖时 fail-open 改公式，不能准入 |
| 数字起卦 | 无 | 当前 `supplied_number` + provenance 缺失 |
| 声数 / 观察 / supplied hexagram | 无；铜钱是另一种方法，不能代替 | 当前 3 类显式方法及 provenance 全缺失 |
| 上下卦、本卦、互卦、变卦 | 有 lines/trigrams 计算 | 64 卦名表与自身 `(下卦, 上卦)` 键定义冲突；现有 Golden 可立即击中 |
| 动爻、体用 | 有；体用取第一个动爻 | `compute_hexagrams` 直接访问 `moving_indices[0]`，而 `qigua_coin` 可合法返回空动爻，因此静卦抛 `IndexError`；多动体用也不是当前显式方法合同 |
| 季节旺衰、来源 profile | 只有静态五行关系和“吉凶”字符串 | 无月令旺衰、source-conditioned patterns、dimension facts、evidence-bound adjudication；吉凶字符串必须丢弃 |
| 对外合同 | 未版本化 Python dict 与格式化文本 | raw dict/text 不可成为 Canonical Facts |

首个无需安装即可确认的机械失败：tag 源码声明 `GUA_NAMES` 的 key 是 `(下卦索引, 上卦索引)`，但 `GUA_NAMES[(7,1)]` 写成“天泽履”。`7=乾` 为下卦、`1=兑` 为上卦时，bits `111110` 的正确名应为“泽天夬”。候选的 `test_all_64` 只断言名称不是“未知”，没有逐个断言 64 个正确名称。

第二个确定性失败是静卦：`qigua_coin([7,8,7,8,7,8])` 返回空动爻，随后 `compute_hexagrams` 在 `moving_indices[0]` 处失败。

### 解锁条件

- 以独立、合法表格修正并穷举测试 64 个精确卦名。
- 移除“没有 lunardate 就静默改公历”的 fail-open 行为，改为消费 owned normalizer 产出的日历/方法事实。
- 覆盖当前 `time`、`supplied_number`、`sound_count`、`observation`、`supplied_hexagram` 五种显式方法，不能拿铜钱法冒充缺失入口。
- 定义静卦/多动行为并通过全部现有合法 fixture differential。
- 只有在后续获授权准入卡中，才建立本地 LICENSE/PROVENANCE bundle。

## 最小 synthetic differential 方案

现有自研盘只作为迁移期 oracle/golden；MING-68 不新增或修改 expected。Candidate 只在私有 Adapter shadow mode 运行，比较的是规范化 Canonical Facts，不比较第三方 raw dict、文本或吉凶结论。

### 六爻最小 case

| Case | 来源 / 输入 | 必比事实 |
| --- | --- | --- |
| `LY-STATIC-QIAN` | `liuyao-v51.yaml` `stable-all-yang`；固定 owned calendar + `[7,7,7,7,7,7]` | 本卦、动爻、规范化静态变卦、纳甲、世应、六亲、六神、旬空、伏神 |
| `LY-ONE-MOVING` | `zengshan-02`；辰月戊子日 + `[7,7,7,7,7,9]` | 乾为天、6 爻动、泽天夬、变爻纳甲/六亲及回头/爻关系 |
| `LY-MULTI-MOVING` | `middle-pair`；固定 owned calendar + `[7,8,9,6,7,8]` | 水火既济、动爻 `[3,4]`、泽雷随、全部逐爻 facts |
| `LY-CALENDAR-POLICY` | 立春前、两种子时政策、纽约 DST、历史 offset | candidate 只消费 owned calendar identity；不得让默认 `+480` 或候选日历回写事实 |

### 梅花最小 case

| Case | 来源 / 输入 | 必比事实 / 预期首结果 |
| --- | --- | --- |
| `MH-NAME-SENTINEL` | 乾下兑上，bits `111110` | `primary_hexagram.name == 泽天夬`；0.1.1 预期立即 FAIL |
| `MH-SUPPLIED-NUMBERS` | `supplied-number-9-zi`、`supplied-number-8-hai` | 上下卦、动爻、本/互/变、体用 |
| `MH-METHOD-COVERAGE` | 五类方法各取一条 `exact_replays` | 方法、provenance、无 fallback/替代；0.1.1 有 4 类无法表达 |
| `MH-CALENDAR-BOUNDARIES` | 立春前后、闰月、纽约 DST、历史 offset | time totals、本/互/变、动爻、owned calendar identity |
| `MH-STATIC-API` | candidate `qigua_coin([7,8,7,8,7,8])` → `compute_hexagrams` | 静卦确定行为；0.1.1 预期 `IndexError` |

允许的 policy 差异只有：

- 字段命名/大小写和 0/1-based 爻位在无损 Adapter 中归一。
- 六爻静卦的 `changed=null` 可显式归一为与本卦相同的当前 Canonical 盘。
- Candidate 随机生成、格式化文本、吉凶/assessment、用神断法全部排除，不比较也不接管。
- 时区、地点、子时、起卦 provenance、流派/source profile 始终是 owned 输入或 owned facts。

首个失败判据：本/互/变卦、爻序、动爻、纳甲/世应/六亲/六神/旬空、体用、方法 provenance、owned calendar identity 任一不一致立即停止；缺 required fact、fail-open fallback、许可未闭合或 raw 对象泄漏同样立即失败。

## 单事实源切换门禁

1. 先关闭候选精确版本、许可证、来源和发行单元证据。
2. Candidate 只在私有 Engine Adapter shadow mode 跑；当前自研 Canonical Facts 仍是唯一权威。
3. 不改 expected，跑完选定现有 Goldens 与边界；每个可接受差异必须是明确 Adapter normalization 或 owned policy 差异。
4. Adapter 只发出现有每术 Canonical Facts；raw candidate 对象全部剥离，自研规则/古籍证据/裁决层保持不变。
5. 以一个版本化 Provider 配置原子切换；保留旧 fixtures 作为回归证据，同时删除/禁用自研机械盘的并行生产路径，不能长期保留两个事实源。
6. 切换后任一事实、provenance 或 release-closure 漂移立即 rollback。

## 唯一下一步

`NO-QUALIFIED-CANDIDATE`，现在不创建 Adapter 卡。两术继续 self-owned migration oracle；仅当上述同一候选的新上游版本关闭缺口，或出现新的 focused candidate 时，再创建独立 evidence-only 准入卡。本结论只覆盖本次定时核证窗口，不把当前候选不足扩写成永久自研路线。
