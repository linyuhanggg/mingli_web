# P0–P12 批量施工与验收记录（2026-08-13）

## 基线

- 当前 Git HEAD：`f488fa4d6eaa989b708b14d87b747ee931468829`。
- 本轮没有提交或重置工作树；用户已有 staged/unstaged 改动全部保留。
- P0 权威合同要求 `docs/plans` 不存在，本轮曾生成的临时计划已删除，未恢复并行计划权威。

## 本地完成的部分

- P1：共享中性 Token、Web/Admin primitives、公共壳、私有缓存边界、Admin 壳、UI Lab 和 Playwright smoke 基础。
- P2：公共、术数、合参、Auth、账户、订单、邀请、分享、工具和知识详情深链均有诚实的预制页面；未接能力显示待接入，不生成假盘、假订单或假支付。
- P3：Admin 路由目录覆盖总览、用户、Subject、商品、CMS、盘面、Runtime、订单、权益、邀请、员工、通知、审计和系统路径；未接数据明确显示不可用。
- P5：七术/合盘/跨术 ViewModel schema、`reading-document/v1`、PresentationContract、projector、raw/unknown 禁止测试，以及运行时 OpenAPI 对齐。
- P6：OTP、设备会话、Guest→User 接管、scrypt 密码哈希/登录/设置、版本化 ConsentRecord；新增 0011 迁移。
- P7：Product/Offer、Order/Payment/Refund、追加式权益账本、Outbox 的数据基础；新增 0010 迁移。
- P8：邀请策略测试、活动/邀请码/临时归因/唯一注册锁/奖励槽数据基础；新增 0012 迁移的一部分。
- P9：持久化 CMS 服务/API，覆盖草稿、预览、定时、发布、撤回、归档、历史和恢复；新增 0012 迁移的一部分。
- P6：数据导出、单项档案删除、设备会话全撤销、7 天注销撤销期和 Admin 执行队列；新增 0013 迁移。
- P11：加密 `ReadingDocumentV1` 与 AcceptedCopy 绑定的首写落库、claim 级核对、独立 ReportFeedback、限时可撤销 ShareSnapshot；新增 0014 迁移。

## 验收命令与结果

| 范围 | 结果 |
|---|---|
| Web Vitest | 46 files / 358 tests passed |
| Web lint/typecheck/build | 全部通过；build 路由表含补齐的 P2 深链 |
| Admin Vitest | 10 files / 57 tests passed |
| Admin lint/typecheck/build | 全部通过 |
| Backend pytest | 607 passed / 90 skipped |
| Backend Ruff/mypy | 全部通过，101 source files |
| Contract suite | 181 passed / 82 skipped |
| Web Playwright | 360/768/1024/1440：24 passed |
| Admin Playwright | 360/768/1024/1440：16 passed |
| Accessibility Playwright | Web 4 项目 / 20 passed；Admin 4 项目 / 20 passed；见 `2026-08-13-accessibility/` |
| Git diff hygiene | staged/unstaged `diff --check` 全部通过 |

### Native Runtime / P10-001

- release 原始目录位于 exFAT `/Volumes/Lexar`，文件系统忽略 Unix mode；没有改签名字节。
- 原 release 原样复制到 APFS `/Users/yuhanglin/.local/share/mingli-master/release-v51` 后，mode 217/217、digest 217/217 均与 manifest 一致。
- Runtime release inspector：217 files / 13 providers / 55 reference packs / 1328 evidence / 217 closure files，全部通过。
- 专用 `MINGLI_PYTHON` provision：Python 3.14.6、PyYAML 6.0.3、sxtwl 2.0.7、astronomy-engine 2.1.19、cnlunar 0.2.4；隔离 origin 与 reviewed-file hashes 通过。
- `bazi_calc.py birth`：产出 `甲戌 / 戊辰 / 丙戌 / 辛卯`，时间政策为 `local_apparent_solar-v1`，记录 astronomy-engine apparent-solar correction。
- 应用层 one-shot smoke：13/13 describe、协议 `mingli-portable-interface-v2`，实际 `Prepare` 返回 Brief 与 state token。
- DeepSeek real-model smoke 未运行：当前没有注入真实凭据；不能把 fake 或 skip 当成模型生产验收。

浏览器截图位于 `docs/releases/evidence/2026-08-13-ui-smoke/web/screenshots/<viewport>/methodology.png` 和 `docs/releases/evidence/2026-08-13-ui-smoke/admin/screenshots/<viewport>/login.png`。最终路由矩阵复用已完成构建的 standalone 服务，并额外直接核验首页与 CSS/JS 静态资源为 200 且 MIME 正确。Web/Admin 日志有代理访问 `127.0.0.1:8000` 的非关键 API 连接拒绝，但文档、脚本、样式、字体无关键错误，测试通过。

### 最新本地复核（2026-08-14）

