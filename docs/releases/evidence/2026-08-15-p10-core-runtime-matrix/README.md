# P10 核心 Runtime 版本矩阵复核

日期：2026-08-15

## 当前算法接入审计（不是完整产品发布结论）

这次审计把“核心 Provider 已接入”与“对应术数已经具备完整公开产品能力”分开记录：前者检查 Runtime 的确定性事实是否经过 Request Compiler、Worker、Guard、Typed ViewModel 和 ReadingDocument；后者还要检查正式规则包、黄金样例、深读/追问和发布门禁。按这个口径，当前缺口如下。

| 对应术数/产品 | 核心事实接入 | 目前还缺的算法或产品层 |
|---|---|---|
| 八字 | 已接入 `bazi`；真太阳时、四柱、藏干、十神、日主、月令、大运序列、有界解释候选，以及指定年/月/日层已能跑通 | Runtime 明确把旺衰、格局、从化、用神排序保留为 `evidence_only`；还没有可发布的硬裁定规则包、逐术黄金样例和完整深读链 |
| 紫微斗数 | 已接入 `ziwei`；命宫、星曜、四化、限层、指定年层和月度层可投影 | 完整发布版黄金样例、深读/追问和真实 Worker/生产 Runtime 证据仍缺 |
| 七政四余 | 已接入 Runtime `xingming`，产品动作使用 `qizheng` 名称；星体、宫位、命身和限层可投影 | 三术合参的权威互证/分歧规则仍缺；单术公开深读和生产门禁仍缺 |
| 六爻、梅花 | 六爻已接入；梅花五种起法字段也已接入，不能互相静默替代 | 目前主要是盘面/关系事实；完整断法、深读黄金样例、真实 Worker 和发布门禁仍缺 |
| 奇门遁甲、大六壬 | 局盘、九宫/星门神、四课三传、时空事实已接入；大六壬事件时间别名已修正 | 问事三术只完成结构和事实范围；实质互证/分歧规则、深读和生产证据仍缺 |
| 问事合参 | `六爻 + 奇门 + 大六壬` 三术结构已接通，缺失会诚实显示 | 还没有 Runtime 原生的实质性 convergence/disagreement 结论，不能宣称三术合断完成 |
| 命盘合参/合盘 | 八字/紫微/七政关系 Runtime 已有原生 `relationship_signals`；共同事实范围也已接通 | 合参的权威解释规则、深读/追问、公开发布与生产 Runtime admission 仍缺 |
| 禄命纳音、太乙、择日、风水 | 五个内部 Provider 中对应的四类事实输出已接入产品纵切片；候选排序和风水观测边界保持事实化 | 仍缺各自正式商品合同、深读、黄金样例、真实 Worker 和生产门禁；风水不是自动替代现场勘验 |
| 相法 | `physiognomy` 只接结构化可见观察和 face 模式，媒体本地私有链已接通 | 手相、体态、综合模式明确未接；生产对象存储、正式用户授权和完整发布链仍缺 |
| 每日/工具 | `fortune` 是事实面板；五行事实、音律纳音、八字同盘已有独立 Provider/VM/API/UI 纵切片；V53 新增寻时定盘的十二时辰事实 Provider | 解梦、姓名分析仍没有正式规则包、输入输出合同、黄金样例或 Provider；寻时目前只枚举事实，不做事件匹配、淘汰或排名 |

所以当前答案是：**V51 的 13 个已登记核心 Provider 已完成接线，V53 另完成寻时定盘的有界事实接线；还没有完成的是各术数的权威解释层、合参实质结论、解梦/姓名分析两项工具算法，以及每一项的完整公开产品/生产验收。**

### 三项工具的历史资料核对

- **寻时定盘**：V53 已完成“重算确定性盘面 → 应用出生地真太阳时 → 枚举 12 个时辰事实”的 Provider/Worker/ViewModel 接线，并把已知时间范围标在每个时辰上；仍没有已审核的事件特征、权重、淘汰和排序规则，因此不能生成匹配结论或排名。
- **解梦**：资料库里出现过六壬类象中的梦寐/梦象材料，但它依赖具体六壬盘的神将、所临和状态，不能直接当成独立、通用的梦境解释 Provider；当前没有独立输入合同和适用性裁判。
- **姓名分析**：当前 Runtime、历史源码和参考目录没有可审计的姓名学规则包或笔画/字典口径；不能自行选“康熙笔画、五格、三才”中的一套作为正式算法。

解梦和姓名分析缺的是正式方法与可验收规则，不是前端页面接线；寻时则已完成有界事实层，仍缺事件匹配与排序方法。方法、字典口径和黄金样例冻结后，才可以进入 `P10-013` 的完整 Provider→Worker→ViewModel 纵切片。

