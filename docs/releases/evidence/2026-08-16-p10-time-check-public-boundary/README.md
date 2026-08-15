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
- 方向 C 全站真实浏览器复核：Web 阶段 2 为 `64/64`、阶段 3 为 `32/32`、阶段 4 为 `44/44`；Admin 阶段 5 为 `164/164`，均覆盖 360/768/1024/1440。
- 最终 `make check`：Backend `934 passed/113 skipped`，Web `72 files / 453 tests`，Admin `33 files / 121 tests`，两端 lint、typecheck、production build 全通过。

## 测试服务器同步

已将本切片以可回滚 hotfix 同步到 `fateradar-prod` 的
`ui-preview-20260815-public-products`，只覆盖两个 Web 源文件。旧文件备份在：

`/opt/fateradar/shared/cache/time-check-boundary-hotfix-20260816-a020b3b/`

远端 `npm run build`、standalone 预启动和 `fateradar-test-web.service` 重启通过；
`/tools/time-check` 与 `/tools` 均返回 HTTP 200。使用系统 Chrome 访问公开寻时路由时，
computed style 为 `body color=rgb(10, 10, 10)`、`background=rgb(250, 250, 250)`，加载 4
份 CSS，未出现裸蓝色文字。该服务器仍是 `local + Fake` 测试验收机，不是生产环境。

本次重建后曾复现一次真实的 CSS 发布故障：HTML 已指向新 hash，但 standalone
目录未同步 `.next/static`，导致 CSS 404、链接退回浏览器默认蓝色。按正确路径运行
`web/scripts/start-standalone.mjs --prepare-only` 后同步静态资产；同时将 Web unit 的
`ReadWritePaths` 收口到构建后必然存在的 `.next` 父目录，避免缺失 `cache` 子目录时
在 `ExecStartPre` 之前被 systemd namespace 阻断。修复后的 360/768/1024/1440 四视口
中，首页、工具总览、寻时页共 12 个组合全部 HTTP 200、横向溢出 0、默认蓝色计数 0；
四个 CSS URL 均 HTTP 200，寻时页没有结构化事件字段且保留“事件匹配、候选淘汰和排序
尚未接通”边界文案。旧 Web 源文件和 unit 备份在：

`/opt/fateradar/shared/cache/time-check-boundary-corrective-20260816/`

## 范围声明

这不是寻时定盘完整算法完成证明，也不代表事件规则包、古法校时结论、真实生产 Runtime 或用户验收已经完成。结构化事件匹配与候选排序仍是 P10-013 的后续工作；测试服务器仍是 `local + Fake`，不等同于生产环境。
