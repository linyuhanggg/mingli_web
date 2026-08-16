# P10 大六壬维度候选证据补充

日期：2026-08-17

## 本轮接入

在 V53 `liuren` Runtime 中，把来源索引标记为 `runtime_active=true`、且当前课盘事实足够直接匹配的三条规则接入维度证据层：

- `state`：大六壬秘本 `LM-R01`，由三传天将/落支的已索引类象对应生成 `state_general_landing_correspondence`；它是类象候选，不是现实活动事实。
- `timing`：大六壬秘本 `LM-R21`，在有界日/月窗口且能计算候期支时生成 `timing_candidate_branch`；候选日期仍标记为候选，不是保证的应期。
- `relationship`：六壬指南 `LR-17`，仅在日辰形成定向生克时生成主客关系证据；按方向分别保留 support/oppose，不合并成结论。

每条记录都带 Runtime 事实路径、规则 ID、activation ID、来源锚点、依赖组和 `hard_verdict: null`。Wenshi 只消费这些 Runtime 已声明的 matched 记录，Host 不自行推导极性或合断。

## 明确没有冒充完成的部分

- `location` 目前已输出十二支到方位的确定性候选，但来源表把它作为象征方向，尚未有独立的可执行断法规则。
- `work/career` 仍只有六亲、阶段和主客结构事实，缺少事项目标合同，不能把官鬼/父母等自动当成用户的工作目标。
- `timing` 的 `DLR-16`、`LM-R13`、`LR-16`，以及 `state/relationship/work` 的 `LM-R06`、`LM-R09`、`LM-R15`、`LR-09` 等仍是 `inactive_unverified`，继续保持未绑定。
- 完整大六壬成败、吉凶、学校裁判、三术合断和深读仍未完成。

## 复核结果

- V53 真实 Runtime→Worker→Accepted→typed `ReadingDocument` 全核心矩阵：`1 passed`。
- Wenshi 六壬来源证据投影：`1 passed`。
- Runtime 启动配置/manifest 定向回归：`4 passed`。
- 正向规则探针：`state=LM-R01`、有候期支时 `timing=LM-R21`、定向相克时 `relationship=LR-17` 均命中。
- V53 release manifest SHA-256：`149d150839a664c551f53afddae9acc93a82c5e5e9ca8379a49151c01f338554`；describe digest 与 capability shape 未改变。

本证据不包含出生资料、姓名、密码、SMTP 凭据或 API key。