### 本轮真实回归（2026-08-15）

- 用户明确授权的个人资料只在一次性进程和临时 Runtime 状态目录中使用；15 个已登记单术/工具用例全部返回 `Prepared`，Runtime admission 为 `13/13`。没有把个人姓名、出生时间、地址或坐标写入仓库、证据正文、服务器或记忆。
- Provider→产品动作映射合同定向回归 `28 passed`；相法、显示层和工具边界合成资料回归为后端 `29 passed / 12 skipped`、Web `38 passed`。
- 真实 V51 Worker 矩阵为 `3 passed / 1 skipped`：13 个单术 Provider 均完成 `Prepare → Worker → Accepted → ReadingDocument`；唯一 skip 是当前环境未安装的 V52 relationship release 条件，不把它记作通过。

### 本轮新增：八字有界解释证据接线（2026-08-15）

- 将 V51 Runtime 已有的 `interpretive_candidates` 接入后端 `BaziCoreFacts`、`FiveElementsFactsViewV1`、`reading-document/v1`、前端 ViewModel 和五行事实结果表；页面展示强弱原始证据、月令结构候选、合化/从格候选和机械显著信号，但明确不生成旺衰、喜忌、用神或吉凶硬结论。
- 八字主结果页 `bazi-chart/v1` 也消费同一组 Runtime 候选：主命盘的“Runtime 已计算事实”现在同时展示强弱证据、月令结构、合化/从格候选、机械显著信号和证据边界；共享格式避免五行事实页与主命盘出现不同口径。该页仍不在浏览器重排，也不把候选升级为吉凶结论。
- 用户授权的临时个人输入只在进程内做真实 one-shot Runtime smoke，未写入仓库、服务器、证据正文或记忆。真实结果成功投影：13/13 capability admission、日主元素 earth、同类出现 5、生扶 fire 出现 3、结构状态 `candidate_only`、7 个机械信号、`hard_verdict=None`；独立 `five-elements-facts-view/v1` JSON Schema 校验通过。
- 本地回归：后端 `882 passed / 107 skipped`，Web `70 files / 443 tests`，Admin `33 files / 121 tests`，mypy 141 source files；Ruff 全量通过，两端 typecheck、lint、production build 通过。
- 测试服务器 `ui-preview-20260815-public-products` 已热更新并重建 standalone；API live/ready、`/tools/five-elements`、`/bazi` 均 200，页面新标题“**五行事实与调候**”已生效，主命盘源码已包含候选边界说明。web 重启时补建了 systemd namespace 所需的 cache/server 目录；四个 test unit 最终均 active。该服务器仍是测试环境，不代表生产 Runtime 或 P12 外部门禁。

### 本轮追加合同复核（2026-08-15）

- `reading-document/v1` 已把 Bazi/Five Elements 的 `interpretive_candidates` 挂入严格 schema：四个候选入口必填，`status` 固定为事实/候选状态，`hard_verdict` 固定为 `null`，嵌套对象拒绝未声明字段；正向与缺字段、错误状态、额外字段负向合同测试共 37 项通过。
- 真实 V51 Worker 单术矩阵在启用真实 Runtime 后通过：`1 passed / 2 deselected`。八字黄金事实现在额外固定 `strength=evidence_only`、同类 3、生扶 4、结构 `candidate_only`、9 个机械信号，以及三个候选区块不产生硬裁定。
- 当前工作树 `make check` 通过：Backend `882 passed / 107 skipped`、Web `70 files / 443 tests`、Admin `33 files / 121 tests`；Ruff、mypy、两端 lint/typecheck/production build 全通过。

## 这次确认了什么

核心 Runtime 的“算法 Provider → Request Compiler → Prepared → 严格 ViewModel”链路已按已登记 release profile 复核。公开产品仍按产品合同组织，不直接暴露 Provider 内部键或原始 Runtime 结果；本轮又把禄命/纳音、太乙、择日、风水四个产品输入/API/UI 纵切片接上。

### 本轮最终复核（2026-08-15）

