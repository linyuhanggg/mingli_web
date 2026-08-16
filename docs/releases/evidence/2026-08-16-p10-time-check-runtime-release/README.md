# P10 寻时定盘 V53 Runtime 事实 release 复验（v2）

日期：2026-08-16

## 当前 v2 复验

- 当前工作区 release source commit 为 `local-time-check-candidate-evidence-v2`，release manifest SHA-256 为 `a6babf16be193daf6f59b5759a6734e902d4d85137bdc9832d4a84465289ae67`。
- 当前 admission inventory 为 `219 files / 14 providers / 55 reference packs / 1328 evidence records / 219 closure files`；Runtime describe digest 为 `8036a77edb8c30036fc076ec17a0375a6ee0d604d040b128ac992dc5764179c3`，capability shape SHA-256 为 `c0fc6b3d51e419ea6a9c4fd06cc6c48431ab2158934943a307b9b29a668e531f`。
- 修正十二时辰代表候选：代表时刻为 `00:00, 02:00, …, 22:00`，候选资格按半开时辰区间与已知范围求交；候选代表时刻、`hour_branch` 和实际四柱时支逐项一致。
- 修正事件证据边界：负向关系不会单独产生命中，越过已知时间范围的候选不会进入 `matched_candidate_ids` 或 `event_matches`。
- 真实专用 Runtime + 正式 one-shot 启动器 + Worker → Accepted → typed ReadingDocument 回归：`1 passed / 3 deselected`；纯 Runtime 语义回归：`3 passed`。
- 由于工作区位于 exFAT，文件模式无法持久表达 manifest 的私有模式；本次正式 admission 使用按 manifest 恢复模式的 APFS 临时副本验证。没有部署生产，也没有把测试机 `local + Fake` 当作生产证据。

当前 v2 仍只证明有界候选事实和结构化事件证据排序，不是完整古法校时、候选淘汰规则或“最可能时辰”结论。

## v1 历史基线（保留）

- 修复 V53 release 与当前 V51 核心代码之间的漂移：Bazi 公开扩展事实、来源推理工具和自定义投影保持一致。
- 保留 `time-check` Provider，按指定日期和时间范围生成十二个传统时辰代表候选。
- 每个候选继续复用 Bazi Runtime，并保留真太阳时口径、四柱、日主和归一化时间事实。
- 当时重新生成并签名 218 个 release 文件；该结果已被当前 v2 的 219 文件 release supersede。
- 修复内部 TimeCheck 调用 Bazi 时空 intent 为空导致的启动错误；通过 staged 与正式本机 release 两轮真实 Worker 回归。

## 可复核结果

- staged release admission：通过。
- 正式本机 V53 release admission：通过。
- 真实 Runtime → Worker → Accepted → typed ReadingDocument 的 14 Provider 矩阵：通过，单个 pytest 用例覆盖 14 项。
- 公开核心盘面、目标年份/月份/日期投影：`5 passed`。
- 受影响的本地合同与启动门禁：`93 passed, 12 skipped`。
- 结构化事件直算输出 12 个候选、12 条候选证据排序和 2 条事件匹配；状态为 `candidate_evidence_ranked/structured_evidence`。
- 纯文本事件标签仍只计数，不参与匹配；无结构化事件时保持 `ranking_status=not_ranked`、`event_matching_status=not_calculated`。

## 明确边界

这不是完整古法校时完成证明。当前结构化路径只使用事件年份干支、地支关系和事件领域十神角色生成有界候选证据，不生成生命事件结论，也不把证据排序升级为“最可能时辰”。没有结构化事件时不能从自由文本标签推导排名。当前结果也不包含姓名、出生资料、坐标、密码、SMTP 凭据或 API key。

旧的本机 V53 release 保留在 `release.before-sync-20260816`，用于回滚和差异核对；工作区镜像位于 `.runtime/v53-time-check-release`，不含生成的 Python 字节码。
