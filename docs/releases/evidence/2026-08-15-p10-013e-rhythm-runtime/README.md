# P10-013E 本命音律纳音事实工具

日期：2026-08-15

## 这次完成了什么

本切片把公开工具“本命音律”接到已经存在的 `luming-nayin` Runtime Provider，产品身份单独使用 `rhythm`，避免把工具名称误当成新的算法 Provider。

- `rhythm_preview` 已注册为明确的 ProductRoute，能力固定为 `luming-nayin`、对象 `natal`、周期 `life`。
- `POST /api/v1/readings/rhythm` 只接受已确认 ProfileVersion、可选查询和唯一的 `state` 维度。
- Web `/tools/rhythm` 从服务端已确认档案启动任务，进入独立的 Rhythm Runtime Chart；浏览器不重新排盘、不读取出生资料，也不生成姓名学、吉凶或性格结论。
- 结果使用严格的 `rhythm-facts-view/v1`，只展示四柱、四柱纳音、算法谱系、事实范围和 `facts_only` 状态，不泄漏禄马贵关系等禄命产品字段。
- 后端真实 Worker 会以 `product_id="rhythm"` 构建并保存 `reading-document/v1`，因此产品身份与共享的 `luming-nayin` Provider 已在同一条链路内分开。

纳音的事实范围来自已安装 Runtime 的 Provider 和项目内纳音资料；本切片没有另造“声音评分”或模型解释规则。

## 已验证

- 后端契约、投影、RequestCompiler、API、ReadingDocument 定向回归：`201 passed`。
- Web Runtime Chart 回归：`6 passed`；typecheck、lint 通过。
- 冻结 V51 Runtime：原有 `luming_nayin_preview` 与新增 `rhythm_preview` 均为 `Prepared`，并成功投影四柱纳音，`2 passed`。
- 真实 V51 Worker 核心矩阵包含 `rhythm` 产品：`1 passed / 2 deselected`，覆盖 `Prepared → calculated facts → Accepted → rhythm-facts-view/v1 → reading-document/v1`。
- 使用用户授权的临时个人输入做了一次真太阳时 Runtime smoke：返回 `Prepared`、4 个纳音事实，产品时间策略为 `local_apparent_solar-v1`；输入只存在于临时进程和临时状态目录，没有写入仓库、服务器、证据正文或记忆。

## 边界

这证明的是“本命音律 = 纳音事实展示”的核心接入，不证明完整音律解释、姓名学、吉凶结论或生产上线。解梦、姓名分析、寻时定盘和同盘匹配仍没有可验收的确定性 Provider/规则合同，不能用这个切片冒充已经完成。

本证据不包含个人出生资料、密码、邮箱凭据、API key 或其他秘密。

## 测试服务器热更新（2026-08-15）

- `fateradar-prod` 当前 release 仍为 `ui-preview-20260815-public-products`；没有新建整套 release，采用可回滚热更新。
- 更新前备份保留在 `/opt/fateradar/shared/cache/rhythm-facts-hotfix-20260815/`，包含后端变更文件、旧 Web standalone 和旧静态资源。
- API、Worker、Web、Admin、Nginx 均 active；API live/ready、`/healthz`、`/tools/rhythm`、`/tools/five-elements`、`/bazi`、Admin `/login` 返回 200。
- 服务器动态 OpenAPI 位于 `/api/openapi.json`，其中包含 `startRhythmReading`；测试机仍是 `local + Fake`，只用于页面浏览，不代表真实生产 Runtime 或 P12 准入。
- 用户浏览入口：`http://127.0.0.1:18080/tools/rhythm`；同时可复验 `http://127.0.0.1:18080/tools/five-elements` 和 `http://127.0.0.1:18080/bazi`。
