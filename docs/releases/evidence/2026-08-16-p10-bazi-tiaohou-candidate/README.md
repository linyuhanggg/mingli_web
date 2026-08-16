# P10 八字调候候选规则接入

日期：2026-08-16

## 完成内容

Runtime 已把参考包 `bazi/qiongtong-baojian` 的 40 条“日干 × 月令”调候规则接入 `interpretive_candidates.reasoning_tools.tiaohou_candidates`。规则路由只读取 Runtime 已确认的节气月令和日干，不使用公历月份猜月令。

每条候选输出：

- 规则 ID（`QR-01-01` 至 `QR-05-08`）；
- 典型优先天干顺序；
- 每个天干在年/月/时透干、地支藏干或缺失的状态；
- `candidate_only`、参考包 `unverified` 标记、原始 fact/source refs 和 tool digest。

“日柱自身”不会被当作透干证据。调候候选与旺衰证据、月令格局、合化/从化仍然分开，未生成喜忌、用神、富贵、疾病或吉凶硬结论。

## 复核结果

- 合成盘探针：丙日辰月命中 `QR-02-01`；壬为缺失、甲为透干，未把日柱自身计入透干。
- V51-extension 真实 13 Provider Worker→Accepted→typed ReadingDocument：`1 passed`。
- V53-time-check 真实 14 Provider Worker→Accepted→typed ReadingDocument：`1 passed`。
- Bazi ViewModel/Runtime contract/chart projector 定向回归：`39 passed`。
- V53 release admission：`218 files / 14 providers / 55 reference packs / 1328 evidence records / 218 closure files`。

## 边界

参考包中的规则状态仍为 `unverified`，所以本轮只完成来源绑定和候选可见性，不把典型调候组合升级成最终用神。完整旺衰、格局成败、从化和多派冲突裁判仍需独立合同与黄金样例。证据不包含个人出生资料、姓名、密码、SMTP 凭据或 API key。
