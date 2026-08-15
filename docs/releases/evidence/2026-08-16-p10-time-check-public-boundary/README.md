# P10 寻时定盘公开输入边界校正

## 结论

当前准入的 V53 time-check Runtime 只输出十二个确定性候选事实，并明确返回：

- `ranking_status=not_ranked`
- `event_matching_status=not_calculated`

它会记录自由文本 `known_events` 的条数，但不会从自由文本推导事件匹配、候选淘汰、权重或排名。当前 release 的 `TimeCheckProvider` 也明确停在候选事实层。

因此 Web `/tools/time-check` 不再让用户提交尚未被当前准入 release 消费的结构化事件输入；页面保留可核对事件条数输入，并直接说明事件匹配、淘汰和排序尚未启用。结果页已有的排序表只在 Runtime ViewModel 真正返回 `candidate_evidence_ranked` 时显示。

## 验证

- Web 定向回归：`npm test -- --run src/test/time-check-flow.test.tsx` → `1 file / 2 tests passed`
- 当前准入 release：`.runtime/v53-time-check-release/scripts/reading_engine/providers.py` 的 `TimeCheckProvider.calculate()` 固定返回上述两个未计算状态。
- 页面与工具总览文案已统一为“事件匹配、候选淘汰和排序尚未启用”。

## 测试服务器同步

已将本切片以可回滚 hotfix 同步到 `fateradar-prod` 的
`ui-preview-20260815-public-products`，只覆盖两个 Web 源文件。旧文件备份在：

`/opt/fateradar/shared/cache/time-check-boundary-hotfix-20260816-a020b3b/`

远端 `npm run build`、standalone 预启动和 `fateradar-test-web.service` 重启通过；
`/tools/time-check` 与 `/tools` 均返回 HTTP 200。使用系统 Chrome 访问公开寻时路由时，
computed style 为 `body color=rgb(10, 10, 10)`、`background=rgb(250, 250, 250)`，加载 4
份 CSS，未出现裸蓝色文字。该服务器仍是 `local + Fake` 测试验收机，不是生产环境。

## 范围声明

这不是寻时定盘完整算法完成证明，也不代表事件规则包、古法校时结论、真实生产 Runtime 或用户验收已经完成。结构化事件匹配与候选排序仍是 P10-013 的后续工作；测试服务器仍是 `local + Fake`，不等同于生产环境。