- 修正了一条过时的大六壬黄金断言：当前锁定的 V51 Runtime 对同一合成事件稳定返回第一课 `辛/戌 → 申/比和`，而不是旧测试写死的 `酉/比和`；没有修改 Runtime 算法。
- 修正后真实 V51 Worker 矩阵为 `2 passed / 1 skipped`：13 个单术 Provider 全部完成 `Prepare → Prepared → calculated facts → Guard → Complete → Accepted → typed ReadingDocument`，关系矩阵也通过；唯一 skip 是本机未安装的 V52 relationship release 条件用例。
- 新增的五行事实/调候有界产品以临时授权输入实际跑通真实 V51 Runtime 与 Worker，返回 23 条事实、14 条 calculated facts，最终 `Accepted` 并生成 `reading-document/v1`；当前来源状态诚实显示为 `identity_only`，因为该 Runtime 返回来源身份但没有逐条 source rule ID。这一切不等于已经完成旺衰、喜忌或用神结论。
- 测试服务器 `ui-preview-20260815-public-products` 已以可回滚热更新接入五行页面、`startFiveElementsFactsReading` OpenAPI/API、ViewModel 合同和结果页；备份位于 `/opt/fateradar/shared/cache/five-elements-facts-hotfix-20260815/`。服务器 backend import、Nginx `/healthz`、API live/ready、Nginx `/tools/five-elements`、Admin `/login`、Web standalone build（`BUILD_RC=0`）和四个 test unit 均通过，四个 unit `NRestarts=0`。测试机当前 venv 仍未安装 Pillow/reportlab，因此 PNG/PDF 导出保持明确 unavailable；没有把它写成导出已完成。
- 本轮结束时本地完整 `make check` 为 Backend `882 passed / 107 skipped`、Web `70 files / 443 tests`、Admin `33 files / 121 tests`，Ruff、mypy、两端 lint/typecheck/production build 全通过。

- 本机 V51 真实 one-shot Runtime：内部/composite Provider 回归 `test_runtime_process_adapter.py -k frozen_runtime` 为 `10 passed / 16 deselected`；公开核心回归 `test_runtime_public_core_process.py` 为 `2 passed`，覆盖八字、紫微、七政、六爻、大六壬和 fortune 事实面板。
- 本机 V51 真实 one-shot Worker 矩阵新增覆盖全部已登记的 13 个单术 Provider：一个测试循环逐项完成 `Prepare → Prepared → calculated facts → Guard → Complete → Accepted → typed ReadingDocument`，fortune 保持事实面板不伪装成 chart；矩阵用例 `1 passed`（本轮与冻结 Runtime 回归合计 `11 passed / 18 deselected`）。
- 同一 13 Provider Worker 矩阵新增最小语义黄金断言：固定四柱/日运周期、紫微历法引擎、七政星体集合、六爻变卦、梅花体用、纳音谱系、太乙盘位、择日候选计数与排序策略、风水朝向、奇门局式、六壬四课和相法可见观察；明确排除生成时间、digest 与候选 opaque ID 等实现噪声。真实 V51 回归仍为 `1 passed`，当前默认后端全量为 `882 passed / 107 skipped`。
- V51 的 Canwen 三术结果按历史合同返回八字、紫微范围，七政 `missing_art_ids=("qizheng",)`，且不生成三术齐全的 convergence；测试已按 release profile 固定这一边界。
- 本机 V52 relationship release 的同一 Canwen 三术用例为 `1 passed / 25 deselected`；三术均返回 `dimension_fact_scope`，每个请求维度无缺失，并生成“范围齐全、尚未形成实质互证”的结构提示。
- 本机 V52 relationship release 真实 Worker 矩阵重新复跑为 `1 passed / 2 deselected`：八字、紫微、七政关系请求均完成 `Prepare → calculated relationship_signals → Guard → Complete → Accepted → ReadingDocumentV1`；独立关系 smoke 同时通过 `13/13` admission 与原生信号数量 `6 / 9 / 30`，不接受输入事实引用或浏览器重算。
- 本机 V51 真实 Worker 矩阵重新复跑为 `1 passed / 2 deselected`；新增语义黄金断言只固定稳定算法事实，关系请求不误套单人盘黄金值。当前默认后端全量为 `882 passed / 107 skipped`，Web 全量为 `70 files / 443 tests`。
- 核心 Provider→产品动作反向覆盖合同已补齐：13 个 V51 Provider 均有显式产品动作，且锁定七政→`xingming`、五行事实→`bazi`、节律→`luming-nayin`、问事→六爻主术+奇门/大六壬 comparisons；定向映射回归 `25 passed`，新增合同后的完整 `make check` 为 Backend `909 passed / 110 skipped`、Web `71 files / 448 tests`、Admin `33 files / 121 tests`。
- 用户授权的临时个人输入真实 Runtime smoke 已通过；只使用临时状态目录，个人输入未写入仓库、服务器、证据正文或记忆。
- 同一临时真太阳时核验覆盖八字、紫微、七政、禄命/纳音和 fortune；产品 `solar` 明确编译为 Runtime `local_apparent_solar-v1`，子时 `solar` 编译为 `midnight`，五项均返回 `Prepared`，个人资料未落盘。
- Web 结果层现已注册并分派 `luming-nayin-chart/v1`、`taiyi-chart/v1`、`selection-chart/v1`、`fengshui-view/v1` 四个内部 ViewModel；`RuntimeChart` 以现有事实表组件展示四柱/周期/候选/观测状态，结果页白名单也会消费它们。Web 受影响回归为 `7 passed`，全量为 `70 files / 441 tests`，typecheck、lint、production build 均通过。
- 四个产品已分别拥有公开本地入口和 API：`/api/v1/readings/luming-nayin`、`/taiyi`、`/selection`、`/fengshui`，以及 Web `/luming-nayin`、`/taiyi`、`/selection`、`/fengshui`。后端读取 API 定向回归 `53 passed`，OpenAPI 对齐 `6 passed`；本轮以 `backend` 项目目录为工作目录重跑后端全量回归，结果更新为 `882 passed / 107 skipped`。
- 修复 fortune 产品入口断线：私有 `/app/fortune/today` 与 `/app/fortune/week` 不再跳转到不可用的公共 `/daily` CMS 页面，而是直接承载已有 `FortuneFlow` 和 `/api/v1/readings/today|week` 合同；定向 Web 回归 `26 passed`，全量 `70 files / 441 tests`，typecheck、lint、production build 均通过。公开 `/daily` 继续只承担每日公开内容，不混入个人档案运算。
- 进一步修复 Next 请求层遗留 redirect：从 `web/next.config.ts` 删除两个把私有 fortune 入口送往 `/daily` 的规则，并用实际配置合同锁定；定向回归增至 `27 passed`。测试机当前 `ui-preview-20260815-public-products` 已同步该热更新，Web build/standalone prepare 与全服务重启后的第二轮健康检查通过，两个私有入口均 200 且无 `Location`，服务器仍为 `local + Fake`。

