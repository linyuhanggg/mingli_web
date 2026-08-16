# P10-005A 三术合参结构化 Runtime/API/UI 接入

状态：`IN_PROGRESS`。这是 P10-005 的结构接线切片，不是三术完整互证、分歧和深读完成证明。

## 本次完成

- 新增产品 action `hecan_preview` 和 `/api/v1/readings/hecan`；请求固定八字为主术，用户只能从八字、紫微、七政中选择两术或三术。
- Hecan 和 Canwen 使用同一组 required Runtime comparisons，但分别持久化 `product_id=hecan` / `product_id=canwen`，结果层按产品身份选择严格 ViewModel，不再把合参误投影为普通八字或 Canwen。
- 新增 `hecan-view/v1` 的 Runtime projector、Web API 调用、任务提交、结果卡片和 OpenAPI/合同测试。
- Hecan 只展示 Runtime 声明的维度事实范围、已提供术数、缺失术数和明确的范围状态；没有把不同术数拼成吉凶、互证或分歧结论。
- 结果页按 `product_id`/ViewModel 分派，Hecan 不再因为八字是 Runtime 主术而误显示八字盘；生产/真实流量只允许 P0 Runtime capability 集合。
- 选七政时编译器要求经度、纬度和坐标来源；Web 只接受已确认 ProfileVersion UUID，并明确八字主术、至少再选一术。

## 验证

- Request Compiler、ViewModel projector、OpenAPI 合同定向回归：`85 passed`。
- Backend readings API：`49 passed`。
- Backend Runtime process adapter：`16 passed, 10 skipped`（真实 Runtime opt-in 项按现有门禁跳过）。
- Web Hecan/Canwen API 与产品路由定向回归：`17 passed`；结果页/注册表回归 `31 passed`；TypeScript 和 ESLint 通过。
- 全量本地门禁：Backend `807 passed, 102 skipped`；Web `435 passed`；Admin `121 passed`；Ruff、mypy、两端 lint/typecheck/production build 全通过。
- 使用用户授权的个人资料做本机临时真实 Runtime 核验：返回 `Prepared`、`bazi/ziwei/xingming`，Hecan 严格投影为 `hecan-view/v1`；只选八字+紫微的 `career` 范围无缺失。输入未写入仓库、证据正文、数据库或测试服务器。
- 本轮 V51 历史复核曾显示三术结果缺少七政跨术范围；随后 V52 relationship release 已补齐七政 `dimension_fact_scope` 的 manifest 绑定。当前 one-shot 13 项 capability 启动通过；八字+紫微和八字+紫微+七政均为 `Prepared`，三术结果每个请求维度均无 `missing_art_ids`。缺少七政经纬度/来源时编译仍直接拒绝。

## 仍未完成

- 七政跨术范围已接入，但这仍不是三术完整互证：还缺权威实质互证/分歧规则、黄金样例、真实 Worker 轨迹、ReadingDocument/深读、导出分享、浏览器逐页批准和生产 admission。
