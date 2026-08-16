# P10 大六壬来源规则证据接入

日期：2026-08-16

## 完成内容

V53 `liuren` Runtime 新增来源绑定的规则证据层，加载
`references/inference/liuren-rules-v1.json` 中的 17 个规则定义。它只把已计算的课体事实编译成规则激活记录，不把支持/反对记录相加，也不生成吉凶硬结论。

当前可直接评估的事实路径：

- `outcome`：日干/日支关系、三传与日干关系、初传/末传关系、中传旬空；可对应 `LR-17`、`LR-18`、`DLR-17` 和 `LM-R10`。
- `money`：妻财是否出现在三传、妻财是否旬空、中传旬空；可对应 `LM-R20`、`LR-15` 和 `LM-R10`，没有妻财时输出 `wealth_absent_scope` 范围边界。
- `message_target_*`：当前课体合同没有消息目标事实，明确输出 `required_fact_missing`，不猜测目标强弱或空亡。
- `timing`、`state`、`location`、`relationship`、`work`：继续保留已有确定性维度事实，当前规则包没有可直接绑定的完整解释激活，因此输出 `not_bound`。

每个维度都保留：`rule_id`、`activation_id`、极性、权重、依赖组、来源引用、事实路径和观察值；聚合结果固定包含 `hard_verdict: null` 与 `requires_school_adjudication: true`。

## 来源与准入

- 规则包：`references/inference/liuren-rules-v1.json`。
- 主要来源：`san-shi/liuren-zhiyin` 的 `LR-17/LR-18/LR-19`，`san-shi/liuren-miben` 的 `LM-R10/LM-R20/LM-R22`，以及 `san-shi/daliuren-daquan` 的 `DLR-17`。
- Provider contract：`mingli-liuren-pipeline-v5-rule-evidence`。
- 新规则文件 SHA-256：`429148101cc057c9398561b6c5201ac9506f6821053ce4d8e709acf4dbefc438`。
- V53 release manifest SHA-256：`7e52363526bfc3ddd5d864c8356def8723277ea1762191f11c8f07b51f34fb85`。

## 复核结果

- 独立规则探针：17 条定义加载成功，日干/三传/初末传/中传旬空四类命中路径通过，硬裁定保持为空。
- V53 真实 Worker→Accepted→typed ReadingDocument 核心矩阵：`8 passed, 1 skipped`。
- skip 原因：当前环境没有安装 V52 relationship release，不是大六壬规则证据失败。
- 全仓旧门禁尚未在本轮重跑；接下来需要跑 `make check`，确认准入计数、manifest 配置和工作区合同全部一致。

## 边界

本轮没有实现大六壬完整成败、吉凶、应期或三术合断；规则证据不是预测结论。消息目标、财务成本基础、问题专属取用和多派冲突裁判仍需独立输入合同与来源规则。证据不包含个人出生资料、姓名、密码、SMTP 凭据或 API key。