## V53 寻时定盘事实层补充（2026-08-15）

- V53 Runtime capability `time-check` 已通过 `describe → prepare → Worker → Accepted → ReadingDocumentV1`，完整矩阵为 `14/14`；V51 原有 13 项和 V52 八字/紫微/七政关系矩阵也分别通过。
- 输入/API/UI 使用公开维度 `time_options`。Runtime 返回 12 个时辰、对应八字四柱、日主、候选当地民用时间和真太阳时归一化事实；时间范围只标记是否落入已知范围。
- `ranking_status=not_ranked`、`event_matching_status=not_calculated` 保持明确，不把事件文本直接变成权重或吉凶结论。公开页面只消费 Typed ViewModel，不在浏览器重算。
- V53 release manifest SHA-256 为 `55efe80255b6f5ad9c6c9c226d9f8f95af3213a2d941ae5258a7f6ff5d05fada`；该 release 仅是本机/测试用受控制品，不等于生产 admission。

## 当前核心层结论

已接入的核心模块包括八字、紫微、七政、六爻、梅花五种起法、奇门、大六壬、问事三术结构、命盘合参结构，以及禄命纳音、太乙、择日、风水、相法五个 Provider；V53 另接入寻时定盘的十二时辰事实层。前四个本轮已补产品输入/API/UI 入口；相法已有私有媒体与结构化观察纵切片。`fortune` 保持 P0 的时间事实面板，不伪装成命盘型 ViewModel。

## P12-001 证据边界

2026-08-15 对历史 `docs/releases/evidence/2026-08-09-native-full/` 做了独立复验。历史 `prepared-inputs.json` 绑定的 source、research、native runtime 和 release manifest 位于已消失的临时目录，`verify_local_full.py` 因 `source.release_manifest` 不再是当前可读文件而拒绝加载。因而历史 `1584/0` 不能作为当前可复验的 Mac mini native-full 通过证据；没有用普通业务测试替代这条门禁。P12-001 仍需在 Mac mini 上用新一套匹配的 release manifest、PreparedInputs 和 native-full runner 重跑。

## 仍未完成

这份复核不代表 P10/P11/P12 完成。V51 的 13 个 Provider 已完成本地真实 Worker/ReadingDocument 矩阵，V53 的寻时定盘事实 Provider 也已通过 14 项矩阵；但各术数仍缺完整发布版黄金样例、深读、追问、导出分享和生产 Runtime admission，合参仍缺权威的实质互证/分歧规则。五行事实切片只完成盘面库存与调候标记的事实展示，不是完整旺衰/喜忌/用神产品。相法的 HTTP 上传、数据库记录、前端 File 选择和结构化观察提交已在本地接通，生产对象存储和用户外部验收仍缺。剩余仍未接入规则包/Provider 的工具是解梦、姓名分析两项；寻时还缺事件匹配、淘汰和排名规则。P4-007 用户逐页批准、真实生产凭据、备份恢复、支付、告警、合规和最终回滚仍是外部门禁。

