# P11-002 AcceptedCopy → ReadingDocumentV1 构建接线（2026-08-15）

## 状态

`IN_PROGRESS`。本轮补齐了已接受候选从 Runtime brief、NarrativeCandidate 和 AcceptedCopy 到类型化 `ReadingDocumentV1` 的本地/测试机接线，并补齐梅花、禄命/纳音、太乙、择日、风水五类冻结 ViewModel 合同；P11-002 仍不标记完成，因为真实生产 Worker、每术黄金样例、PNG/PDF 和最终发布门禁仍缺。

## 本轮完成

- `ReadingDocumentBuilder` 只消费 Guard 已通过的 Candidate 和 Runtime 已计算事实，通过现有 `project_runtime_view_model()` 生成严格 ViewModel。
- 支持已有的单术、合参和关系 ViewModel；没有类型化公开 ViewModel 的能力会返回 `None`，不会伪造一张报告。日运继续保持事实面板路线，不被硬套成图盘。
- Accepted 后由同一个 Worker 数据库事务读取加密 GenerationAttempt、构造 AcceptedCopy 引用并写入不可变 ReadingDocument；同一版本仍遵守 first-write-wins。
- Repository 只会读取 `guard_errors` 为空的成功候选，避免把最新一次 Guard 失败候选投影成最终文档。
- 追加原子交付门禁：SQL Worker 配置了 `ReadingDocumentBuilder` 时，除 `fortune` 事实面板外，Accepted 阶段若缺少成功 Candidate、Typed ViewModel 或 ReadingDocument 会抛出不变量错误；外层事务会同时回滚 AcceptedCopy、ReadingDocument 和 Accepted 状态，不再留下 Accepted-only 半成品。`fortune` 保留明确的事实面板例外。
- `contracts/schemas/reading-document-v1.schema.json` 和 `contracts/schemas/views/**` 已覆盖全部当前类型化 ViewModel；结果页没有合法文档时不显示分享/追问入口，避免把事实结果冒充完整交付报告。
- Web 共享文档的 `view_model` 已收紧为同一 `ViewModel` 联合类型，不再以 `Record<string, unknown>` 绕过结果合同。
- 新增结果文档构建器单测、Orchestrator 接线单测和真实 SQLite 加密 Repository 读回测试；没有写入个人资料、密码、API key 或生产秘密。

### 2026-08-15 真实 Runtime → Worker → ReadingDocument 矩阵

新增 opt-in `backend/tests/test_runtime_worker_document_matrix.py`，使用本机冻结 v51 one-shot Runtime、`FakeModelGateway`（只负责合同测试候选，不负责算法计算）和真实 `ReadingOrchestrator`，逐条执行 `Prepare → Prepared → Worker Guard → Complete → Accepted → ReadingDocumentV1`：

- 13 个单术数 provider 全部通过；其中 12 个生成对应 typed ViewModel/ReadingDocument，fortune 按设计只生成事实面板，不伪造 chart。
- Canwen、Hecan、Wenshi 三个合参产品全部通过 typed ReadingDocument。
- 矩阵过程中修正了一个真实 Host 接入问题：多 provider Brief 的同维度 `claim_scopes` 不能用最后一条覆盖，改为事实/证据/允许类型并集，certainty ceiling 取更严格者；维度限定的 `limit` 也按 subject 或 dimension 适用范围闭合。
- 真实矩阵结果：`2 passed in 19.89s`；Guard/引用回归 `27 passed`；Backend 全量 `865 passed, 107 skipped`。
- 矩阵还会逐个检查 Runtime brief 的 `fact:{subject}/calculated/{provider}/…` 引用；13 个单术数和合参中的每个 required comparison 都必须有对应计算命名空间，并对主 Provider 检查最小核心字段（如八字 `day_master`、六爻 `changed_hexagram`、奇门 `board_digest`、大六壬 `four_lessons`、相法 `normalized_visible_observations`）。对应 calculated fact 的值也必须至少有一个非空结果；允许业务上为空的字段（例如没有满足约束的择日候选、该样例没有年度变换）只要求引用存在，不被误报为算法失败。只有 input facts 或页面 schema 不能通过。最新真实矩阵为 `2 passed, 1 skipped`（20.01s），证明本机 V51 跑到的是各 Provider 的计算事实，不是空壳投影。
- 另加了 v52-relationship 的三条关系 Worker 验收用例；本地和测试服务器都以签名 v52 制品跑通八字、紫微、七政的 `relationship_signals → Accepted → ReadingDocumentV1`，本地矩阵结果为 `1 passed`，服务器内存 Worker 三术均 Accepted。测试服务器守护进程仍保持 local + Fake，不把一次性 native 验收误称为常驻真实 Worker。

