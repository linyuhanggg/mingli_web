# P10-013C 真太阳时与子时 Runtime 合同修复

日期：2026-08-14

## 这次完成了什么

- 产品的 `solar` 时间口径明确编译为 Runtime 的
  `local_apparent_solar-v1`，不再把产品短标签原样送入 Provider。
- 产品的子时标签明确编译为 Runtime 合同：`midnight` 保持午夜换日，
  `substitute` 编译为 `late-zi-next-day`；未知值在 Request Compiler 阶段拒绝。
- `fortune` 在出生资料使用真太阳时或经度均时策略时，补齐经度、纬度和坐标来源；
  民用时的冻结 Prepare fixture 保持不变。
- 本机真实 Runtime 核验使用了用户授权的个人资料，但个人姓名、出生资料和坐标没有写入
  仓库、测试 fixture、证据正文或记忆。

## 已验证

- Request Compiler：`61 passed`。
- 冻结 V51 one-shot Runtime：`8 passed / 16 deselected`，覆盖命盘、近时运势、
  三术结构比较、梅花、奇门、大六壬、禄命纳音、太乙、择日、风水和相法的真实 Prepare
  与现有严格投影路径。
- 个人授权输入的临时本机核验：13 Provider 均返回 `Prepared`；其中三术返回
  `bazi`、`ziwei`、`xingming` 三组计算事实，已接入的严格 projector 均成功。
- Startup gate：固定 V51 协议和 13 Provider inventory 通过；测试前后固定 venv 与
  release 没有残留未签名 `.pyc` 或其他运行时副产物。
- Ruff 与相关定向差异检查通过。

## 边界

这次修复解决的是产品输入到 Runtime 的真实合同错误，不代表合参、合盘、见相媒体
Adapter、公开 API/UI、真实 Worker、黄金样例或生产准入已经完成。七政目前仍没有供
Canwen 使用的跨术 `dimension_fact_scope`，因此系统继续禁止伪造共同信号或分歧结论。

本证据不包含个人出生资料、密码、SMTP 凭据、API key 或其他秘密。