本证据不包含个人出生资料、姓名、密码、邮箱凭据、API key 或其他秘密。

### 本轮最终收口复验（2026-08-15）

- 全仓 `make check` 最终结果：Backend `914 passed / 110 skipped`；Ruff 全量通过；mypy `142 source files` 无错误；Web `72 files / 450 tests`，lint、typecheck、production build 全通过；Admin `33 files / 121 tests`，lint、typecheck、production build 全通过；`git diff --check` 通过。
- 真实受控 Runtime 矩阵：V51 的 13 个核心 Provider、V52 的八字/紫微/七政关系矩阵、V53 的寻时定盘 12 时辰事实矩阵均通过；V53 仍明确标记 `ranking_status=not_ranked` 与 `event_matching_status=not_calculated`。
- V53 发布包复验：218 个签名文件全部存在，文件哈希和权限均匹配，无额外文件、无缺失文件、无 `__pycache__`/`.pyc`；manifest SHA-256 为 `55efe80255b6f5ad9c6c9c226d9f8f95af3213a2d941ae5258a7f6ff5d05fada`。
- 这些是本地/测试受控品的代码与 Runtime 证据，不把用户逐页批准、Mac mini native-full、生产凭据、支付/备份/告警/合规和公开生产上线误记为完成。

### 测试机浏览 hotfix（2026-08-15）

- 测试机 `fateradar-prod` 当前仍指向 `ui-preview-20260815-public-products`；因磁盘仅余约 387MB，按既有 runbook 使用可回滚源码 hotfix，没有复制新的 2GB release，也没有删除历史 release。
- 覆盖前源码备份：`/opt/fateradar/shared/cache/time-check-hotfix-20260815/source-before.tar.gz`；SHA-256 `6584bb6fad2b6f4427f6ee6a547732a0ab0a8784747cd6337d25328d303fa3c7`。覆盖内容限于本轮寻时定盘 API、Runtime ViewModel/合同、工具页和相关读取模块；部署临时目录已清理。
- 服务器端 Web 重新 build、standalone prepare、API/Web/Worker/Admin/Nginx 重启和健康检查均通过：`/healthz`、API live/ready、`/tools/time-check`、`/bazi`、Admin `/login` 均 `200`；四个应用服务 `NRestarts=0`；动态 OpenAPI 含 `/api/v1/readings/time-check`。
- 浏览入口：`http://106.14.10.235:18080/tools/time-check`；也可用 SSH 隧道 `ssh -L 18080:127.0.0.1:8080 -L 13001:127.0.0.1:3001 fateradar-prod` 后访问 `http://127.0.0.1:18080/tools/time-check`。该机仍是 `local + Fake`，只用于虚构资料浏览和 P4-007 逐页验收。

### 本轮新增：三术目标年份与 Runtime 扩展事实闭环（2026-08-15）

- 八字、紫微、七政均新增明确的目标年份编译动作：请求只允许一个 `1800–2199` 年份，并分别路由到 `bazi`、`ziwei`、`xingming` 的 `year` horizon；目标年份不会回退到本命 `life` 层。
- 八字 `year_layers`、紫微 `annual_layers`/当前大限/算法约定、七政 `annual_transformations`/指定时限/星历与计算口径已进入后端严格 ViewModel、`reading-document/v1` 合同和 Web RuntimeChart；Web 只展示 Runtime 事实，不在浏览器重排或补断法。
- 真实受控 Runtime 定向回归覆盖三术年份层与既有本命链路：`4 passed`；本轮最终 `make check` 为 Backend `921 passed / 112 skipped`、Web `72 files / 450 tests`、Admin `33 files / 121 tests`，Ruff、mypy、两端 lint/typecheck/build 和 `git diff --check` 全通过。
- 测试服务器同步前仍保持 `local + Fake` 边界；服务器热更新只用于让用户浏览输入/API/结果页面，不把 Fake 结果写成真实年份算法证据。
- 测试服务器已完成本轮可回滚热更新：后端/合同源码备份为 `/opt/fateradar/shared/cache/core-year-hotfix-20260815/source-before.tar.gz`（`f01c60710ee2756654aaeb3af6561bf8708c208837a8a2c9cb318381d0b92078`），补充 Web 源码备份为 `/opt/fateradar/shared/cache/core-year-hotfix-20260815/web-extra-before.tar.gz`（`97978dde09baac2c5cf1d0029c6656826a2a23d50c844a650dd0d5c69de1e56e`）。
- 服务器 Web production build/standalone prepare、后端 import、五个 unit（API/Worker/Web/Admin/Nginx）均 active，`NRestarts=0`；`/healthz`、API live/ready、`/bazi`、`/ziwei`、`/qizheng` 均为 `200`，OpenAPI 的 `PreviewStartRequest.target_year` 已为 `1800–2199|null`。服务器仍是 `local + Fake`，只供用户浏览批准。