这证明当前本机 v51 的单术数与三术合参、本机 v52 的八字/紫微/七政关系产品，以及测试服务器的一次性 v52 native Worker，都已经接到 Worker 和类型化结果文档。没有用 v51 的两张独立命盘冒充关系信号。

## 本地门禁

```text
Backend pytest: 831 passed, 102 skipped
Backend Ruff: passed
Backend mypy: passed, 134 source files
Web: 70 files / 441 tests passed; lint/typecheck/build passed
Admin: 33 files / 121 tests passed; lint/typecheck/build passed
```

本轮回归后的 Backend 全量为 `868 passed, 107 skipped`；真实 v51 Runtime 矩阵为 `2 passed, 1 skipped`，真实 v52 关系矩阵为 `1 passed`。上面的旧数字保留作本轮前基线。

## 测试服务器

服务器：`fateradar-prod`，当前仍是 `local + Fake` 验收机，不是 production。代码同步到 `/opt/fateradar/current` 指向的 `ui-preview-20260815-public-products`；API、Worker、Web、Admin、Nginx 均 active，导入、live/ready、Web 入口和 OpenAPI `document` 字段检查通过。

更新前备份保留在：

```text
/opt/fateradar/shared/cache/backup-reading-document-builder-20260815/
```

新增的 `backend/app/readings/presentation/builder.py` 在旧 release 中不存在，备份目录明确记录了这一点；临时上传目录已清理。测试服务器只用于用户浏览，不代表真实 Runtime、生产支付、备案或公开上线。

### 2026-08-15 结果页热更新

在同一测试 release 上补发结果页动作门控和关系产品无 ViewModel 时的渲染边界修复。服务器端 production build、standalone 启动和 Nginx 入口复验通过；`/bazi`、`/ziwei`、`/qizheng`、`/liuyao`、`/meihua`、`/qimen`、`/daliuren`、`/wenshi`、`/hecan`、`/luming-nayin`、`/taiyi`、`/selection`、`/fengshui`、`/jianxiang` 及 `/healthz` 均返回 200。原结果页保存在 `/opt/fateradar/shared/cache/reading-result-hotfix-20260815/reading-result.tsx.before`，测试机仍是 `local + Fake`，P4-007 仍等待用户逐页浏览批准。

### 2026-08-15 Host scope merge hotfix

将本轮 `narrative_contracts.py`、`candidate_reference_closer.py`、`narrative_guard.py` 同步到测试机当前 release；同步前备份在 `/opt/fateradar/shared/cache/host-scope-merge-20260815/`。三文件远端 SHA-256 与本地一致，API/Worker/Web/Admin 重启后均 active、`NRestarts=0`；`/api/v1/health/live`、`/api/v1/health/ready`、`/healthz` 和 14 个术数入口均返回 200。该同步只更新测试机 Host 合同处理，不改变测试机 `local + Fake` 性质。

### 2026-08-15 测试服务器真实 Runtime 单次核验

验收机当前 release 仍为 `ui-preview-20260815-public-products`，服务环境明确是 `MINGLI_RUNTIME_ADAPTER=fake`、`MINGLI_MODEL_ADAPTER=fake`，因此没有把页面或守护进程误称为真实算法 Worker。服务器已有 `/opt/fateradar/shared/mingli-master` 的签名 V51 Runtime；在不改 systemd、不切换服务的临时覆盖环境中：

- Runtime admission 返回 `13` 个 capability；
- 使用合成资料跑一次真实八字 Prepare，返回 `Prepared`，并发现 `14` 个 `/calculated/bazi/…` fact refs；
- 临时 state 目录已清理，服务配置和 DeepSeek 凭据未改动。

这只证明服务器签名 V51 Runtime 与本机路径可启动，并补了一条真实 Provider 轨迹；不证明测试服务已切到真实 Runtime、不证明 13 个服务器 Provider 全量 Worker，也不替代生产准入。

### 2026-08-15 原子文档门禁热更新

- 在当前 `ui-preview-20260815-public-products` 上热更新 `backend/app/readings/orchestrator.py` 与 `backend/worker/readings.py`；更新前文件备份在 `/opt/fateradar/shared/cache/reading-document-atomic-hotfix-20260815/`。
- 真实 one-shot Worker/矩阵默认开启 `require_reading_document`：除 `fortune` 事实面板外，缺少 Candidate、Typed ViewModel 或 ReadingDocument 会使 Accepted 阶段失败并由 Worker 外层事务回滚；测试机 systemd 仍是 `local + Fake`，因此不宣称它已切真实算法。
- 后端 import、API/Worker 重启、API live/ready、Web `/bazi`、`/tools/five-elements`、Admin `/login`、Nginx 和五个服务均复验通过；四个应用服务 `NRestarts=0`。无数据库迁移。
- 服务器浏览入口保持：`http://127.0.0.1:18080/bazi`、`http://127.0.0.1:18080/tools/five-elements`；Admin：`http://127.0.0.1:13001/login`。仍只供虚构数据验收，P4-007 需要用户浏览批准。

