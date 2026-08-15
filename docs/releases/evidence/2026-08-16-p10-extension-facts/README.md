# P10 Runtime 扩展事实透传（2026-08-16）

## 结果

本轮修复了一个真实的 Runtime→Prepared brief→Typed ViewModel 断点：Provider 的自定义公共投影在合并时丢掉了 manifest 已声明的 fact-extension 输出。现在自定义投影只负责基础盘面裁剪，声明的扩展输出仍会进入公共计算事实。

六爻 Runtime 新增独立公共事实绑定：

- `line_facts`
- `returning_relations`
- `changed_plate_lines`
- `shi_ying_moving_relations`

大六壬的 `timing_candidates` 仍遵循真实边界：只有请求 `timing` 维度时才生成；没有明确日期范围时可以返回空候选列表，但这仍是已计算的“无可承诺候选”，不会被硬写成应期结论。

## Runtime 受控发布身份

为不改写官方冻结 V51，新增仅本地/测试可用的 `v51-extension-facts` profile：

- describe manifest digest：`560fdbdd6c9eed66dd232209a055ab206dba31ee51adf238fa88239956154725`
- release manifest SHA-256：`3dca2cda59faab83ad829b1a5870b6f34f2e4b81d2cafdeb2d56c414430bd807`
- 13/13 Provider、217 个签名文件、55/55 reference pack、1328 条 evidence 保持不变
- 生产配置明确拒绝该 profile；它不代表 Mac mini native-full 或生产 admission

## 验证

- 真实 one-shot Runtime/Worker/ReadingDocument 矩阵：`36 passed / 1 skipped`
- 全仓 `make check`：Backend `933 passed / 113 skipped`，Ruff 通过，mypy `142 source files` 通过
- Web：`72 files / 452 tests`，lint、typecheck、production build 通过
- Admin：`33 files / 121 tests`，lint、typecheck、production build 通过
- skip 只涉及受控 V52 relationship release 的环境条件；没有用两张独立命盘冒充原生合盘

## 边界

这轮只补确定性事实透传和合同回归，不新增深读、旺衰/喜忌/用神硬断、六爻/大六壬完整断法、寻时事件匹配/淘汰/排名、Canwen/Hecan 实质互证、解梦/姓名 Provider，也不改变 P4-007 用户浏览批准和 P12 外部门禁状态。

本证据不包含个人资料、密码、SMTP 凭据、API key 或状态 token。