这次仍未把以下内容误记为完成：三术合参的实质互证/分歧规则、各术完整深读/追问/分享发布、寻时事件匹配/淘汰/排名、解梦/姓名 Provider，以及 P4-007/P12 外部门禁。

### 本轮继续开发：时间层与原生关系 Runtime 收口（2026-08-15）

- 八字新增精确 `month`、`day` 请求；紫微新增精确 `month` 请求；七政新增精确 `month`、`day` 请求。五种请求均由 Compiler 生成单一明确 horizon，Runtime 扩展事实进入后端 Typed ViewModel、`reading-document/v1` 和 Web 结果页，未在页面端重算。
- 用户授权的临时个人资料只做一次性真太阳时 smoke，覆盖八字本命/年/月/日、紫微本命/年/月、七政本命/年/月/日；结果只输出能力与事实数量，未写入仓库、服务器、证据正文或记忆。
- v52 relationship release 在修正发布工件权限和清除两份未列入签名清单的生成性 `__pycache__` 后，真实 admission 为 `13/13`；八字、紫微、七政分别返回 `6/9/30` 条原生跨命盘信号，并成功投影为 `BaziRelationshipV1`、`ZiweiRelationshipV1`、`QizhengRelationshipV1`。这证明合盘“核心信号接入”已完成，但不等于合参解释结论已完成。
- 当前本地完整门禁为：Backend `931 passed / 113 skipped`、Web `72 files / 450 tests`、Admin `33 files / 121 tests`；Ruff、mypy `142 source files`、两端 lint/typecheck、两端 production build 全通过。
- 当前仍明确未完成的算法边界没有变化：寻时定盘的事件匹配/淘汰/排名、Canwen/Hecan 的实质互证与分歧规则、解梦和姓名正式 Provider，以及各术完整深读/追问。不能用 UI 文案或模型生成替代这些 Runtime 规则。

### 测试服务器同步（2026-08-15）

- `fateradar-prod` 当前仍指向 `ui-preview-20260815-public-products`；覆盖前的源码/合同备份为 `/opt/fateradar/shared/cache/temporal-layer-hotfix-20260815/source-before.tar.gz`，SHA-256：`adcc2da6b91b15b0405cdfc34949a2d9c378d1231a45283fbc16546b26593ef2`。
- 服务器实际完成 backend import、JSON Schema 解析、Web production build、standalone prepare；API/Worker/Web/Admin 重启后均 active，`NRestarts=0`，Nginx 保持 active。
- `/healthz`、`/bazi`、`/ziwei`、`/qizheng`、`/tools/time-check`、`/tools/five-elements`、`/tools/rhythm`、`/tools/chart-similarity` 均返回 `200`；动态 OpenAPI 的 `PreviewStartRequest` 已包含 `target_year`、`target_month`、`target_date`，页面实际包含目标月份/目标日期/流月/流日文案。
- 该服务器仍为 `local + Fake`，只用于你逐页浏览和验收页面合同；没有把 Fake 结果当作真实算法证据。

### 2026-08-16 当前工作树复验

- 使用本机受保护的 `0600` Runtime 环境文件加载 one-shot V51 Runtime 后，真实公开核心与 Worker/ReadingDocument 定向矩阵为 `8 passed / 1 skipped`，耗时 `39.92s`。覆盖八字本命/年/月/日、紫微本命/年/月/年层、七政本命/年/月/日/年层、六爻、大六壬、相法、日运事实面板、V51 13 Provider Worker、同盘和跨术结构；实际读取的是签名 Runtime 计算事实，不是 Fake 结果。
- 本机 PostgreSQL 16 `mingli_test` 上完整 `backend/tests/test_reading_worker.py` 为 `20 passed`，包含 Accepted 提交失败后的事务回滚、精确 Complete 重放、租约 fencing、幂等并发和 Worker 状态恢复。
- 唯一 skip 是当前私有环境未安装 `v52-relationship` Runtime release；没有把 V51 两张独立命盘冒充 V52 原生关系信号。V52 关系仍需匹配的 release、manifest 和 PreparedInputs 重新执行。
- 这次复验没有把个人资料、密码、SMTP 凭据、API key 或状态 token 写入证据；私有环境文件只用于进程内加载。

