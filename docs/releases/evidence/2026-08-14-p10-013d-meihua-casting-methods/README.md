# P10-013D 梅花五种起法核心接入

日期：2026-08-14

## 这次完成了什么

- 保留 `time` 时间起卦的既有冻结请求合同，并新增四种真实 Runtime 起法：
  `supplied_number`、`sound_count`、`observation`、`supplied_hexagram`。
- Request Compiler 按方法只组装 Runtime 允许的字段：数字与来源、声数与观察来源、上下卦与观察来源、上下卦/动爻与资料来源；缺字段、非法卦名、非正整数和越界动爻在进入 Runtime 前拒绝。
- `MeihuaStartRequest`、Reading Service、私有 API 和 Web 任务输入已同步支持五种方法。页面按所选起法显示所需资料，没有把自然语言观察自动分类成卦象。
- 既有 `meihua-chart/v1` 投影已能消费五种方法的 Runtime 结果，仍只展示结构事实，不生成吉凶结论。

## 已验证

- Backend 编译器与 API 定向回归：`111 passed`；Ruff 通过。
- Web 类型检查通过；API/阅读流程相关测试：`19 passed`。
- 冻结 V51 one-shot Runtime：梅花时间起卦 + 其余四种起法 `2 passed / 23 deselected`；每种结果均为 `Prepared`，`request_view.capability_ids == ["meihua"]`，并成功投影到 `meihua-chart/v1`。
- Runtime 启动门禁使用正确的 describe 摘要和 release 文件清单摘要；没有修改 V51 release。

## 边界

这证明的是梅花五种起法的核心输入编译、真实 Provider 计算、严格结构投影和当前 API/UI 输入接线。它不证明真实 Worker 数据库全旅程、ReadingDocument/深读、导出分享、用户逐页批准、生产 Runtime admission、真实支付或公开生产上线。

本证据不包含个人出生资料、密码、邮箱凭据、API key 或其他秘密。

