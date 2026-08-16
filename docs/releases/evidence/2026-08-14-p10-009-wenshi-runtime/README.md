# P10-009 问事合参三术核心接入

状态：`IN_PROGRESS`，这是已验证的核心接入切片，不是 P10-009 全部完成。

## 已完成

- `wenshi_one_question` 将同一问题、同一事件时空和同一组六爻输入编译为 Runtime 原生比较合同：六爻为主 capability，奇门和大六壬为 `required` comparisons。
- Reading Root/Version 增加产品身份和有序 Runtime capability 集合。Wenshi 新记录明确保存 `product_id=wenshi` 与 `liuyao → qimen → liuren`，不会在历史或 API 摘要中伪装成单独六爻。
- `/api/v1/readings/wenshi`、OpenAPI、幂等、权益动作映射和 Web `/wenshi` 输入流程已接通。页面提交六次起卦过程、事件时间、时区和地点到服务端，不在浏览器起盘。
- `wenshi-view/v1` 严格投影三术 Runtime fact provenance：六爻关系事实、奇门局面范围/盘面事实、大六壬请求维度事实。缺失能力进入 `missing_art_ids`；没有权威共同语义时 `convergence` 和 `disagreements` 保持空。
- 结果页新增三术结构事实表，只显示 Runtime 已计算事实，不把九宫、四课三传、卦爻字段硬拼成吉凶或实质互证结论。

## 验证

- 后端请求编译、投影、迁移、OpenAPI 定向回归：`131 passed`。
- Reading Repository、Readings API、账户历史、Worker、权益和 Runtime 受影响回归：`89 passed, 20 skipped`。
- 本机 frozen V5.1 one-shot Runtime：Wenshi `describe → prepare` 真实回归 `1 passed`；返回 `liuyao`、`qimen`、`liuren` 三组计算事实，并成功投影为 `WenshiViewV1`。
- 最终 `make check` 后端全量回归为 `801 passed, 102 skipped`；迁移 revision 名称修正与 Wenshi 字段断言也通过迁移 `31 passed` 和受影响回归。
- Web 定向流程 `52 passed`，全量 `68 files / 434 tests`，lint、typecheck、Next production build 全通过。
- `git diff --check` 通过。

## 明确未完成

本切片只证明三术能在同一个 Runtime Brief 中真实生成并被正确展示，不证明三术已经形成统一的实质判断规则。仍缺：权威跨术共同维度/互证与分歧规则、真实 Worker 轨迹和恢复、ReadingDocument/深读/追问/导出、黄金样例、生产 Runtime admission、公开上线以及 P4-007 用户逐页批准。

测试输入均为合成数据，不包含用户个人出生资料、密码、API key、SMTP 凭据或支付凭据。