### 2026-08-16 个人资料一次性真太阳时 smoke

- 按用户授权使用一次个人资料，在 `solar` 时间口径和一次性授权坐标下执行八字、紫微、七政本命请求；Runtime admission 为 `13/13`，三项均返回 `Prepared`。
- 脱敏结果只记录总事实数/计算事实数：八字 `23/14`、紫微 `33/24`、七政（Runtime capability `xingming`）`21/13`；没有记录姓名、出生时间、地址、坐标或状态 token。

### 2026-08-16 Runtime 来源证据 → ReadingDocument 回归

- 真实 V51 单术数 Worker 矩阵新增来源证据合同：每个 Provider 的 Prepared brief 必须返回至少一条 Runtime-owned `evidence`，或返回明确的 `limits`；每条来源证据的 `supports_fact_refs` 必须只引用同一 brief 的事实，finding 不能引用不存在的证据。
- 当前真实矩阵 `1 passed`，覆盖本机 V51 已登记的单术数/工具产品；八字、紫微、七政、六爻、梅花、禄命/纳音、太乙、择日、奇门、大六壬、相法、日运和音律均返回来源证据，风水按其观测边界返回明确限制，不被强行写成来源证据。
- Accepted 后的 `ReadingDocumentV1.evidence` 逐项与 Prepared brief 的证据引用一致，确认来源证据经过 Worker、Guard 和不可变文档，而不是只停留在 Runtime 进程中。该回归不把来源证据升级成旺衰、吉凶、合参或事件排名结论。
- 该 smoke 只证明真太阳时输入和三术核心 Provider 的当前接线可运行，不把它升级成完整断法、合参结论或生产准入证据。

### 2026-08-16 V52 原生合盘重新复跑

- 使用当前可读的受控 V52 relationship release 和临时 700 权限状态目录，真实 Worker 关系矩阵 `1 passed`；八字、紫微、七政三种关系请求均经过 `Prepare → calculated relationship_signals → Accepted → ReadingDocumentV1`。
- V52 Runtime 结构回归 `12 passed / 16 deselected`；三术合参的 `dimension_fact_scope` 均完整，结果仍保留“范围齐全、尚未形成实质互证结论”的边界。
- 这次复跑修正了此前“当前环境未安装 V52 relationship release”的即时状态描述；它只证明 V52 原生关系信号和结构范围已可复验，不把合盘信号升级成权威合参断法，也不改变 P10 的 `IN_PROGRESS` 状态。

### 2026-08-16 关系引用闭合 hotfix 测试机同步

- `backend/app/charts/relationship_engine.py` 新增 Runtime signal `fact_refs` 闭合校验：引用必须来自同一 brief 已返回的非输入事实；未知引用、输入引用和空引用均不再投影成关系 ViewModel。新增负向回归，局部关系测试 `6 passed`。
- 测试机 `fateradar-prod` 的 `ui-preview-20260815-public-products` 已先备份旧文件，再以可回滚 hotfix 同步；备份目录为 `/opt/fateradar/shared/cache/relationship-fact-ref-hotfix-20260816/`。本地与远端目标文件内容一致。
- API、Worker、Web、Admin、Nginx 均 active，API live/ready、Nginx `/healthz`、`/bazi/hepan`、`/ziwei/hepan`、`/qizheng/hepan` 和 Admin 登录页均返回 `200`，API/Worker `NRestarts=0`。测试机仍是 `local + Fake`，只供浏览合同，不代表 V52 真实 Runtime 已切入服务器或生产准入。

### 2026-08-16 P10 Provider 展示标签闭合

- 发现并修复结果侧栏只覆盖 P0 三个能力标签的问题：P10 的梅花、奇门、大六壬、禄命/纳音、相法、择日、太乙、七政、紫微和 V53 寻时定盘现在均显示中文产品名称，不再把 Runtime capability ID 直接呈现给用户；对象和维度也补齐空间观察、可见观察、时辰候选等产品标签。
- 这是 Provider→ReadingDocument 之后的展示合同修复，不新增算法、不在浏览器重算，也没有改变任何 Runtime 输入或事实。
- 本地验证：Web `reading-display` 定向 `11 passed`；全仓 Backend `933 passed / 113 skipped`、Web `72 files / 452 tests`、Admin `33 files / 121 tests`，Ruff、mypy、lint、typecheck、production build 全通过。
- 测试机已备份 `/opt/fateradar/shared/cache/reading-scope-labels-hotfix-20260816-v1/` 后重建 Web standalone；`/healthz`、八字、梅花、寻时、解梦、Admin `/login` 均返回 `200`，五个服务 active，Web `NRestarts=0`。测试机仍为 `local + Fake`。

