# P10 六爻问题维度与用神候选链接入

日期：2026-08-16

## 完成内容

V53 `liuyao` Provider 已把结构化问题维度接入六爻候选层。路由只读取
`IntentFrame.question_dimensions`，不从自由文本猜测用神：

| 问题维度 | 候选六亲 | 状态 |
|---|---|---|
| `career/work` | 官鬼 | 已接候选 |
| `money` | 妻财 | 已接候选 |
| `relationship` | 官鬼、妻财 | 已接候选 |
| `health` | 官鬼、子孙 | 已接候选 |
| `education` | 父母 | 已接候选 |
| `location` | 父母 | 已接候选 |

在候选六亲存在时，Runtime 进一步按五行生克生成有界的用神、原神、忌神、仇神候选链，并按《增删卜易》`ZP-05` 把每个候选的月令状态、月破、日冲、旬空和动静整理为 `strength_evidence`。输出明确标记为
`candidate_only`，并设置 `requires_school_adjudication=true`；这只是把可复核的候选事实送到产品层，不是成败、吉凶或应期断语。

## 来源与合同

- 规则依据：`divination/zengshan-buyi` 的 `ZP-04`（按问题分类取用神，再看原神、忌神、仇神）以及项目已登记的 `HZL-P001` 来源绑定。
- Runtime 来源依赖：`liuyao.interpretation.useful-spirit-chain-candidates`。
- 版本：V53 `liuyao` Provider `1.3.0`。
- `strength_evidence` 来源依赖：`liuyao.interpretation.useful-spirit-strength-evidence`。
- V53 release manifest：`7e5cf39aeff3a563a8e0ee60bb6573b4a4531107ad030faa9e9f0a75de6f4b4b`。

## 复核结果

- 真实 V53 Worker→Accepted→typed ReadingDocument 核心矩阵：`8 passed, 1 skipped`。
- skip 原因：当前环境没有安装 V52 relationship release，不是六爻候选链失败。
- 六爻定向真实 Worker 用例：通过。
- 事业维度黄金样例：官鬼候选含 `ZP-05` 来源证据、逐候选信号和 `hard_verdict=null`。
- 文式 `outcome/timing` 用例：保持 `not_requested`，不会无依据地自动指定官鬼等用神。

## 边界

本轮没有实现六爻旺衰裁决、世应成败、动爻断法、具体应期、吉凶结论、跨术数实质互证或完整深读。`outcome`、`timing` 等尚未绑定正式取用神规则的维度继续保持未请求状态。后续必须先补来源、输入输出合同和黄金样例，再接入解释层；不能用自由文本或用户个人资料替代规则。

证据不包含个人出生资料、姓名、密码、SMTP 凭据或 API key。