## 仍缺的核心/产品边界

13 个 Runtime Provider 的计算入口、单术数 Worker 闭环和严格 ViewModel 已在本机 v51 通过；这不等于 13 个完整商业交付产品。禄命/纳音、太乙、择日、风水、相法仍需要黄金样例、深读、导出和生产发布状态；相法的本地媒体采集、质量和授权 Adapter 已接入，生产对象存储仍缺。Canwen/Hecan/Wenshi 已通过当前 v51 的事实合同和 Worker 文档闭环，但合参仍缺权威的实质互证/分歧规则。双人合盘仍缺测试机/生产 native v52 Worker→ReadingDocument 轨迹。日运保留事实面板，不伪造 chart ViewModel。以上边界仍按 P10/P11/P12 清单执行。

### 2026-08-16 ProductVersion 合同快照接线

- SQL Repository 从不可变 `ReadingRoot.product_version_snapshot_id` 读取 `ProductVersion` 与 `ProductFamily`，生成固定的 `product_version` 和 `presentation_contract_version`，沿 `ReadingJob → ReadingDocumentContext → ReadingDocumentBuilder` 传递；自由预览没有商品快照时继续使用既有 fallback，不修改历史文档。
- 本地定向回归：`test_reading_document_builder.py`、`test_reading_repository.py` 共 `14 passed`；Worker/履约/API 定向回归 `74 passed / 10 skipped`；配置过的 mypy `142 source files` 无错误，受影响 Ruff 通过。
- 已同步到测试机当前 release `ui-preview-20260815-public-products`。更新前源码备份在 `/opt/fateradar/shared/cache/product-version-contract-hotfix-20260816/`；三份服务器文件与本地 SHA-256 一致。API、Worker、Web、Admin、Nginx 均 active，live/ready、回环 healthz、`/bazi` 返回正常，API/Worker `NRestarts=0`。
- 测试机仍是 `local + Fake`，没有切换真实 Runtime、支付或生产凭据；本节不把测试服务器当作生产准入，也不包含个人资料或秘密。

### 2026-08-16 PostgreSQL 与真实 Runtime 复验

- 本机 PostgreSQL 16 `mingli_test` 的 `backend/tests/test_reading_worker.py` 为 `20 passed`，覆盖 Accepted/ReadingDocument 事务边界、Complete 重放、租约 fencing、幂等并发和故障恢复。
- 受保护 one-shot V51 环境下，真实 Runtime→Worker→ReadingDocument 定向矩阵为 `8 passed / 1 skipped`；skip 仅是未安装匹配的 V52 relationship release。P11-002 的真实生产 Worker、生产数据库故障注入和外部验收仍未完成。

### 2026-08-16 Runtime evidence lane 接线回归

- 真实 V51 单术数 Worker 矩阵新增 `evidence`/`limits` 互斥边界和引用闭合检查：Runtime brief 必须提供来源证据或明确限制；来源证据只能支持同一 brief 的事实，finding 只能引用已返回的证据。
- Accepted 生成的 `ReadingDocumentV1.evidence` 与 Prepared brief 的 Runtime evidence refs 逐项相等，真实矩阵 `1 passed`。这证明来源证据没有在 Host 投影或文档落库阶段丢失；它仍不代表深读规则、合参结论或生产 Runtime 已完成。

### 2026-08-16 V52 关系 ReadingDocument 复验

- V52 relationship release 的八字、紫微、七政关系 Worker 矩阵重新完成 `1 passed`；每个请求都保留 Runtime 原生 `relationship_signals`，并在 Accepted 后生成对应的关系 `ReadingDocumentV1`。
- 本次复验只确认关系信号从 Runtime 进入 Worker、Guard 和不可变文档；合参的实质互证/分歧规则仍未生成，不能把结构化信号写成最终关系判断。

### 2026-08-16 关系引用闭合 hotfix 测试机同步

- 关系投影现在拒绝同一 brief 中不存在的 Runtime `fact_refs`，并保留旧文件备份 `/opt/fateradar/shared/cache/relationship-fact-ref-hotfix-20260816/`。
- 测试机 API/Worker/Web/Admin/Nginx active，API live/ready、`/healthz`、三个合盘入口和 Admin 登录页均 `200`；本次只更新测试机 Host 投影合同，不改变 `local + Fake` 边界，也不把它写成生产 Worker 证据。
