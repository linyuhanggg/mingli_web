# P10-004 双人合盘核心接线（本地与测试服务器）

## 状态

`IN_PROGRESS`。双主体输入、Reading 持久化、产品内结果路由、严格 ViewModel 接线、Runtime 原生关系算法核心，以及本地 v52 的 Worker → Accepted → ReadingDocumentV1 闭环已经完成；每术黄金样例、深读交付、真实服务器 native Runtime、四视口用户批准和生产门禁仍未完成。

## V52 Runtime 原生关系核心

本轮建立 `v52-relationship` release profile，仍保持 13/13 Provider、217 个签名文件、55/55 reference pack、1328 条 evidence 和原有 capability shape；只在 Runtime 的合并边界新增三术关系事实后处理器。随后补齐七政 `dimension_fact_scope` 的 Provider 输出绑定，供三术共同事实范围投影使用。当前 V52 release manifest SHA-256 为 `bef3df256ce06a9796d5eaef999d1141873128fe75b06916922ddd7fe9ac5d50`，describe manifest digest 为 `6118c5f525c87b9cbde95b4d51c945be18bfd18fff8e03306da9fa748b87d917`，source identity 为 `da46e7c0d565fe781e40a115acbb2874c400a195`。

合成双主体真实 one-shot 核验通过：

```text
runtime admission: OK (v52-relationship, 13/13)
bazi: PREPARED / 6 native signals / BaziRelationshipV1
ziwei: PREPARED / 9 native signals / ZiweiRelationshipV1
qizheng: PREPARED / 30 native signals / QizhengRelationshipV1
```

同一份 v52-relationship 制品在本地真实 Worker 矩阵中又通过了三条关系产品：八字、紫微、七政均完成 `Prepare → calculated relationship_signals → Guard → Complete → Accepted → ReadingDocumentV1`，测试结果为 `1 passed`（一个测试循环内覆盖三术）。过程中修正了关系维度允许引用另一主体 calculated source fact 的 Host scope 规则；该例外只对明确列入 relationship scope 的 fact ref 生效，单主体术数仍保持严格主体隔离。

同一 V52 one-shot Runtime 还通过了八字主术 + 紫微 + 七政的三术 Brief：三个术数都返回 `dimension_fact_scope`，Canwen/Hecan 的每个请求维度 `missing_art_ids=()`；投影只显示“所选术数的计算事实范围均已提供”，不把不同术数的范围名称误判成分歧，也不生成实质互证结论。

八字关系事实覆盖跨盘天干五合、地支六合/六冲/六害/六破及可识别三合/三刑；紫微覆盖同名十二宫和命身宫地支结构；七政覆盖经典星体合相、六合相、刑相、拱相、对冲，并按固定容许度输出。每条信号只引用两张单盘的 calculated fact refs，输入事实和浏览器重算均被排除。可复跑入口：`scripts/smoke_local_real_relationship_runtime.py`；需要把 `MINGLI_RUNTIME_RELEASE_PROFILE` 和 V52 路径放进当前私有运行环境，脚本不会输出凭据或原始资料。

烟测对合成双主体固定断言三术 signal ID 集合（八字 `6` 条、紫微 `9` 条、七政 `30` 条），不只检查数量；规则、字段引用或排序语义发生意外变化时会直接失败。

## 本地证据

- Backend 关系/档案授权/同一 SubjectProfile 版本拒绝回归：`23 passed`；此前编译器、迁移和 OpenAPI 定向回归仍为 `93 passed`。
- Web 合盘/API/结果/UI Lab 定向回归：`15 passed`；Web 全量为 `70 files / 438 tests`，Admin 全量为 `33 files / 121 tests`。
- Web `typecheck`、`lint`、production `build` 通过。
- Backend 全量：`868 passed, 107 skipped`；全目录 Ruff 与 `mypy app`（`137 source files`）均通过。另有 v52 关系 Worker 矩阵 `1 passed`，v51 全量矩阵 `2 passed, 1 skipped`。
- 根合同测试：`185 passed, 82 skipped`；UI token 合同 `25 passed`。
- 本机 `alembic check` 无法连接默认 PostgreSQL（本机没有 `mingli` role）；迁移测试通过，测试服务器上的 `alembic upgrade head` 与 `alembic check` 均通过。

## 接入内容

- 三条独立 API：`bazi-relationship`、`ziwei-relationship`、`qizheng-relationship`。
- 两个 ProfileVersion ID、关系类型、关系维度持久化；双方必须属于当前 owner 且不能相同。
- 三个关系 product 的输入、授权、持久化和严格 ViewModel 接口。
- 关系层只消费 Runtime 已计算的事实、信号和 fact refs，不在业务后端复制八字、紫微或七政算法；没有原生关系事实时保持空结果。
- 真太阳时和七政输入在页面与编译器分别要求坐标/来源，不把缺失坐标静默当成民用时。
- 生产/real-traffic gate 已额外阻止三个尚未完成 P10/P11/P12 的合盘 product，即使底层 capability 恰好是 P0 的 `bazi`。

## V51 真实 Runtime 历史核验

使用合成双主体输入调用本机真实 one-shot Runtime；不写入个人资料、仓库或证据正文：

```text
bazi    PREPARED：两主体独立事实返回；无 Runtime-native relationship_signals
ziwei   PREPARED：两主体独立事实返回；无 Runtime-native relationship_signals
qizheng PREPARED：两主体独立事实返回；无 Runtime-native relationship_signals
```

