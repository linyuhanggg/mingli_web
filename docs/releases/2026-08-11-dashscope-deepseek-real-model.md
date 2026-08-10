# 阿里云百炼 DeepSeek 真实模型接入

记录日期：2026-08-11（Asia/Shanghai）

状态：**本机真实 Runtime + 真实模型冒烟通过 / 测试服务器真实链路出现 accepted / Task 13 未完成 / production blocked / real traffic disabled**

## 变更

- 模型适配器允许两个 base URL：
  - `https://api.deepseek.com`
  - `https://dashscope.aliyuncs.com/compatible-mode/v1`
- P0 默认改为百炼兼容端点。
- 模型仍冻结为 `deepseek-v4-flash` / profile `deepseek-v4-flash-p0-v1`。
- 对百炼请求强制 `enable_thinking=false`，避免思考 token 吃光 `max_tokens` 导致空 content。
- 后续热修：
  - `aff23aa`：narrative policy id 与 model adapter 对齐
  - `5b5ceb7`：真实 brief limits 与 preview Guard 兼容
  - `9623ee3`：Worker 对 runtime state root 可写，避免真实 Runtime 状态落盘失败
  - `3446061`：免费八字 preview 默认发送 `career` 维度，避免必需维度缺失

## 本机证据

- Runtime startup：`OneShotMingliRuntimeAdapter` 通过。
- bazi prepare：`Prepared`。
- 真实模型 generate：`receipt_outcome=succeeded`，`provider_model=deepseek-v4-flash`，返回 Candidate blocks。
- 聚焦测试：`test_standalone_model_adapter.py` + `test_model_data_boundary.py` 全绿。

## 服务器真实链路

- 测试服务器：`fateradar-prod`
- 真实模型接线基线：`cb01d65`，并叠加 policy/limit/worker state 热修
- Worker 使用真实 Runtime（`/opt/fateradar/shared/mingli-master` + Linux dedicated venv）与真实 DashScope DeepSeek
- 服务器 E2E 已出现 `accepted` 记录，且 generation_attempt 无 guard_errors
- 验收期间 OTP 可暂回 `fake`（`development_code=246810`），避免邮件通道干扰真模型联调
- Worker state root 写权限已修（`9623ee3`）

## 前端配套

- `6f77658`：八字盘面工作区、档案入口、结果页展示增强
- `3446061`：免费八字 preview 默认 `career` 维度

## 密钥边界

- API Key 只注入运行环境：`DEEPSEEK_API_KEY`
- 本机私密文件：`~/.config/mingli/local-real-model.env`（600）
- 服务器私密文件：`/etc/fateradar/test.env`（0600）
- 仓库、示例 env、发布归档不得包含真实密钥

## 仍 blocked

- 固定模型质量评测、Guard 红队、Task 13 staging 全轨迹、生产告警与外部合规 Gate 未完成
- 未开放公网真实业务流量
- 当前服务器真实链路属于代码测试/联调环境，不等于隔离 staging 合同完成，更不是 production 放量