### 2026-08-16 Admin 能力清单闭合

- 发现 Admin 能力 API 仍只枚举 V51 的 13 个 Provider，导致已接入 V53 的 `time-check` 不出现在能力清单；同时其中文标签表也缺少该 ID，直接扩展枚举会触发 `KeyError`。
- 已将 Admin 枚举统一到 `V53_TIME_CHECK_RELEASE_CAPABILITY_IDS`，补齐“寻时定盘”标签和 `time_check_preview` 动作回归。现在后台清单包含 14 项，`time-check` 保持 `INTERNAL_TEST`，不误报为 P0 公开能力。
- 定向 Admin 回归为 `2 passed`，受影响 Ruff 通过；全仓 `make check` 为 Backend `933 passed / 113 skipped`、Web `452 passed`、Admin `121 passed`，mypy、两端 lint/typecheck/build 全通过。
- 这是能力注册/后台可见性闭合，不新增算法、不把寻时的事实枚举升级成事件匹配、淘汰或排名；V53 仍保持 `ranking_status=not_ranked` 与 `event_matching_status=not_calculated`。

### 2026-08-16 Admin 能力清单测试机同步

- 测试机 `fateradar-prod` 仍指向 `ui-preview-20260815-public-products`；覆盖前备份保存在 `/opt/fateradar/shared/cache/admin-capability-list-hotfix-20260816-v1/`，只覆盖两份后端源码文件。
- 两份远端文件哈希与本地完全一致；远端 Python import 断言 `time-check`、中文标签和 `time_check_preview` 均通过。API/Admin 重启后 `NRestarts=0`，API health `200`，Admin `/login` `200`。
- 远端示例 Admin 账号返回 `401`，因此本轮没有伪造或继续猜测服务器凭据来读取已认证能力列表；用户用测试机真实 Admin 账号登录后即可浏览该项。测试机仍是 `local + Fake`，不代表生产准入。

### 2026-08-16 梅花 / 六爻 / 大六壬结构事实透传

- 反向核对 V51 Provider manifest 与公共 ViewModel 后，确认三处真实断链：梅花的 `body_relation_facts`、`seasonal_strength`，六爻的纳甲/六亲/六神/旬空/月日旺衰/世应关系/用神选择，大六壬的天地盘/贵人/月将/旬空/课传规则轨迹/维度事实，原先都在 Runtime 已计算但在投影器后被丢弃。
- 现已新增 `MeihuaCoreFacts`、`LiuyaoCoreFacts`、`DaliurenCoreFacts`，接入各自 `*-chart/v1`、`reading-document/v1`、Web Registry 和 RuntimeChart；结果页只展示 Runtime 结构事实及状态，不生成吉凶、事件结论、匹配分数或浏览器端重算。
- 受控真实 V51 one-shot 回归：公共六爻/大六壬核心与梅花五种起法 `3 passed`；V51 Worker/ReadingDocument 矩阵 `3 passed / 1 skipped`，并新增黄金字段存在性检查；ViewModel/ReadingDocument 合同回归 `53 passed`，Ruff 与 Web typecheck 通过。
- 这项变更扩大的是“已计算事实的可追溯展示”，不是六爻/大六壬深读或合参断法完成证明。六爻用神定性、六壬事件判断、梅花体用吉凶等仍必须依赖正式解释合同与边界，不能从这些结构字段直接推断。

### 2026-08-16 测试服务器同步与健康复验

- `fateradar-prod` 的 `ui-preview-20260815-public-products` 已先备份本轮 8 个后端/合同/Web 文件，备份目录为 `/opt/fateradar/shared/cache/core-structure-facts-hotfix-20260816-v1/`；远端目标文件与本地上传版本逐项 SHA-256 一致。
- 远端 backend compile/import、JSON Schema 解析和 Web production build/standalone prepare 通过。一次 Web 重启因 Next standalone 构建后缺少 systemd `ExecStartPre` 所需的应用缓存目录而失败，已按服务现有合同补建该精确目录并复启；不是代码启动错误。API、Worker、Web、Admin、Nginx 当前全部 active，`NRestarts=0`。
- 按项目真实路由复验：API `/api/v1/health/live`、`/api/v1/health/ready`，Nginx loopback/public `/healthz`，Web `/bazi`、`/liuyao`、`/meihua`、`/daliuren` 和 Admin `/login` 均返回 `200`。测试服务器仍是 `local + Fake`，只供逐页浏览和产品合同验收，不是生产 Runtime 证据。
- 服务器根分区剩余约 `389MB`，本轮没有做无授权清理；后续正式发布前应先扩容或按运维方案释放空间。