这段是 V52 关系后处理器之前的 V51 基线，保留用于说明为什么不能把两张独立单盘硬拼成合盘。当前关系核心证据以上方 V52 记录为准。

## 测试服务器发布（当前）

当前应用 release 已包含授权边界、产品内结果路由、Runtime-native fact-only 投影、V52 三术关系核心、UI token 修复和生产构建的 Suspense 修复；API/Worker 守护进程仍使用 `local + Fake`，不把 V52 切成常驻服务。

```text
server: fateradar-prod（代码联调与验收机，不是 production）
release: ui-preview-20260815-crossscope
archive_sha256: 8d0dcf69e330eb291130d5dca2af6d093c7125172080cd04a54cffe8e81ea822
source_kind: 当前工作树应用快照；不是干净 Git commit
database_schema_head: 0034_reading_relationship
pre_migration_backup: 本版 `alembic check` 显示无新迁移，因此没有执行数据库写迁移
server_manifest: /opt/fateradar/shared/cache/ui-preview-20260815-crossscope.tar.gz（归档 SHA 已核对）
```

### 2026-08-15 测试服务器 V52 native Runtime 与 Worker 补验

为完成关系核心的服务器验证，在不改变守护进程配置的前提下，将 V51 与 V52 实际差异的三个 Runtime 文件及签名清单安装到：

```text
/opt/fateradar/shared/mingli-master-v52-relationship
manifest_sha256: bef3df256ce06a9796d5eaef999d1141873128fe75b06916922ddd7fe9ac5d50
describe_manifest_digest: 6118c5f525c87b9cbde95b4d51c945be18bfd18fff8e03306da9fa748b87d917
```

在服务器临时 state 目录中完成真实 Runtime admission 和内存 Worker 验收：

```text
admission: 13 capabilities
bazi: accepted bazi-relationship/v1
ziwei: accepted ziwei-relationship/v1
qizheng: accepted qizheng-relationship/v1
relationship_signals: 6 / 9 / 30
API/Worker after hotfix: active; live=200; ready=200; NRestarts=0
```

服务器应用只同步了关系 scope Guard 修复，旧文件备份在
`/opt/fateradar/shared/cache/narrative-guard-20260815/narrative_guard.py.before`；三术测试使用合成主体和内存 Repository，没有写入测试数据库。V52 仍是一次性 native 验收制品，不代表生产 Runtime 或公开上线。

服务器检查通过：

- `/bazi/hepan`、`/ziwei/hepan`、`/qizheng/hepan`、`/hecan`、`/canwen`、`/wenshi`、Admin `/login` 最终返回 200（`/canwen` 的无尾斜杠入口会先返回正常 308，再到 200）；首页抽取的 Next 静态资源返回 200。测试机页面诚实显示 Fake/Runtime 原生关系事实边界，不展示伪造信号。
- API live/ready、Nginx healthz 返回 200；OpenAPI 含三个合盘 operation。
- API、Worker、Web、Admin、Nginx 全部 active；首次启动和重启后均等待冷启动完成，live/ready 和产品路由再次返回 200。
- 新 release 的 standalone 资产已通过官方 `start-standalone.mjs --prepare-only` 补齐；目录权限已修正为 `fateradar` 可读可执行。旧 current、上一版 Hecan、Wenshi 和 relationship 回滚版本保留；本次迁移前 dump 与 SHA 已记录。

### 2026-08-15 结果文档只读接线热更新

在上述验收 release 上又同步了一个已通过本地回归的 P11 兼容接线：`GET /api/v1/readings/{reading_version_id}/result` 现在明确返回 `document` 字段；没有合法落库 `ReadingDocumentV1` 时返回 `null`，已有文档才返回加密仓储解出的公开文档。此次没有数据库迁移，也没有生成假文档。

服务器热更新前备份保存在 `/opt/fateradar/shared/cache/backup-result-document-slot-20260815/` 和 `/opt/fateradar/shared/cache/backup-result-document-slot-viewmodel-20260815/`；最终同步文件 SHA 为：

```text
backend/app/readings/api_schemas.py  0e238f6a9f7d3c0d7932f511515df0d1dd39e94729b13e04b56eb2cf258fce83
backend/app/readings/service.py       0d50c9475d563a445ccbb288c9848ec869863d08594537ba826760bdd30ec6eb
```

API/Worker 重启后均为 `active`，live/ready 和 `/api/openapi.json`（`ReadingResultResponse` 同时要求 `view_model`、`document`，并含 `ReadingDocumentV1`）返回 200，五个服务 `NRestarts=0`，近五分钟 error journal 为空。这个热更新只推进结果交付接线，不把 P11 深读生成、真实 Worker、PNG/PDF 或 P12 生产门禁标记为完成。

## 用户浏览入口

```bash
ssh -L 18080:127.0.0.1:8080 -L 13001:127.0.0.1:3001 fateradar-prod
```

- Web：`http://127.0.0.1:18080/bazi/hepan`
- 紫微：`http://127.0.0.1:18080/ziwei/hepan`
- 七政：`http://127.0.0.1:18080/qizheng/hepan`
- Admin：`http://127.0.0.1:13001/login`

测试服务器只用于虚构数据浏览，不是生产；P4-007 仍等待用户逐页浏览并明确批准。用户批准应以本次 release 的页面为准。