- `make check`：Backend `607 passed / 90 skipped`；Web `46 files / 358 tests passed`；Admin `10 files / 57 tests passed`；两端 lint、typecheck、production build 与 Backend Ruff/mypy 全部通过。
- Contract suite：`181 passed / 82 skipped`；Token 权威合同单独复核 `25 passed`。
- Web 路由矩阵：4 个视口共 `24 passed`；Admin 路由矩阵：4 个视口共 `16 passed`。两端均通过生产 `/_ui-lab` 404、跳过链接焦点和页面级横向溢出检查；Web 另通过 767/768 导航边界、私有 no-store/noindex，Admin 另通过移动抽屉与全静态路由目录。
- Web legacy `/app/**` 入口改为 Next 配置级临时重定向，360 专项与全矩阵均不再出现中间文档或连续导航 context 销毁；Next 官方语义为临时重定向返回 307，见 [Next.js redirects 文档](https://nextjs.org/docs/app/api-reference/config/next-config-js/redirects)。
- UI Lab 合同与交互测试：`26 passed`；54 条冻结 Web 路线均可发现，预览按 discriminated fixture 组合正式 ProductInputForm、WorkbenchShell、ReadingShell、Account/Auth/Commerce/PublicContentSurface 和 Status，不再使用 bespoke preview shell；`INTERNAL_TEST` 会阻断普通身份，`PAUSED` 只阻断新任务录入并保留历史/阅读边界。
- Web 产品旅程：`12 passed`；覆盖首页→八字录入→确认→工作台、事件/观照/合参输入和双人合盘，四个视口均通过。Admin 内容合同：`8 passed`；覆盖详情状态、列表领域列和无数据时不伪造表格。
- Admin 写操作状态合同新增覆盖：`确认` 独立展示影响范围与确认按钮，`原因` 保留审计原因字段；已有 `无权限`、`只读`、`保存中`、`成功`、`验证失败`、`版本冲突`、`对象已变化`、`审计完成` 分支保持通过。该证据仍只证明 UI Lab 预制，不代表真实服务端写入。
- 视觉抽查：重新生成并查看 360/1440 首页、八字工作台、双人合盘与 Admin 登录截图；未发现可复现的裁切、重叠、低对比或横向布局问题。一次 1440 Admin 无样式截图被后续 1440 smoke 重跑修正，确认是并发旧产物而非当前页面故障。
- P4-005 可访问性合同：Web `20 passed`、Admin `20 passed`；覆盖移动抽屉键盘/焦点回收、Web 任务表单顶部错误摘要与首错聚焦、Admin 登录表单命名、Chrome AX 树地标/表单语义、320/640 CSS 重排等价视口、reduced-motion。具体边界与命令记录在 `docs/releases/evidence/2026-08-13-accessibility/README.md`。
- P1-003/004/005 已依据上述壳层、状态、RBAC、UI Lab 与四视口浏览器证据更新为 `VERIFIED`；P4-006 的参考站同视口差距审阅准备记录见 `docs/releases/evidence/2026-08-14-visual-comparison/README.md`，因仓库没有参考截图仍保持 `NOT_STARTED`。
- 本轮修复并复核首页暗色任务卡的段落文字级联：`.taskCardInk p` 位于通用 `.taskCard p` 之后，使用 `--color-text-inverse`；UI token 合同 `1 passed`，公共样式合同 `4 passed`。
- P1-008 合同脚本：Web/Admin `2 passed`；staged 与 unstaged `git diff --check` 全部通过。
- 以上均为当前工作树本地证据，未创建提交；不能替代 P4-007 用户批准或 P12 真实环境门禁。

## 不能宣称已完成的部分

- P4 的可访问性合同已覆盖代表性壳层和任务表单，但仍不是完整的所有路由/状态、真实屏幕阅读器、原生浏览器 200%/400% zoom、视觉对照审阅，也没有用户逐页批准，因此 P4-007 未完成。
- P6 资料授权/手动合并和真实 PostgreSQL 并发门禁仍未闭环；数据权利本地 API/队列已完成。
- P7 真实支付渠道、验签、查单、退款、对账、通知 worker、正式 Fulfillment API 仍未接通；本地支付确认编排不代表真实到账。
- P8 仍缺真实 API 服务、支付触发、90 天过期、退款例外、风险/申诉和后台漏斗。
- P9 仍缺每日/工具/知识等真实内容消费 API、四角色完整写操作和六组 Admin 聚合读写。
- P10 仅八字原生输入/时间口径/Brief 已通过；正式盘面 ViewModel/免费摘要 API、其余六术及跨术仍未完成。
- P11 的 Guard/PresentationContract、文档落库、claim 核对、反馈和分享快照已有本地证据；同盘 Follow-up 的 Recast/次数/期限/权益占用、PNG/PDF renderer 与短时下载仍未完成。
- P12-001 还需 Mac mini 正式 release root 重跑完整 native-full 1584/0；P12-003/004/005/006/007/009/010 需要真实备份、支付、告警、法律/备案和用户发布批准；P12-002 凭据泄露闭环仍明确 BLOCKED。

结论：本轮完成了“可在当前工作树本地完成的实现、合同和自动化验收”，没有完成生产发布，也没有把预制 UI 或数据模型说成已接真实业务。
