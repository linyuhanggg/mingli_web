# Task 13 服务器真实轨迹（runner 输出）

- 生成时间（UTC）：2026-08-10T21:53:07+00:00
- 服务器：`iZuf67fkafnm3w0abdmz3mZ`（SSH 别名 `fateradar-prod`）
- 本机 main HEAD：`6c592b6`；服务器 current：`/opt/fateradar/releases/1c26f0924ce22171b32f0c75a781f7599eec6ed5`
- API 入口：`http://127.0.0.1:8080/api/v1`（nginx 回环同源，浏览器同路径）
- 身份：t***@example.com（虚构邮箱 / 虚构出生资料，原文不落库不落仓）

## 环境适配器（非秘密键）

- `MINGLI_ENVIRONMENT` = `local`
- `MINGLI_MODEL_ADAPTER` = `deepseek`
- `MINGLI_MODEL_ID` = `deepseek-v4-flash`
- `MINGLI_MODEL_PROFILE_ID` = `deepseek-v4-flash-p0-v1`
- `MINGLI_OTP_ADAPTER` = `fake`
- `MINGLI_RUNTIME_ADAPTER` = `one-shot`

## 轨迹状态

| 步骤 | 内容 | 结果 | 细节 |
|---|---|---|---|
| S1-guest-session | guest session | ok |  |
| S2-email-otp | email OTP request | ok |  |
| S3-otp-verify | email OTP verify | ok |  |
| S4-S5-profile | profile draft + confirm (fictional) | ok |  |
| S6-preview-bazi | preview bazi (career) | ok | input_ready / ['input_ready', 'prepared', 'accepted'] / accepted / 218 |
| S7-today | today fortune | FAIL | input_ready / ['input_ready', 'prepared', 'delayed'] / delayed |
| S8-week | week fortune | FAIL | input_ready / ['input_ready', 'prepared', 'delayed'] / delayed |
| S9-liuyao-digital-coin | liuyao digital_coin | FAIL | input_ready / ['input_ready', 'prepared', 'delayed'] / delayed |
| S10-follow-up | follow-up (new version) | FAIL | ['input_ready', 'terminal_stopped'] / terminal_stopped |

## 敏感扫描

- 检查标记：state_token, prompt_key, api_key, raw_birth_datetime, cookie_token_echo
- 发现：1 处

## delayed 存量（只读 status 计数）

- 运行前：`{"available": true, "counts": {"accepted": 6, "delayed": 10}, "total": 16}`
- 运行后：`{"available": true, "counts": {"accepted": 7, "delayed": 13, "terminal_stopped": 1}, "total": 21}`

## 结果

- exit_code：`2`
- hard_failure：`True`
- partial 原因：
  - S7-today today fortune: delayed
  - S8-week week fortune: delayed
  - S9-liuyao-digital-coin liuyao digital_coin: delayed
  - S10-follow-up follow-up (new version): terminal_stopped
  - sensitive markers found: raw_birth_datetime@S6-preview-bazi-result

## 说明

- 原始 HTTP 响应体只保留在服务器 0700 工作目录，未复制回仓库。
- 未伪造 delayed：本轮只记录存量与自然结果；Guard 红队仍 pending。
- 本记录是测试服务器联调证据，不等于 staging 合同完成；production blocked。
