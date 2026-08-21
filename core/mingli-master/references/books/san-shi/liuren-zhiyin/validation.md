# 《六壬指南 / 六壬指南注解》Validation

## Source state

**完整可检索注本已入库、原本影印已取得、未全本逐页校勘。**

`source_status: complete_text` 只描述张洪完整可检索注本的文本覆盖，不代表影印精校、古本定本或逐句作者归属已经完成。

## Static self-check results

Run date: 2026-07-10

| check | result | detail |
|---|---|---|
| `source-manifest.yaml` parse | PASS | PyYAML 6.0.3 |
| `test-prompts.json` parse | PASS | Python JSON parser |
| normalized extent | PASS | 2798 lines |
| quote exact hits | PASS | 48/48 `exact_quote` values命中声明行 |
| rule quote references | PASS | 37 unique quote ids; 0 missing |
| rule-card schema | PASS | 15/15 cards含来源层、quote、行号、前置字段、执行、例外、冲突、adapter、置信度 |
| normalized line ranges | PASS | `chapter-map.md` / `rules.md` 均在 L1-L2798 内，0 invalid ranges |
| manifest checksums | PASS | 11/11 local files sha256 matched |
| source-state wording | PASS | 精确命中要求状态句 |
| dependency correction | PASS | `index.md` 的 `depends_on` 为空；《大六壬大全》仅为可选比较 |
| test prompt structure | PASS | 14 cases: 7 should-trigger, 3 should-not-trigger, 4 edge |

## Cangjie gates

| gate | status | evidence / limitation |
|---|---|---|
| V0 completeness | PASS WITH QUALIFICATION | 完整注本、五个 CTP 容器和完整注解镜像可检索；影印未逐页校勘 |
| V1 location | PASS | 每条最终规则绑定 `quote_id` 与 normalized 行号 |
| V2 source fidelity | PASS WITH OPEN RISKS | 两赋/陈注/张注/庄氏层/现代课例已分开；卷四题下注作者仍有未定项 |
| V3 operationality | PASS | 15 张规则卡均有输入字段、分支、停止条件和 decision effect |
| V4 lineage boundary | PASS | 规则限定《指南》注本口径，不把《大全》或他派 tie-break 偷并入 |
| V5 no calculation hallucination | PASS | 月将、天地盘、四课三传、神将和神煞全部要求 adapter |
| V6 case-layer separation | PASS | 增补、1998 年和潍坊课例均标现代层；第 30 章不并入陈公献 1-29 章 |

## Structural indexing claim

- 卷首：6 个来源语义单元。
- 卷一：8 个赋文/注释语义段。
- 卷二：12 个赋文/注释语义段。
- 卷三：1-29 章主体加 1 个“第三十章”现代附录异常。
- 卷四：卷题、全图、岁煞、月/季煞、旬煞、干煞、支煞、辨讹共 8 层。

这是结构索引，不是“规则 100% 覆盖”。`rules.md` 选择性保留核心取用、解释顺序、来源守门和神煞后置规则；卷一、二全部类象和卷三所有断语并未逐条卡片化。

## Behavioral test status

`test-prompts.json` 已通过 JSON 和字段静态检查，但尚未执行独立模型盲测。因此不能报告通过率，也不能把 `minimum_pass_rate` 当实际成绩。后续盲测必须特别审查：

1. 下贼是否始终优先于上克。
2. 多克并列时是否会擅加别派涉害 tie-break。
3. 八专无克是否错误进入遥克。
4. 反吟无克但日柱不符六日时是否停止。
5. 神煞是否被错误提升为主判断。
6. 现代潍坊课例是否被误称陈公献古例。
7. 是否伪造 NLC 影印页码。

## Remaining risks

1. **影印校勘**：NLC 248 页没有全本逐页逐行对校，不能给稳定影印页码或声称图表无误。
2. **卷四表格**：CTP 行表压平了图表和空格；具体神煞起例须由已校验 adapter 计算并回看影印。
3. **卷四归属**：旧序称庄公远，卷末署庄广之；L2451 又是 CTP 题下注。逐句作者归属仍需版面证据。
4. **章数异常**：L860 的二十九章与 L2431 第三十章并存；当前把第三十章列现代附录，但尚无影印版次链证明其最初加入时间。
5. **卷次映射**：现卷四与 L910“卷五神煞”之间的映射尚属强解释、非逐页定论。
6. **文本异文**：如“六壬如入/如人”、伏返/伏反、干/乾、丑/醜等尚未形成校勘记。
7. **涉害并列**：本注本可定位规则不足以解决同一孟仲季层内的全部并列，故保留 `unresolved_by_this_pack`。
8. **行为盲测**：14 条 prompt 未实际跑模型，不得宣称测试通过。

## Acceptance boundary

本包可用于来源分层、文本检索、核心取用流程解释和历史/现代案例辨识。它不是影印定本，不承诺术数预测有效，也不得替代现实医疗、法律、投资或其他专业判断。
