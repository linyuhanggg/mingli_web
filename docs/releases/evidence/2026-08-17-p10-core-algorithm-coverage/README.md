# P10 全 Provider 核心算法接线复核

日期：2026-08-17

## 结论

当前 V53 本地 Runtime 的 14 个 Provider 都已经进入统一的
`Request Compiler → Runtime → Prepared → Worker → Accepted → Typed ReadingDocument`
链路。这里的“接入”指对应算法事实、候选或观察层能被 Runtime 计算并被结果文档消费；不把事实层自动升级成正式断法。

## 复核范围

- 14 个单术数入口：八字、风水、近时日运、大六壬、六爻、早期禄命纳音、梅花、相法、奇门、择日、太乙、寻时定盘、七政四余、紫微斗数。
- 三个合参入口：Canwen、HeCan、Wenshi。
- 每个入口均检查 Runtime calculated fact namespace、来源 evidence/limit 合同、Worker 状态推进、Accepted 和 Typed ReadingDocument。

## 当前算法深度

- 已有较完整候选链：八字（强弱证据、调候候选、领域指标）、六爻（六亲/用神链、月日旺衰候选）、梅花（体用/互变/季节强弱候选）、大六壬（课式事实与已验证维度 rule evidence）。
- 大六壬的 `location` 目前只保留三传支位到八方的结构候选；release 未携带其声明的《大六壬秘本》方向原文，因此已移除错误的 `LM-R01/LR-09` 激活，不把方向字段伪装成已审计裁断。
- 大六壬的 `money` 目前只激活已核验的 `LM-R20`；来源虽已定位但仍为 `inactive_unverified` 的 `LR-15` 不进入 `source_rule_ids` 或 matched evidence。`work/career` 已补显式六亲类神输入（兄弟、子孙、妻财、官鬼、父母）与目标事实投影；只有目标类神在三传中出现时才激活已核验的 `LR-19`，否则记录 `required_fact_missing` 或 scope boundary。
- 大六壬的 `work/career` 目标链已穿过 Compiler → V53 Provider → Prepared Brief；真实合成课命中 `target_relative=兄弟`、`target_presence=true`、`LR-19`，并保持 `hard_verdict=null`。这补的是可追溯事实/证据合同，不等于完成事业吉凶断语。
- 修复 V53 发布包中 `liuren_calc` 与 `liuren_fact_adapter` 对同一 source table 使用不同 SHA 的漂移；源码、测试机 release manifest 和后端准入期望值已重新对齐，避免真实 Runtime 把该错误折叠为通用 `Stopped`。
- 共用日历层已补真太阳时回归：`local_apparent_solar-v1` 必须记录经度/均时差修正、`effective_datetime` 和修正后四柱；合成坐标定向测试 `4 passed`，不会把“Prepared”误当成已经验证了时间口径。V53 Bazi 现在额外公开脱敏的时间口径事实（策略、修正秒数、边界状态和算法版本），不公开出生日期、地点或坐标。
- 本轮来源审计修复了两处真实规则锚点漂移：八字调候 `QR-02-01` 改为发行包内的 `references/books/bazi/qiongtong-baojian/rules.md`，八字冲突路由明确标注为产品合同而非古籍裁决；六爻旺衰证据将不存在的 `ZP-05` 改为发行包内已声明的 `ZR-05-05`，并由真实 Worker 矩阵验证 source rule 文件和规则号可解析。修复后 V53 单术数全文件回归 `9 passed, 1 skipped`。
- 已有确定性结构事实或有界候选：紫微、七政四余、奇门、太乙、择日、禄命纳音、近时日运。奇门的活动盘面模式会按问题维度绑定可用的来源 evidence；禄命纳音现在还会把 59 条已核验来源规则的命中条件投影为 `source_conditioned_patterns`；紫微接入 2 条、七政四余接入 3 条、择日接入 `KR-05`（带方向事实时还可命中 `XR-18`，`开山/修方` 保持原文豁免），均保持“谓词命中、未下断语”。
- 梅花本轮补齐来源证据桥：先天数命中已核验 `HR-04-01` 与 `MR-01-01`，主卦成六十四卦命中已核验 `ZZR-M001`，三条均以 `predicate_matched_not_verdict` 进入 Runtime calculated facts、Prepared Brief 和 evidence refs；未验证的体用吉凶 `MR-04-02` 仍保持 `candidate_only/pending_verification`，没有被升级为断语。
- 风水本轮补齐来源条件投影：八宅门向合成输入在 Runtime calculated facts 中命中生产 Evidence 已激活的 `YZS-R005`，并进入 `source_conditioned_patterns`、Prepared Brief、Worker 和 `FengshuiViewV1`；`HDZJ-R002` 与 `YZS-R007` 虽在来源表的活动规则 ID 中，但当前 Evidence 绑定仍是 `inactive_unverified`，因此没有伪装成正式命中。该切片仍只表达来源谓词满足，不生成宅运吉凶或现场诊断。
- 八字本轮补齐来源条件桥：V53 `bazi_fact_adapter` 依据 23 条已激活的 Bazi Runtime 规则生成 `source_conditioned_patterns`，并由 Bazi FactContract 校验状态只能是 `predicate_matched_not_verdict`。合成丙日辰月盘实际命中 `QR-02-01`、`QTB-M01`、`R-01-02`、`ZPR-01`，四条均保留 fact paths、predicate audit、source anchor 和 source dependency；随后穿过 Prepared Brief、Worker、Accepted 与 `BaziCoreFacts`。本地 Bazi projector/Runtime 回归 `22 passed/18 skipped`，真实 V53 Worker 矩阵 `9 passed/1 skipped`；这补的是来源可追溯性，不是旺衰、格局、喜忌、用神或吉凶硬裁决。
- 六爻本轮补齐来源条件桥：V53 `liuyao` 将盘面事实索引交给生产 Evidence 谓词匹配，合成六爻实际命中 `BSZZ-M01`、`HJC-M001`、`HZL-M001`、`ZZR-M001`，四条均以 `predicate_matched_not_verdict` 保留 fact paths、predicate audit、source anchor 和 source dependency；随后穿过 Prepared Brief、Worker、Accepted 与 `LiuyaoCoreFacts`。六爻事实层仍不选择用神、不生成成败吉凶或应期断语；本地投影定向回归通过，清洁真实 V53 Worker 矩阵 `9 passed/1 skipped`。
- 相法本轮补齐来源条件桥：V53 `physiognomy` 将 face 观察索引交给生产 Evidence 谓词匹配；合成 face 输入命中 `LZ-R01`、`SR-02-04`，combined 输入命中 `LZ-R01`，palm/posture 因没有适用 face 规则保持空数组。匹配结果均为 `predicate_matched_not_verdict`，保留 fact paths、predicate audit、source anchor 和 source dependency，随后穿过 Prepared Brief、Worker、Accepted 与 `PhysiognomyViewV1`；这仍不是手相、体态或综合相法正式诊断。
- 观察/边界型：风水输出现场事实并保留来源缺口；相法输出 face/palm/posture/combined 四种结构化可见观察、来源分歧和缺失目标；寻时只做十二候选与结构化事件的有界证据排序。
- 寻时结果层现在额外展示每个候选与事件的证据明细（分数、命中状态、支关系、事件年柱十神和无信号原因），直接消费 Runtime 已计算的 `event_evidence`；不改变排序、不生成“最可能时辰”或古法定盘结论。

## Wenshi 合参证据桥补充

- Wenshi 结果投影现在消费 Runtime 已计算的六爻 `useful_spirit_candidates` 候选池、`useful_spirit_selection` 的候选链/旺衰证据，以及奇门 `named_patterns` 的 `predicate_matched_not_verdict` 来源谓词；每条信号保留 calculated fact ref。
- 真实 V53 one-shot Wenshi 黑盒核验确认两个请求维度都能保留六爻候选池和 `evidence_bound` 选择证据，奇门来源谓词也继续保留；合成投影回归 `24 passed`，真实 Wenshi Prepared 回归 `1 passed`，相关 Canwen/HeCan/Wenshi 适配回归 `3 passed`，`convergence` 与 `disagreements` 仍为空。
- 这一步补的是三术“证据可见性”，没有选择用神、合并格局、判定成败吉凶，也没有把三术分歧强行压成一个答案。

## Canwen / HeCan 合参证据桥补充

- Canwen/HeCan 结果投影现在消费八字 `interpretive_candidates` 的强弱、结构、从格/合化、推理工具和显著性候选通道；紫微与星命分别消费 `source_conditioned_patterns` 中状态为 `predicate_matched_not_verdict` 的来源谓词。每条新增信号都保留 calculated fact ref。
- 真实 V53 one-shot Canwen 回归已通过：八字候选和紫微来源谓词进入三术维度信号层；合成全三术事实范围时，`convergence` 只表示“计算事实范围均已提供”，不表示实质互证，`disagreements` 仍为空。
- 这一步补的是 Canwen/HeCan 对已有核心事实的可追溯消费，不是八字旺衰/格局、紫微/星命正式断法，也没有实现跨术共同结论、分歧分类或裁决优先级。

## 仍未完成的核心算法工作

- 八字、六爻、梅花、大六壬仍没有完成问题级硬裁决、完整深读和跨流派冲突裁判。
- 紫微、七政四余、奇门、太乙、择日目前已有可追溯结构候选，但缺对应正式解释链；禄命纳音、紫微、七政四余、择日的来源条件候选仍缺从候选到正式解释、跨来源冲突裁判的链路；未验证的来源规则继续不激活。
- 大六壬还缺完整成败/吉凶/应期的学校裁决、更多问题类型的专项目标合同和三术实质合断；本轮只完成有来源支持的 `work/career` 目标事实链。
- Wenshi 目前只完成六爻候选池/候选选择证据、奇门来源谓词和大六壬规则证据的可追溯展示；仍没有选择用神、三术共同结论、分歧分类和裁决优先级。
- Canwen/HeCan 目前只完成八字候选、紫微/星命来源谓词的可追溯展示；三术之间的共同结论、分歧分类和裁决优先级仍未实现。
- 风水需要完整现场资料和可执行来源规则；相法现在已覆盖 face、palm、posture、combined 的可见观察，但手相/体态/综合结果仍不是正式相术诊断。
- 解梦、姓名等产品若要成为正式术数 Provider，还缺独立输入合同、可执行来源规则和统一结果投影；目前不能把模型文案当核心算法。

## 2026-08-17 奇门深读垂直切片

- 新增 `qimen_deep` 产品动作、`POST /api/v1/readings/qimen-deep`、付费能力映射和 `qimen-deep-output-v1` 输出合同。Job 在正式商品履约绑定前保持 `awaiting_fulfillment`，固定 `outcome`、`timing`、`state` 三个维度；错误维度不会被静默改写。
- 奇门深读复用已接通的奇门 Runtime 局式事实、来源谓词和证据，不新增未经验证的断法。真实 V53 Runtime → Worker → Accepted → `qimen-chart/v1` Typed ReadingDocument 回归 `1 passed`；八字既有深读合同也补了真实 Worker 回归 `1 passed`。
- 修正两个深读合同 ID 中斜杠不符合模型审计安全标识的问题：`bazi-deep-output-v1`、`qimen-deep-output-v1`。Fake Model 同时按合同 `min_blocks` 补齐深读段数，避免把本地合同测试误判为生成失败。
- 修复奇门盘面的一处真实事实丢失：V53 `stars_doors_deities` 在天芮宫会同时返回天芮与天禽，旧投影只取 `stars[0]`。现在 `QimenPalace.stars`、ViewModel/UI 和 `qimen-chart/v1` Schema 保留完整星列表，现有 `star` 只作为首星字段；合成投影 `2 passed`、真实 V53 Qimen `1 passed`、真实 Qimen 深读 Worker→Accepted→Typed ReadingDocument `1 passed`、Web RuntimeChart `9 passed`。
- 本轮续验修复了全量测试中的一个真实时序脆弱点：Runtime 进程组探针的子进程延迟从 `0.5s` 调整为 `2s`，避免 50ms 超时测试在整套门禁调度抖动下先写入探针文件；后端测试 `958 passed / 127 skipped`，Ruff、应用/Worker mypy、Web/Admin 测试、lint、typecheck、production build 和 `git diff --check` 均通过。
- 定向阅读 API/合同回归 `61 passed`；当前完整本地门禁为 Backend `956 passed / 127 skipped`、Web `454 passed`、Admin `123 passed`，Ruff、mypy、两端 lint/typecheck、生产构建和 `git diff --check` 均通过；真实 V53 Worker 矩阵为 `9 passed / 1 skipped`。
- 已按可回滚热更新同步到 `fateradar-prod` 测试验收机的当前 release `ui-preview-20260816-codex-web`。7 个后端文件的旧版本备份在 `/opt/fateradar/shared/cache/qimen-deep-contract-hotfix-20260817`；API/Worker/Web/Admin/Nginx active，health、OpenAPI `/api/v1/readings/qimen-deep`、公网 `/`/`/qimen` 均复验通过。服务器仍是 `local + Fake`，只用于用户浏览批准，不代表生产或真实支付/模型准入。

## 2026-08-17 六爻深读候选证据垂直切片

- 新增 `liuyao_deep` 产品动作、`POST /api/v1/readings/liuyao-deep`、付费能力映射和 `liuyao-deep-output-v1` 输出合同。Job 在正式商品履约绑定前保持 `awaiting_fulfillment`，固定 `outcome`、`timing`、`state` 三个维度；部分维度或错误顺序会被拒绝，不静默改写用户请求。
- 六爻深读复用已接通的本卦/变卦、爻位、六亲、用神候选、月日旺衰和来源条件谓词；合同明确候选不等于用神定夺，不输出成败或应期硬结论。真实 V53 Runtime → Worker → Accepted → `liuyao-chart/v1` Typed ReadingDocument 回归 `1 passed`。
- API/编译器/付费权限/OpenAPI/合同定向回归 `187 passed`；OpenAPI 冻结清单同时锁定 `startLiuyaoDeepReading`、`LiuyaoDeepStartRequest` 和六爻 `state` 维度。
- 这一步补的是六爻“深读入口和证据交付”合同，不是六爻正式用神选择、成败吉凶、应期裁决，也不代表真实商品支付、模型履约、用户浏览批准或 P12 生产准入。
- 本轮完整本地门禁为 Backend `973 passed / 128 skipped`、Web `459 passed`、Admin `123 passed`；Ruff/mypy、两端 lint/typecheck、生产构建和 `git diff --check` 均通过。

## 复核结果

- 真实 V53 单术数 Worker/Accepted/Typed ReadingDocument 矩阵：`40 passed, 1 skipped`（包含 14 个入口的 Worker/Accepted/Typed ReadingDocument、pinned adapter、禄命/紫微/七政/择日来源条件候选回归与已核验 Luming `LX-01-17` 来源绑定回归；skip 是没有匹配 V52 relationship release）。
- Provider 接入护栏通过：V53 14 个 Provider 均映射到 Typed ViewModel；新增 Provider 若缺 ViewModel 合同会直接失败。
- Canwen/HeCan/Wenshi 合参 Worker/Accepted/Typed ReadingDocument：`1 passed`。
- 清除 V53 环境变量后的启动准入/manifest 定向回归：`4 passed`。
- `ruff check app/config.py`、`mypy app/config.py`：通过。
- 奇门真实合成盘回归：命中模式按问题维度进入 `QM-P16/QM-P17` 来源 evidence，`1 passed`。
- 大六壬方向候选边界、求财规则激活边界、`work/career` 目标类神证据与 source-table 双适配器契约回归通过；真实 V53 事业目标链、pinned Runtime adapter/validator 与 Wenshi 来源证据 smoke 均通过。
- 真实 V53 择日方向回归覆盖 `立向 + site_mountain=丁` 命中 `XR-18`，以及同一山向在 `开山` 动作下不命中；同时修正 Runtime 返回结构化时间候选时，Backend projector 只取 `candidate_time_id`，避免“存在可选时辰时结果页为空”。
- 真实 V53 择日安葬/破土来源回归：2026-01-03 安葬命中已核验 `sansang_day`（`chen-zixing-sansang-v1`），2026-01-10 破土命中已核验 `tujin`（`chen-zixing-tujin-v1`）；两者均进入 `event_fact_hard_elimination`、`no_valid_candidate` 和公开 `SelectionChartV1.eliminations`，保留来源锚点，不把规则升级成通用吉凶断语。新增 Worker→Accepted→Typed ReadingDocument 回归 `1 passed`，确认该淘汰原因没有在业务编排或最终 ViewModel 阶段丢失。
- 真实 V53 奇门来源谓词 Worker 回归：关键 `QM-P16`（三奇入墓）与 `QM-P17`（六仪击刑）在完整盘上命中，并随同盘其它合法谓词进入 `QimenChartV1.named_patterns` 和 Typed ReadingDocument；状态保持 `predicate_matched_not_verdict`，不把格局谓词升级成事件吉凶。
- Wenshi 六爻候选选择链回归：`useful_spirit_selection` 的 `chain_candidates` 与 `strength_evidence` 仅在 Runtime 标注 `evidence_bound/candidate_only` 且无 `hard_verdict` 时进入三术信号层；合成投影 `24 passed`，真实 V53 Wenshi Prepared `1 passed`，所有新增信号均保留 calculated fact ref 并明确“不形成问事合参结论”。
- 本轮全仓验收：Backend `953 passed / 125 skipped`，Web `454 passed`，Admin `123 passed`；Ruff、mypy、lint、typecheck、Admin/Web production build 和 `git diff --check` 全通过。新增测试只涉及 Worker 回归与证据记录，没有产生新的 Runtime/Web 可部署产物。
- 真太阳时共用日历合同回归：`4 passed`；个人资料只用于本机临时黑盒核验。收口扫描发现旧测试夹具与历史说明曾含可识别的出生/姓名/籍贯片段，当前工作区已全部替换为合成资料或脱敏表述；Git 历史未做破坏性重写。
- 用户授权的临时个人资料本机黑盒核验：V53 当前 16 条单术数 Worker 矩阵全部 `passed`，覆盖八字、五行事实、日运、紫微、七政、六爻、梅花、禄命纳音、本命音律、太乙、择日、风水、奇门、大六壬、相法和寻时定盘；每条均闭合 Runtime 计算事实、证据/限制合同、Worker、Accepted 与 Typed ReadingDocument。旧合成资料黄金值断言未用于本次判定；当前工作区对出生时刻、姓名和详细籍贯的定向扫描均为零命中，测试服务器和公开 ViewModel 未写入这些原始值。
- 个人测试资料收口后的完整门禁：Backend `981 passed / 129 skipped`，Web `460 passed`，Admin `123 passed`；Ruff、mypy、两端 lint/typecheck/production build 与 `git diff --check` 全通过。清理只替换测试夹具与证据措辞，不改变 Runtime 算法或公开合同。
- V53 Bazi 脱敏历法事实真实 one-shot 回归：`Prepared → BaziChartV1`，真太阳时状态为 `apparent_solar_applied`，公开字段无出生日期、地点或坐标；当前全仓 `make check` 为 Backend `953 passed / 125 skipped`，Web `454 passed`，Admin `123 passed`，Ruff、mypy、lint、typecheck、production build 全通过。
- 当前工作区 V53 release manifest SHA-256：`bc961d4ced75c80d824617762e090fa4a872649959f2d7a6c9e409f61c8006ce`；describe digest：`2188f5c92336174872881c78a1826457d072480258be34f1c3d64bd75fe0765d`；capability shape SHA-256：`94c2ccaafa587ea64f15bd9bd96a35ac36b72dd07523b7359a37973a4cf893e0`；source commit：`local-bazi-san-yuan-v1`。

## 测试服务器复验

- `fateradar-prod` 测试机继续使用 `/opt/fateradar/current` 指向的 `ui-preview-20260816-codex-web`；因为根盘可用空间只有约 `101 MB`，本轮没有新建 release，也没有删除历史 release。覆盖前的 5 个文件已备份到 `/opt/fateradar/shared/cache/core-algorithm-display-hotfix-20260817/`，未上传环境文件或秘密。
- 随后在同一当前 release 上以可回滚 hotfix 同步 `backend/app/charts/contracts.py`、`backend/app/charts/projectors.py` 及两份 Qimen/ReadingDocument Schema；四个远端文件与本地 SHA-256 一致，覆盖前版本备份在 `/opt/fateradar/shared/cache/qimen-stars-hotfix-20260817/`。API/Worker 重启后均 active、`NRestarts=0`，API live/ready、Nginx healthz 和 `/qimen` 均返回 `200`。因根盘仅剩约 `100 MB`，本次未在服务器重建 Next Web 产物；测试页面继续使用现有首星渲染，完整叠星 UI 等下一次有容量的完整 Web 发布，不能把本 hotfix 写成前端叠星已上线。
- 本轮 Wenshi 证据桥只热更新一个后端文件 `backend/app/charts/projectors.py`；覆盖前版本备份在 `/opt/fateradar/shared/cache/wenshi-evidence-bridge-hotfix-20260816/projectors.py.before`，远端新文件 SHA-256 为 `4584f26d0e04c8debf6289bcbd030f35596a624a78489e24dd7c248ec8757489`，与本地一致。API/Worker 重启后五个服务 active，`/healthz`、API live/ready、`/wenshi`、`/hecan`、`/qimen` 均 `200`，`NRestarts=0`。
- 随后 Canwen/HeCan 证据桥继续只热更新同一个后端文件；覆盖前版本备份在 `/opt/fateradar/shared/cache/canwen-evidence-bridge-hotfix-20260816-v2/projectors.py.before`，备份 SHA-256 为 `4584f26d0e04c8debf6289bcbd030f35596a624a78489e24dd7c248ec8757489`，远端新文件 SHA-256 为 `f4ee622d161f41a3c6ab5381bb263476ee84fcf8f2413f9ed922f5d862aba2a7`，与本地一致。正确工作目录导入检查通过；API/Worker 重启后 `/healthz`、live/ready、`/`、`/bazi`、`/canwen`、`/hecan`、`/wenshi`、`/qimen`、`/ziwei`、OpenAPI 均 `200`，API/Worker/Web/Admin/Nginx active，`NRestarts=0`。测试机仍为 `local + Fake`，只用于用户浏览批准，不代表生产准入。
- 本轮六爻候选选择链热更新先做了启动失败自动回滚；确认 API 只是需要约 3 秒启动后，以新的备份目录 `/opt/fateradar/shared/cache/wenshi-liuyao-selection-hotfix-20260817-v2/` 重试成功。远端 `projectors.py` SHA-256 为 `db756df498daa030a43f048429d1bc0b9d8a4ef371b1dfb7d0c222bd0aeee9ff`，与本地一致；API/Worker/Web/Admin/Nginx active、API/Worker `NRestarts=0`，`/wenshi=200`、`/hecan=200`、`/canwen=308`。浏览入口为 `http://106.14.10.235:18080/wenshi`、`/canwen`、`/hecan`；仍是 `local + Fake` 测试机。
- 已同步并逐字节核对本地已通过门禁的 Backend contracts/projector、Web ViewModel registry、Runtime chart 和 Web 测试夹具；远端 `npm run build`、standalone `--prepare-only` 成功，生成 `34` 个页面。
- API、worker、Web、Admin、Nginx 均为 `active`，本轮重启后的 `NRestarts` 均为 `0`；`healthz`、API live/ready 均正常。`/`、`/bazi`、`/selection`、`/tools/time-check`、`/tools/dream`、`/tools/name`、`/wenshi`、`/hecan`、`/fengshui`、`/qimen`、`/ziwei`、Admin `/login` 和公网测试根地址均可访问；`/canwen` 返回规范化跳转 `308`。
- 该服务器仍是 `local + Fake` 测试环境，只证明上传后的结果层可构建、可启动、可浏览；P4-007 仍等待用户逐页浏览批准，不代表生产部署或真实算法/支付/模型准入。
- 本轮六爻深读 API 合同以可回滚 hotfix 同步到当前测试 release；覆盖前 8 个后端/OpenAPI 文件备份在 `/opt/fateradar/shared/cache/liuyao-deep-contract-hotfix-20260817/`，远端文件 SHA-256 与本地逐项一致。正确的 `fateradar-test-api/worker/web/admin` 四个服务重启后均 active、`NRestarts=0`，live/ready/healthz、动态 OpenAPI `startLiuyaoDeepReading`、公网 `/bazi`/`/liuyao`/Admin 登录均返回 200；公网浏览入口为 `http://106.14.10.235:18080/liuyao`。本次未做 UI 大改，也未注入凭据；测试机仍为 local + Fake，仅供用户浏览批准。

本轮 V53 Runtime 来源修复已同步到测试验收机：新增独立目录
`/opt/fateradar/shared/mingli-master-v53-time-check`，旧 V51
`/opt/fateradar/shared/mingli-master` 保留未覆盖；覆盖前的 API/Runtime 配置备份在
`/opt/fateradar/shared/cache/v53-runtime-admission-hotfix-20260817/`。测试机仍是
`local`，OTP、模型和支付保持 Fake，但 Runtime 已切为 V53 one-shot，manifest
SHA 为 `4f526033e37b813896d7864765af9e5deafe1b351b48ca903b92a8512323d818`。
服务器 `describe`、合成 Bazi `Prepared`（24 个事实，含 reasoning tools）、Liuyao
`Prepared`（31 个事实，`ZR-05-05`）、Meihua `Prepared`（27 个事实，仍标记
`pending_verification`）、API/Worker 启动准入、五服务状态与重启计数均通过；`/bazi`、`/liuyao`、`/meihua`、`/qimen`、
`/daliuren`、`/wenshi`、`/hecan` 和 `/tools/time-check` 均返回 `200`，公网入口为
`http://106.14.10.235:18080/`。这证明测试机已经能浏览当前算法接线，不代表
Mac mini native-full、正式生产 Runtime、真实模型/支付或 P12 生产准入。

本轮新增验证：合成 Canwen 投影 `4 passed`；合成 Wenshi 投影 `24 passed`；真实 V53 Canwen Prepared 投影 `1 passed`；真实 V53 Wenshi Prepared `1 passed`；Canwen/HeCan/Wenshi 适配回归 `3 passed`；真实 Canwen/HeCan/Wenshi Worker → Accepted → Typed ReadingDocument `1 passed`；Ruff、mypy 受影响文件通过。该切片没有改变“事实/候选层已接通、正式合参裁决仍未完成”的边界。

本轮梅花来源桥验证：本地来源匹配探针命中 `HR-04-01`、`MR-01-01`、`ZZR-M001`；全仓门禁为 Backend `958 passed / 127 skipped`、Web `456 passed`、Admin `123 passed`，Ruff/mypy/lint/typecheck/build 全通过。测试机 V53 `describe` 仍通过，真实 one-shot Meihua `Prepared → accepted` 通过，Prepared Brief 保留三个 source rule IDs 和三个 evidence refs；测试机当前目录仍为 `local + Fake`，不代表正式体用吉凶裁决或生产准入。

本轮风水来源桥验证：本地八宅合成输入的 Runtime 直算命中 `YZS-R005`，状态为 `predicate_matched_not_verdict` 且不含 `verdict` 字段；真实 V53 Worker 矩阵 `9 passed / 1 skipped`，图表投影与 Runtime 适配定向回归 `40 passed, 18 skipped`，Ruff 通过。V53 release manifest 已更新为 `14e916de90c0350ad9c6d9b96bcca50deb23ac1144d870ee137784f8abf9b4fe`；该项不代表风水现场完整资料、宅运吉凶或正式形法/理气裁决完成。

测试服务器新增风水黑盒复验：真实 V53 one-shot `Prepare` 返回风水 calculated facts，按 `brief.facts` 引用取到 `source_conditioned_patterns=[YZS-R005]`，状态仍为 `predicate_matched_not_verdict` 且 calculated facts 没有 `verdict`；随后 `Complete` 返回 `Accepted`。复验使用临时合成门向输入，不包含个人资料；API/Worker/Web/Admin/Nginx 均 active，API live/ready 与公网 healthz 正常，重启计数为 `0`。本次只在原测试 release 上做可回滚 hotfix，覆盖前文件备份在 `/opt/fateradar/shared/cache/fengshui-source-patterns-hotfix-20260817/`；仍不代表生产 Runtime、完整风水诊断或用户 P4-007 批准。

测试服务器新增八字来源条件桥黑盒复验：V53 one-shot `Prepare` 的 `brief.facts` 返回 `source_conditioned_patterns=[QR-02-01,QTB-M01,R-01-02,ZPR-01]`，四条状态均为 `predicate_matched_not_verdict` 且没有 `verdict` 字段，随后 `Complete` 返回 `Accepted`。本次只上传 Runtime manifest、Bazi adapter/FactContract 和后端合同/投影器，覆盖前文件备份在 `/opt/fateradar/shared/cache/bazi-source-patterns-hotfix-20260816/`；远端 V53 manifest SHA 为 `ee6a7185…`，API/Worker/Web/Admin/Nginx 均 active、`NRestarts=0`，API live/ready、Nginx healthz、`/` 与 `/bazi` 均返回 `200`。测试机仍是 `local + Fake`，只供用户浏览，不代表生产 Runtime、八字正式裁决或 P4-007 用户批准。

测试服务器随后新增六爻来源条件桥黑盒复验：在保留旧文件的备份目录
`/opt/fateradar/shared/cache/liuyao-source-patterns-hotfix-20260816/` 后，更新 V53
Runtime `liuyao.py`、Provider 来源路由、签名 manifest 及后端六爻合同/投影器；远端
`Prepare` 的 `brief.facts` 返回 `source_conditioned_patterns=[BSZZ-M01,HJC-M001,HZL-M001,ZZR-M001]`，四条状态均为
`predicate_matched_not_verdict` 且没有 `verdict` 字段，`Complete` 返回 `Accepted`。
远端 V53 manifest SHA 为 `51e6a200…`；API/Worker/Web/Admin/Nginx 均 active、
`NRestarts=0`，live/ready、Nginx healthz、`/` 与 `/liuyao` 均返回 `200`。测试机仍是
`local + Fake`，只供用户浏览，不代表六爻正式裁决、生产 Runtime 或 P4-007 用户批准。

测试服务器新增相法来源条件桥黑盒复验：在保留旧文件的备份目录
`/opt/fateradar/shared/cache/physiognomy-source-patterns-hotfix-20260817/` 后，更新 V53
Runtime 相法 Provider、签名 manifest、后端 `PhysiognomyViewV1` 合同/投影器和进程组清理修复；远端合成 face
`Prepare` 的 `brief.facts` 返回 `source_conditioned_patterns=[LZ-R01,SR-02-04]`，两条状态均为
`predicate_matched_not_verdict`，随后 `Complete` 返回 `Accepted`。远端文件与本地 SHA-256 一致；API/Worker/Web/Admin/Nginx
均 active，API/Worker `NRestarts=0`，测试入口 `http://106.14.10.235:18080/jianxiang` 返回 `200`。
测试机仍为 `local + Fake`，只供用户浏览批准，不代表正式相法诊断、生产 Runtime 或 P12 准入。

本证据不包含出生资料、姓名、密码、SMTP 凭据或 API key。Mac mini native-full、P4-007 用户逐页浏览批准、P11 深读以及 P12 生产门禁仍未因此完成。

## 当前轮本地真实复核（2026-08-17）

- 使用当前工作区 V53 release 的干净副本（排除生成的 `__pycache__`/`.pyc`，并按签名 manifest 恢复文件模式）和干净 Runtime venv，按仓库的 `MINGLI_RUN_REAL_RUNTIME_TESTS=1` 入口执行：`23 passed, 1 skipped`。
- 覆盖 V53 的 Runtime 启动准入、14 Provider 的 Worker → Accepted → typed ReadingDocument 矩阵、公开核心层、深读事实消费和寻时语义；唯一 skip 是本机没有安装匹配的 V52 relationship release。
- 这次确认的是当前算法事实/候选/观察层确实穿过 Runtime、Worker 和 Typed ReadingDocument；没有把 `candidate_only`、`predicate_matched_not_verdict` 或 `facts_only` 升级成正式断语。默认本地配置仍是 Fake Runtime，不能把默认配置下的跳过/启动失败写成算法失败。

## 关系 release 与启动边界补验（2026-08-17）

- 使用临时清洁的 V52 relationship venv/release 副本，排除生成的 `__pycache__`/`.pyc` 并按签名 manifest 恢复 217 个文件模式；原始 venv、release 和仓库未改动。
- 真实 V52 one-shot `Runtime → Worker → Accepted → Typed ReadingDocument` 关系矩阵 `1 passed`，覆盖八字、紫微、七政三条关系产品；三术分别产出 6、9、30 条非空 `relationship_signals`，信号只携带 calculated fact refs，最终 ViewModel 的 `signals` 非空。
- 关系矩阵测试按 release 版本使用真实最小计算契约：八字四柱、紫微宫位、七政星体位置；没有把 V53 单术新增的 `source_conditioned_patterns` 错套到 V52 关系 release。V53 清洁副本 Worker 矩阵仍为 `9 passed / 1 skipped`，Runtime process-adapter 回归 `34 passed`。
- 这补齐的是关系 Runtime 到 Worker/文档的本地证据，不等于测试服务器 native-full、深读/追问、用户 P4-007 逐页批准或 P12 生产门禁完成；解梦、姓名仍没有 Provider/规则包/Typed ViewModel。

## 十二长生核心事实垂直切片（2026-08-17）

- 以用户自有 1.3.2 恢复源码中的 `resolveDiShi` 规则为来源，将四柱每一柱的天干与本柱地支按十天干顺逆表计算十二长生位置；合成四柱 `甲戌 / 戊辰 / 丙戌 / 辛卯` 得到 `养 / 冠带 / 墓 / 绝`。
- 新增 Runtime `twelve_growth_stages` 输出、Provider output binding、独立 Bazi FactContract oracle、`BaziGrowthStage` 与 `BaziCoreFacts.twelve_growth_stages` Typed ViewModel 接线；每项保留 `bazi.chart.twelve-growth-stages-v1` 依赖标识和“不能单独推出旺衰、格局、用神或事件结论”的边界。
- 清洁 APFS release/venv 下 Bazi `Runtime → Prepared → Worker → Accepted → bazi-chart/v1`：`1 passed`；V53 全术数 Worker/Document：`9 passed / 1 skipped`；Runtime process/contracts/Bazi deep：`50 passed`；启动准入：`37 passed`。
- 该切片补的是可复算盘面事实，不是完整旺衰、格局、喜忌、用神、应期或正式断语；测试机同步后仍保持这一边界，不能把事实接入写成正式断法完成。

## 测试机同步（2026-08-17）

- 已将 V53 的新 manifest、Bazi adapter、FactContract、Provider binding、Backend contracts/projector 和 Web ViewModel/盘面接线，以可回滚 hotfix 同步到 `fateradar-prod` 当前 release `/opt/fateradar/releases/ui-preview-20260816-account-global-nav`。
- 覆盖前文件与旧 Web `.next` 保存在 `/opt/fateradar/shared/cache/bazi-growth-stage-hotfix-20260817/`；没有上传个人资料、密码、SMTP 凭据、API key 或其他环境秘密。测试环境的 `MINGLI_RUNTIME_EXPECTED_MANIFEST_DIGEST` 只更新为本次已验收的 describe digest，并登记了对应的 local + Fake 测试 Runtime release。
- 服务器 V53 release manifest SHA-256 为 `93c48cc27a3ac27ec1e8a571c38a3e54005a05e2fcd1bf2852fede6f0a8b8e1f`，one-shot `describe` digest 为 `ce25ee24e828c5fc37d792a38299e8f51a8c8c679fe5e0c0971f4eda2ea5a108`；服务器直接 Bazi 合成盘返回十二长生 `养 / 冠带 / 墓 / 绝`。
- 首次重启时 Worker 因测试环境仍登记旧 expected digest 而拒绝启动；保留日志和备份后修正测试 Runtime 登记，最终 API/Worker/Web/Admin/Nginx 全部 active，`NRestarts=0`，live/ready/healthz 正常，公网 `/bazi`、`/tools/dream`、`/tools/name`、`/luming-nayin`、`/jianxiang` 均返回 200。浏览入口：`http://106.14.10.235:18080/bazi`。
- 这仍是 `local + Fake` 测试机，只供用户浏览和 P4-007 逐页批准，不代表生产 Runtime、真实模型/支付、Mac mini native-full 或 P12 生产准入。

## 旬空核心事实垂直切片（2026-08-17）

- 来源规则采用发行包内《三命通会》旬空规则 `R-03-04`（`references/books/bazi/sanming-tonghui/rules.md#L218-L225`）：先按日柱所属旬确定旬首，再取该旬之外的两个地支。恢复源码中的旧 `resolveXunKong` 结果与该标准表不一致，因此没有把旧公式直接当作权威；V53 使用六十甲子序列独立重算，甲申旬的丙戌日得到午、未。
- 新增 Runtime `xunkong` 输出、Provider binding、独立 FactContract oracle、`BaziXunKong` 与 `BaziCoreFacts.xunkong` Typed ViewModel 接线；保留 `bazi.chart.xunkong-sexagenary-v1` 依赖标识和“只能表达旬空事实，不能单独推出吉凶、六亲或事件结论”的边界。
- 清洁本地 V53 真实回归通过：Bazi/公开核心、Worker 矩阵 `9 passed / 1 skipped`、Runtime process adapter `34 passed`；完整 Backend `959 passed / 127 skipped`，Web `72 files / 456 tests`，UI 合同 `25 passed`，typecheck、生产 build 通过。唯一 Worker skip 是本机没有安装匹配的 V52 relationship release。
- 测试机已在 `/opt/fateradar/shared/cache/bazi-xunkong-hotfix-20260817/` 保留覆盖前 V53、Backend、Web `.next`、test env 和 RuntimeRelease 元数据；新 V53 manifest、Backend/Web 接线逐字节核对，远端 Web `34` 页 build 通过。修正 `time-check.json` 的 signed mode 后 API/Worker 均 active、`NRestarts=0`，live/ready 返回 200。
- 测试机 `describe` 返回 `described`、digest `9eff29f56a349fd1325d16233135cd5791b8b2c0ec90cc70a37d698c4c6d9c02`、协议 v2、14 个 capability；远端 Bazi 合成盘返回 xunkong `午 / 未`，公网 `/`、`/bazi`、`/terms`、`/privacy` 均 200。浏览入口仍是 [测试服务器 `/bazi`](http://106.14.10.235:18080/bazi)，待用户逐页浏览批准。
- 这仍是 `local + Fake` 测试机；没有上传个人资料、密码、SMTP 凭据、API key 或其他环境秘密，也不代表真实生产 Runtime、Mac mini native-full、支付、合规或 P12 完成。

## 三垣核心事实垂直切片（2026-08-17）

- 以用户自有恢复源码中的三垣辅助公式为来源，将八字胎元、命宫、身宫接入 V53 Runtime `san_yuan`、Provider binding、独立 FactContract oracle、`BaziCoreFacts` 和 `bazi-chart/v1`；合成四柱 `甲戌 / 戊辰 / 丙戌 / 辛卯` 得到 `己未 / 甲戌 / 庚午`。这里的三垣是盘面位置事实，不单独推出格局、旺衰、吉凶或事件结论。
- 本地三垣定向回归 `22 passed / 10 skipped`；真实 V53 Worker 矩阵 `9 passed / 1 skipped`；公开核心/进程适配器 `40 passed`；完整 Backend `961 passed / 127 skipped`；Web `72 files / 457 tests`；UI 合同 `25 passed`；Web typecheck 与 production build 通过。
- 测试机已用可回滚方式同步新 manifest、Runtime、Backend 和 Web 接线；覆盖前文件保存在 `/opt/fateradar/shared/cache/bazi-san-yuan-hotfix-20260817/`。以实际服务用户 `fateradar` 执行 one-shot Bazi prepare 返回 `Prepared`，并返回三垣 `胎元=己未、命宫=甲戌、身宫=庚午`；服务保持 API/Worker active 且无新增 Runtime 缓存文件。
- 当前测试入口为 [测试服务器 `/bazi`](http://106.14.10.235:18080/bazi)，环境仍是 `local + Fake`，仅供用户浏览批准；P4-007 用户逐页批准、正式断法/P11 深读、Mac mini native-full 和 P12 生产门禁仍未完成。

## Fortune 日运机制事实结果接线（2026-08-17）

- V53 `fortune` Runtime 原本已经计算 `transit_layers`、`mechanism_stack`、选定日柱和未裁定边界，但公开 Brief 的 `period_markers` 只被前端消费为日期、日柱、日主关系和当前大运，机制字段在结果时间线被丢弃。
- 本轮没有新增推算或浏览器重算；Web `fortune-period-markers` 现在保留 Runtime 返回的 `primary_mechanism_ids`、`decisive_mechanism_ids` 和 `unresolved_boundaries`，`FortunePeriodTimeline` 展示已计算机制与“尚未形成具体事件断语”的边界。未知机制 ID 保留原值，不猜测其含义。
- Backend V53 真实 Worker/Accepted/Typed ReadingDocument 矩阵 `9 passed / 1 skipped`，新增黄金断言确认 `period_markers` 非空且机制与未裁定边界仍在文档链；Web reading-display 定向 `12 passed`，typecheck、lint、production build 通过（34 个页面）。
- 这只完成 Fortune 已有近时 Bazi 机制事实的结果接线，不把日干十神、支位关系或机制 ID 升级成事业吉凶、具体事件或金额断语；Fortune 默认产品仍固定“事业与工作”范围。
- Fortune 的目标周期继续按已声明的 `civil_day` 合同计算；出生层仍沿用用户档案的 `local_apparent_solar-v1`。Web 结果层现在同时展示目标周期的民用日边界与太阳时修正状态，避免把目标日的 `not_applied` 误读为出生时间没有应用真太阳时；该修正只补事实展示，不改变目标日算法或生成断语。

## 当前轮寻时证据明细与测试机闭环（2026-08-17）

- V53 Runtime 的 `TimeCheckProvider` 继续只输出十二候选和结构化事件证据；本轮为零分事件补齐明确的 `no_supporting_or_opposing_signal` reason。Web `TimeCheckChart` 直接展示 Runtime 已计算的事件、分数、命中状态、支关系、事件年柱十神和无信号原因，不改变排序，也不生成古法校时结论。
- 当前工作区清洁 Runtime-only smoke 通过：one-shot、14/13 describe、219 个签名文件、14 providers、55 reference packs、1328 evidence；真实 V53 Worker/Accepted/Typed ReadingDocument 矩阵 `9 passed / 1 skipped`，唯一 skip 是未安装匹配的 V52 relationship release。
- 本轮最终本地门禁：Backend `962 passed / 127 skipped`，Ruff 与 mypy 通过；Web `459 passed`、lint/typecheck/production build（34 pages）通过；Admin `123 passed`、lint/typecheck/production build（38 pages）通过；V53 release 清洁检查和 `git diff --check` 通过。
- 测试机新 Runtime 独立目录为 `/opt/fateradar/shared/mingli-master-v53-time-check-20260817-time-evidence`，manifest SHA-256 为 `bc961d4ced75c80d824617762e090fa4a872649959f2d7a6c9e409f61c8006ce`，describe digest 为 `2188f5c92336174872881c78a1826457d072480258be34f1c3d64bd75fe0765d`；旧目录保留，覆盖前 Backend/env/Runtime 备份在 `/opt/fateradar/shared/cache/v53-runtime-time-evidence-20260817/`。
- 远端合成寻时 API→Worker→结果黑盒已闭环：`time-check-view/v1`、12 个候选、12 条事件证据，其中 7 条带 `no_supporting_or_opposing_signal`；API/Worker active、NRestarts `0`、live/ready `200`。期间修复了测试机 `repository.py` 与 `service.py` 的 `status` 参数错配，以及 `orchestrator.py` 与 `repository.py` 的 `follow_up_count` 错配。
- 该证据仍只证明事实/候选层接入和结果层消费；八字正式旺衰/格局/用神、六爻用神硬选与成败应期、梅花体用裁决、大六壬学校裁决、三术合参裁决、解梦/姓名 Provider 仍未完成。

## 本轮七政四余来源事实补齐与个人临时 smoke（2026-08-17）

- `XingmingProvider` 原本已经计算七政七曜与四余，紫炁也已经按 `xingxue-dated-mean-ziqi-v1` 公式和校准档案计算；本轮修复的是 Runtime → `QizhengBodyFact` 的字段丢失：`point_kind`、`observed_body`、`source_dependency_id`、`trace` 现在保留到 `qizheng-chart/v1`，Web 结果页增加“点类型/来源依赖”和“四余算法来源事实”表。没有新增断语、分数或浏览器计算。
- 定向回归：七政 projector `2 passed`，V53 Worker 矩阵文件在本机因真实 Runtime 条件未启用而 `10 skipped`，Web `runtime-chart` `10 passed`；新增断言覆盖实测太阳和紫炁虚点的公式 profile、校准路径和来源依赖。
- 使用用户提供的出生资料做一次性本地真实 smoke（2000-10-18 05:10、男、福建莆田涵江、`local_apparent_solar-v1`、坐标仅作本地临时输入）：V53 startup 通过，describe 返回 14 个 Provider；八字返回 19 个计算事实，紫微 26 个，七政/星命 14 个，禄命纳音 14 个，近时日运 9 个。资料只存在临时进程和临时 state 目录，未写入仓库、服务器、证据或记忆。
- 该轮进一步确认：核心盘面接入已经覆盖这些真实个人输入；剩余不是“没有接上”，而是正式裁决/深读层，以及解梦、姓名的 Provider/规则包/Typed ViewModel，风水现场完整输入、相法媒体 Adapter、三术实质互证和 P11/P12 外部门禁。

## 七政四余来源事实测试机发布（2026-08-17）

- 本轮将前述七政四余 `point_kind`、`observed_body`、`source_dependency_id`、`trace` 接线发布到测试机新 release `/opt/fateradar/releases/ui-preview-20260817-qizheng-provenance`；切换前文件保存在 `/opt/fateradar/shared/cache/qizheng-provenance-hotfix-20260817/`，旧 `current` 可回滚。
- 发布前 Web 生产 build、Backend 导入和四个目标文件哈希校验通过；切换后 API、Worker、Web、Admin 均 `active`，`/healthz`、live、ready 以及 `/`、`/qizheng`、`/bazi`、`/tools/dream`、`/tools/name` 均返回 `200`；从当前工作机访问 `http://106.14.10.235:18080` 的首页、`/qizheng`、`/bazi` 也均返回 `200`。
- Schema 闭合后又将 `qizheng-chart-v1.schema.json` 与 `reading-document-v1.schema.json` 同步到同一 release；远端 SHA-256 分别为 `50950df9aab63d8ce4488f79e7349561e048d9138bf782b5d80044afd1ecc000` 与 `2c10887e5434c3fe6f40482f56dfc37af9a219ed22c92a40df38e0d2eec5f5b4`，四个服务无需重启仍保持 active、NRestarts 为 `0`。
- 浏览入口为 [测试服务器 `/qizheng`](http://106.14.10.235:18080/qizheng)。该服务器仍是 `local + Fake` 测试环境，只供浏览和 P4-007 逐页批准；没有上传出生资料、姓名、密码、SMTP 凭据或 API key，不代表 Mac mini native-full、正式生产 Runtime、正式断法或 P12 生产准入。

## 七政四余 ReadingDocument Schema 闭合（2026-08-17）

- 复核发现七政来源字段已经进入 Pydantic/Worker/Web，但两份严格 JSON Schema 仍未声明 `point_kind`、`observed_body`、`source_dependency_id`、`trace`，同时遗漏了七政 `source_conditioned_patterns`、年度变换和寻限字段；这会让严格 `ReadingDocumentV1` 校验拒绝真实结果。
- 已同步修正 `contracts/schemas/views/qizheng-chart-v1.schema.json` 与 `contracts/schemas/reading-document-v1.schema.json`，并增加专用 ViewModel 与完整 ReadingDocument 正向合同。结果为七政定向 `2 passed`、平台合同七政相关 `18 passed/1 skipped`、全量 Backend/Contract `963 passed/127 skipped`，`git diff --check` 通过。
- 这次是文档契约闭合，不新增算法、不改变断法，也不改变测试服务器的 `local + Fake` 边界。

## 当前最终本地门禁复核（2026-08-17）

- 重新以 `PYTHONDONTWRITEBYTECODE=1` 执行当前 V53 全 Provider 黑盒矩阵：`9 passed / 1 skipped`；唯一 skip 是本机没有安装匹配的 V52 relationship release。启动 inventory 恢复为 manifest 约定的 `219/219` 文件，没有未签名的 `.pyc` 或 `__pycache__` 条目。
- `make check` 最终通过：Backend `963 passed / 127 skipped`，Ruff 通过，mypy 对 142 个源文件无错误；Web `72` 个测试文件 / `459` 个测试通过，Admin `33` 个测试文件 / `123` 个测试通过，两端 lint、typecheck 和 production build 均通过；`git diff --check` 通过。
- 这次复核确认的是当前已登记 Provider 的 Runtime → Worker → Accepted → Typed ReadingDocument 接线稳定；仍不能把 `candidate_only`、`predicate_matched_not_verdict`、`facts_only` 当成正式断语。八字正式旺衰/格局/用神、六爻用神硬选与成败应期、梅花体用裁决、大六壬学校裁决、三术合参实质互证/分歧、解梦/姓名 Provider 和 P11/P12 外部门禁仍保持未完成。

## V53 来源条件输出契约补齐（2026-08-17，本地当前 release）

- 复核发现 Bazi、风水、六爻、梅花四个 Provider 的 Runtime 已产生 `source_conditioned_patterns`，但 V53 manifest 漏掉了对应 `output_binding`；这会让来源条件事实虽进入 calculated facts，却没有正式发布契约绑定。
- 已补齐四份 manifest 的 `/facts/chart_facts/output/source_conditioned_patterns` binding 与 `outputs` 声明，并重签当前本地 release：219/219 文件哈希通过，release manifest SHA-256 为 `9000f1def70089fc6880fb135e1b1c6ae46ee7a2dc45e44beb7b45a0ff23104c`，describe digest 为 `7464229e744d8711dbdf261d758b160d2dce6744cd2f6ee9700dfdd56d145fbd`；capability shape 未改变。
- 回归结果：manifest contract `20 passed`、startup/config `48 passed`、真实 V53 Worker→Accepted→Typed ReadingDocument `9 passed/1 skipped`、process adapter/public core `40 passed`、Ruff/mypy/git diff check 通过；V53 release 无新增 `.pyc`。
- 这只是来源证据的契约闭合，不新增正式断语，也未把 `candidate_only` 或 `predicate_matched_not_verdict` 升级成结论；当前本地 release 尚未作为生产 release 发布。
- 随后完整 `make check` 通过：Backend `967 passed/127 skipped`，Ruff 与 mypy（142 个源文件）通过；Web `72 files/459 passed`、Admin `33 files/123 passed`，两端 lint、typecheck 和 production build 均通过。权威扫描明确跳过 `.claude` 工具工作树，不影响真实 `docs/` 与 `ui/tokens.css` 唯一性校验。

## P4-007/P10 V53 来源条件契约测试机复验（2026-08-17）

- 在保留覆盖前文件的前提下，将四份 Provider manifest、V53 `.mingli-release-manifest.json` 和匹配的后端 Runtime digest 配置同步到 `fateradar-prod` 测试机；备份目录为 `/opt/fateradar/shared/cache/v53-source-binding-hotfix-20260817-local-v2/before-owner-final/`。远端当前 release manifest SHA-256 为 `9000f1def70089fc6880fb135e1b1c6ae46ee7a2dc45e44beb7b45a0ff23104c`，describe digest 为 `7464229e744d8711dbdf261d758b160d2dce6744cd2f6ee9700dfdd56d145fbd`。
- 使用测试夹具和独立临时状态目录，以 `fateradar` 服务用户直接调用远端 V53 one-shot Runtime；Bazi `Prepare` 返回 `kind=prepared`、28 个 facts，并包含 `/source_conditioned_patterns` 事实，随后同一 token 的 `Complete` 返回 `kind=accepted`。该黑盒只验证来源条件事实已经穿过远端 manifest→Runtime→Prepared→Accepted，不把它升级成旺衰、格局、用神或吉凶断语，也未使用个人资料。
- API/Worker 继续为 active/running，`NRestarts=0`；本机 healthz 与 `/bazi` 均返回 `200`。浏览入口为 [测试服务器 `/bazi`](http://106.14.10.235:18080/bazi)，当前仍是 `local + Fake` 测试环境，仅供用户 P4-007 逐页浏览批准，不代表生产 Runtime、正式裁决、真实支付或 P12 生产门禁。

## 当前轮 Bazi 来源绑定修复与测试机复验（2026-08-17）

- 发现 V53 已激活的 `bazi/ditiansui-chanwei#DR-01-01` 仍引用旧输出路径 `/calendar_normalization/ganzhi`；当前 Runtime 的实际四柱事实是 `/four_pillars`，隐干事实仍是 `/hidden_stems`。修复后的严格谓词为 `nonempty(/four_pillars)` + `nonempty(/hidden_stems)`，没有增加旺衰、格局、喜忌、用神或吉凶 verdict。
- classical binding、evidence index、build/runtime binding pin 与 `.mingli-release-manifest.json` 已同步重签；本地 release `219/219` 哈希闭合，release manifest SHA-256 为 `0a9b12bfba192c41189fcb41f3e3235a138531798ed30618cdc85369eda71c7c`，describe digest 仍为 `7464229e744d8711dbdf261d758b160d2dce6744cd2f6ee9700dfdd56d145fbd`。
- 新增 Runtime matcher 回归在旧索引上先失败、修复后通过；完整本地门禁为 Backend `968 passed/127 skipped`、Web `72 files/459 passed`、Admin `33 files/123 passed`，Ruff、mypy、lint、typecheck 和两端 production build 全通过。专用本地 Runtime 的 `Describe → Prepare → Complete` 为 `14 Provider / 28 facts / accepted`。
- 测试机 `/opt/fateradar/shared/mingli-master-v53-time-check-20260817-time-evidence` 已保留旧文件备份；以 fateradar 用户远端 one-shot 验证 `DR-01-01` evidence 1 条，随后 `Complete=accepted`。同步后修正了 release 父目录 owner 以及 Backend V53 profile 的新 manifest SHA；API/Worker/Web/Admin/Nginx 全 active，API/Worker `NRestarts=0`，live/ready、Nginx healthz、`/bazi` 均 `200`。
- 本项仍只是来源条件事实的准确绑定，不能把 `predicate_matched_not_verdict` 写成正式命理结论。测试机仍为 `local + Fake`，P4-007 用户逐页批准、正式裁决/P11 深读和 P12 生产门禁仍未完成。

## 当前轮 V53 证据作用域发布输入与测试机复验（2026-08-17）

- 发现 `build_evidence_index.py` 在发布包内声明依赖 `references/matrices/evidence-scope-bindings-v1.yaml`，但旧 V53 closure 没有发布这个唯一输入；这会使下一次规则变更无法从制品自重建索引。已从当前已检查索引机械恢复 110 条作用域绑定，保留原有 1328 条规则和适用事实，不增加 active rule、候选或 verdict。
- 新输入经过编译器验证：`build_evidence_index.py --check` 为 `pass / 1328 records`，canonical JSONL 与现有 `evidence-rules.jsonl` 逐字节一致。closure 增加该 YAML 后为 58 条 explicit 文件、7 个 pattern；manifest、closure 和后端 V53 文件计数统一为 `220`，本地 manifest 220/220 哈希通过；后端受影响配置/启动/Runtime 回归 `58 passed`。
- 测试机 `/opt/fateradar/shared/mingli-master-v53-time-check-20260817-time-evidence` 已同步新 YAML、closure、manifest 和匹配的后端 profile；远端 220/220 哈希通过，作用域文件为 `fateradar:fateradar`、`0700`。服务用户 one-shot 返回 `14 capabilities / 28 facts / DR-01-01 present / Complete=accepted`；API/Worker/Web/Admin/Nginx active，API/Worker `NRestarts=0`，live/ready/healthz 和公网 `/bazi` 均 `200`。
- 备份目录为 `/opt/fateradar/shared/cache/v53-scope-input-20260817/before`。这仍是测试机 `local + Fake` 的可浏览证据，不等于正式术数裁决、Mac mini native-full、生产凭据、支付、备案或 P12 生产准入；P4-007 仍待用户逐页浏览批准。
- 本轮变更后的完整本地 `make check`：Backend `968 passed/127 skipped`、Web `72 files/459 passed`、Admin `33 files/123 passed`，Ruff/mypy、两端 lint/typecheck/production build 和 `git diff --check` 全通过。

## 当前轮六爻求财结构化来源规则接线（2026-08-17）

- 后端新增显式 `question_class=finance`，经 Liuyao API schema、Service、request compiler 进入 `Prepare.facts`；V53 Provider manifest 声明该输入并固定映射到 `chart_data.question_class`，Runtime 不从用户问题文本猜类别。
- V53 Runtime 将 `finance` 只映射为妻财/子孙候选，并把 `question_context` 保留在 `useful_spirit_selection`；新增黄金策 `HJC-R009` 的三条适用谓词：显式 finance 类别、妻财候选非空、子孙候选非空。原文绑定为研究树 `fulltext.md#L962-L964`，来源摘要、规则摘要和 applicability digest 均已写入 classical binding。
- `HJC-R009` 只以 `predicate_matched_not_verdict` 进入 `source_conditioned_patterns`，没有 `verdict`、用神硬选、成败或应期结论。真实 V53 `Runtime → Worker → Accepted → liuyao-chart/v1` 通过 `1 passed`；完整真实 Worker 矩阵 `11 passed / 1 skipped`。
- 本地 V53 当前清单为 `220/220` 文件，release manifest SHA-256 为 `a9ba0bcb772b2cd3f24a0e782e043738d91e5e9b3db66095e5d7bbb7d6a85f52`，describe digest 为 `0409a91b0b0f3c99591bcc754eb7cf316dc3bb30ccfd36ee5b7c3463cce9bd1b`，capability shape 为 `3bf92ce5d12005be6d50c01a76161e1754f49c210d6c064cb6a0e91d95db19ed`，证据索引为 `1328` 条。
- 这只完成六爻“显式问题类别 → 来源规则适用性 → 候选证据”的核心接线，不等于正式用神定夺、成败吉凶、应期裁决、六爻深读履约或 P11/P12 完成；本轮尚未把该本地 release 发布到测试服务器，也未注入密码、SMTP 凭据或 API key。

## 当前轮六爻求财测试机发布与黑盒复验（2026-08-17）

- 本地 V53 `220/220` release 已同步到测试机独立目录 `/opt/fateradar/shared/mingli-master-v53-time-check-20260817-liuyao-finance`；远端 manifest SHA-256 为 `a9ba0bcb772b2cd3f24a0e782e043738d91e5e9b3db66095e5d7bbb7d6a85f52`，目录归属为 `fateradar:fateradar`、文件/目录权限为 `0700`。切换前的 `test.env` 与 5 个后端接线文件保存在 `/opt/fateradar/shared/cache/liuyao-finance-hotfix-20260817/before`。
- 后端 API schema、Service、request compiler、Runtime 配置已以可回滚 hotfix 安装到当前测试 release；API/Worker 重启后均 active，`NRestarts=0`，公网 healthz、live、ready 均 `200`。没有修改 Web UI，也没有注入密码、SMTP 凭据、支付凭据或 API key。
- 使用测试环境现有的 operator dogfood 授权（不是支付）和虚构测试账号，显式提交 `question_class=finance` 的六爻请求；API → Worker → Accepted → `view_model.core_facts` 黑盒结果为 `liuyao-chart/v1 / accepted`。`question_context.classification_source=explicit_structured_input`、`question_class=finance`；妻财候选 `1` 个、子孙候选 `3` 个，均为 `candidate_only` 且 `hard_verdict=null`。
- 结果中的 `BSZZ-M01`、`HJC-M001`、`HJC-R009`、`HZL-M001`、`ZZR-M001` 均为 `predicate_matched_not_verdict`，没有 `verdict` 字段。该黑盒证明本轮接线在测试机闭环，不把来源规则候选升级为正式用神定夺、成败吉凶或应期结论。
- 测试入口为 [测试服务器 `/liuyao`](http://106.14.10.235:18080/liuyao)。环境仍是 `local + Fake`，只供用户 P4-007 浏览批准；正式六爻裁决、真实支付/模型履约、P11 深读和 P12 生产门禁仍未完成。

## 八字月令状态事实接入 Typed ViewModel（2026-08-17）

- V53 `bazi_fact_adapter` 现在把月令五行映射出的 `旺 / 相 / 休 / 囚 / 死` 状态，与 `bazi_reasoning_tools` 共用同一确定性映射；`interpretive_candidates.strength` 额外保留 `seasonal_state` 和来源规则 `bazi/sanming-tonghui#R-02-04`。
- Backend `BaziStrengthEvidence`、`bazi-chart/v1` Schema 和 Bazi FactContract 已同步校验该枚举及来源规则 ID。状态仍为 `evidence_only`，`hard_verdict` 必须为 `null`；没有把月令状态升级成身强身弱、格局、喜用神或吉凶结论。
- 当前本地 V53 release 为 `220/220`，manifest SHA-256 为 `37f96356c4f3273b132c950bb764cc5ee04354455245d8008299f41f2022c9a0`，describe digest 为 `0409a91b0b0f3c99591bcc754eb7cf316dc3bb30ccfd36ee5b7c3463cce9bd1b`，capability shape 为 `3bf92ce5d12005be6d50c01a76161e1754f49c210d6c064cb6a0e91d95db19ed`；真实 one-shot startup inventory 为 220 文件、14 Provider、55 reference packs、1328 evidence，14/14 capability admission 通过。
- 真实 V53 `public_natal` 和 Bazi Worker→Accepted→Typed ReadingDocument 各 `1 passed`；完整 `make check` 为 Backend `974 passed / 129 skipped`、Web `459 passed`、Admin `123 passed`，Ruff/mypy、两端 lint/typecheck/production build 和 `git diff --check` 全通过。
- 本轮只使用本机临时测试数据；没有把个人资料、密码、SMTP 凭据、API key 或真实支付信息写入仓库、发布包、服务器或证据正文。正式裁决层、P4-007 用户逐页批准、P11/P12 仍按原边界处理。

## 当前轮测试站 Web standalone 同步（2026-08-17）

- 本地 `make check` 在当前表单交互修复后重新全绿：Backend `974 passed / 129 skipped`、Web `72 files / 459 passed`、Admin `33 files / 123 passed`，Ruff/mypy、两端 lint/typecheck/production build 与 `git diff --check` 均通过。日期分段控件保留年/月/日中间态并拒绝不完整日期；该修复没有改变 Runtime 算法。
- 测试机 Web incoming 先上传到 `/opt/fateradar/shared/cache/bazi-seasonal-hotfix-20260817-v2/web-incoming/`，核对新 standalone BUILD_ID `Svuqf6nC8gB_Uc-PRP1xC`、1090 个 server 文件、261 个静态文件和无缓存目录后切换；旧 Web server/static/BUILD_ID 备份在同目录 `web-before/`，可恢复。
- 切换后 Web/API/Worker/Admin active，Web `NRestarts=0`；公网 `http://106.14.10.235:18080/api/v1/health/live`、`/api/v1/health/ready`、`/bazi` 均 `200`。远端 bundle 已包含“月令状态”和新的产品提交交互；测试站仍是 `local + Fake`，只供 P4-007 浏览批准。
- 这次没有上传出生资料、姓名、密码、SMTP 凭据、API key 或真实支付信息；Runtime 远端 one-shot describe 返回 `described / 14 capabilities / 0409a91b…`。Mac mini native-full、正式裁决、P11 深读和 P12 生产门禁仍未完成。

## 当前轮寻时事件证据类型化闭合（2026-08-17）

- 发现寻时 Runtime 已计算的 `event_evidence` 在 `TimeCheckCandidateEvidenceV1` 中仍是裸 `dict`；这会让支关系、事件年柱十神、命中状态、分数和原因在 Worker→Accepted→Typed ViewModel 之间缺少字段级校验。
- 新增 `TimeCheckBranchRelationV1` 与 `TimeCheckEventEvidenceV1`，同步 `time-check-view/v1`、`reading-document/v1` JSON Schema、Web ViewModel 类型和寻时结果测试。缺少 `natal_branch`、`event_branch`、`reasons` 等核心字段时，projector 现在 fail-closed 返回空结果，不让坏证据进入 ReadingDocument。
- 定向回归：Backend 寻时合同 `7 passed`、Web RuntimeChart `10 passed`；全量 `make check`：Backend `976 passed / 129 skipped`、Web `72 files / 459 passed`、Admin `33 files / 123 passed`，Ruff/mypy、两端 lint/typecheck/production build 与 `git diff --check` 全通过。
- 这项只闭合已有候选证据的类型接线，不新增古法校时规则，不生成“最可能时辰”、定盘、吉凶或应期结论。完整古法校时/候选淘汰/结论、正式八字/六爻/梅花/六壬裁决、解梦/姓名 Provider、P4-007 用户批准、P11/P12 外部门禁仍未完成。

## P4-007 测试站同步与黑盒复验（2026-08-17）

- 本轮四个后端/Schema 文件先上传至 `/opt/fateradar/shared/cache/time-check-typed-evidence-hotfix-20260817/incoming/`，覆盖前备份保存在同目录；本地与远端安装文件哈希一致，代码/Schema 权限修正为 `0644`，没有上传个人资料、密码、SMTP 凭据、API key 或支付信息。
- 第一次重启探针真实发现 502，日志定位为上传文件继承 `0600`，服务用户无法读取 `backend/app/charts/contracts.py`；已修正权限后重新启动，API/Worker 恢复，且 `NRestarts=0`。该故障已记录，不把第一次失败隐藏成“全程通过”。
- 最终黑盒：`/api/v1/health/live=200`、`/api/v1/health/ready=200`、`/bazi=200`、`/tools/time-check=200`、`/tools/dream=200`、`/tools/name=200`；动态 OpenAPI 含 `natal_branch` 与 `TimeCheckEventEvidenceV1`；API/Worker/Web/Admin 均 active。
- 浏览入口：[测试服务器 `/tools/time-check`](http://106.14.10.235:18080/tools/time-check)。测试站仍是 `local + Fake`，只用于用户浏览和 P4-007 逐页批准，不代表正式古法校时、真实模型、Mac mini native-full、生产支付或 P12 准入。

## 当前轮 Runtime 超时进程组回归与第二次测试站复验（2026-08-17）

- 全量门禁第一次运行发现 1 个真实失败：高负载下 Runtime 超时测试的子进程写入 marker，说明超时清理使用临时 `getpgid()` 存在竞态。adapter 现在在 spawn 后立即保存进程组 ID，所有超时/异常路径复用该 ID 执行 `killpg(SIGKILL)`；Runtime 适配器定向 `16 passed / 18 skipped`。
- 修复后完整 `make check`：Backend `977 passed / 129 skipped`、Web `72 files / 459 passed`、Admin `33 files / 123 passed`，Ruff/mypy、两端 lint/typecheck/production build 和 `git diff --check` 全通过。
- 更新后的 `runtime.py` 与 `projectors.py` 已同步到测试站；覆盖前 v2 备份在 `/opt/fateradar/shared/cache/time-check-typed-evidence-hotfix-20260817/before-v2`。最终 API/Worker/Web/Admin active，API/Worker `NRestarts=0`，live/ready、`/bazi`、`/tools/time-check`、`/tools/dream`、`/tools/name` 均 `200`，OpenAPI 仍含类型化寻时证据字段。

## 当前轮 Canwen/HeCan/Wenshi 合参证据接线补齐（2026-08-17）

- Canwen/HeCan 现在消费八字 `source_conditioned_patterns`，与既有紫微/七政来源谓词一起进入三术信号层；Wenshi 现在消费六爻 `source_conditioned_patterns`，并把大六壬 `timing` 维度中已存在的相对迟速、候选支、候选日期材料接入信号层。
- 新信号均保留 calculated fact ref；来源规则保持 `predicate_matched_not_verdict`，六壬 timing 保持候选证据，不选择用神、不形成三术互证/分歧裁决、不把候选日期写成正式应期或成败吉凶。
- 合成投影回归 `4 passed`；以本地冻结 V53 one-shot Runtime 跑真实跨术数 Worker→Accepted→Typed ReadingDocument 回归 `1 passed`，锁定八字 `DR-01-01`、六爻 `HJC-M001` 与大六壬 timing candidate signal 均未在结果层丢失。

## 当前轮 Fortune Typed ViewModel 与 ReadingDocument 闭合（2026-08-17）

- `fortune` 之前已经由 V53 Runtime 计算日运事实，但只进入通用事实面板；本轮新增 `fortune-facts-view/v1`，严格投影本命四柱、日主、月令、当前大运、目标周期、可用日期、周期机制标记和历法归一化事实。缺字段时 projector fail-closed，不从输入事实或浏览器补算。
- 新增 Backend Pydantic/ViewModel、独立 JSON Schema、`reading-document/v1` `oneOf`、Web Registry/RuntimeChart/结果页白名单；页面只显示事实与 `specific_event_policy` 边界，不生成具体事件、吉凶或人生判断。
- 移除 Worker Accepted 阶段针对 `fortune` 的旧文档例外；现在 Fortune 和其他已接入 Provider 一样，必须完成 `Accepted → Typed ReadingDocument`，结果可被历史、导出和结果页统一消费。
- 回归结果：Fortune projector + schema `1 passed`，Provider inventory `1 passed`，真实 V53 Fortune public core `1 passed`，真实单术 Worker/Accepted/Typed ReadingDocument 矩阵 `1 passed`（其余案例未在该定向命令中执行），Web RuntimeChart/Registry `14 passed`，前端 typecheck 和受影响 Ruff 通过。全量门禁与测试机同步在后续条目记录。
- 这项补的是已有日运算法的结果契约与文档持久化，不新增日运推算，也不把 `primary_mechanism_ids`、支位关系或候选标记升级为正式事业吉凶、具体事件或金额结论；正式裁决、深读、P4-007、P11/P12 仍未完成。

## P4-007 测试站同步与本轮最终门禁（2026-08-17）

- 仅热更新当前测试 release 的 `backend/app/charts/projectors.py`；覆盖前备份为 `/opt/fateradar/shared/cache/core-synthesis-evidence-hotfix-20260817/projectors.py.before`，远端新文件 SHA-256 为 `e8f0131b6b7996c5e34f6f38b3cd966e1098120da0766603ff78dbf3e2d447db`，与本地一致，旧文件 SHA-256 为 `00ba05a9…`。
- API/Worker/Web/Admin/Nginx 均 active，API/Worker `NRestarts=0`；公网 live/ready、`/wenshi`、`/canwen`、`/hecan`、`/tools/time-check`、`/tools/dream`、`/tools/name` 均返回 `200`。浏览入口为 [测试服务器 `/wenshi`](http://106.14.10.235:18080/wenshi)，另有 `/canwen` 与 `/hecan`。
- 本轮最终本地门禁：Backend `978 passed / 129 skipped`、Web `459 passed`、Admin `123 passed`，Ruff/mypy、两端 lint/typecheck/production build 与 `git diff --check` 全通过。测试机仍为 `local + Fake`，只证明当前接线可启动、可浏览，不代表真实模型/支付、正式术数裁决、Mac mini native-full、P11/P12 或用户批准完成。

## 当前轮 Fortune 测试站发布与黑盒复验（2026-08-17）

- Fortune Typed ViewModel/ReadingDocument 已以新 release 原子切换到 `/opt/fateradar/releases/ui-preview-20260817-fortune-facts`；旧 release 仍保留，可回滚。远端 `contracts.py`、`projectors.py`、`orchestrator.py`、`reading-document-v1` Schema 与 Fortune 独立 Schema 均与本地逐字节一致。
- 切换前第一次 readiness 探针因 API 冷启动约 8 秒触发自动回滚；没有改代码，改用 30 秒 readiness 轮询后切换成功。最终 API/Worker/Web/Admin/Nginx 全部 `active`，API/Worker `NRestarts=0`，live/ready、公共页面和 OpenAPI 均返回 `200`，OpenAPI 已包含 `fortune-facts-view/v1`。
- 用户可浏览：[今日解读](http://106.14.10.235:18080/app/fortune/today)、[近七日解读](http://106.14.10.235:18080/app/fortune/week)，也可复核 [/bazi](http://106.14.10.235:18080/bazi) 与 [/tools/time-check](http://106.14.10.235:18080/tools/time-check)。测试站仍是 `local + Fake`，只证明当前结果层可启动、可浏览，不代表正式裁决、真实模型、生产支付或 P12 准入。
- 本轮没有上传个人出生资料、密码、SMTP 凭据、API key 或真实支付信息；P4-007 仍等待用户逐页浏览批准。
- 文档更新后的完整本地 `make check` 为 Backend `979 passed / 129 skipped`、Web `72 files / 460 tests`、Admin `33 files / 123 tests`；Ruff、mypy、两端 lint/typecheck/production build 与 `git diff --check` 均通过。测试命令设置了 `PYTHONDONTWRITEBYTECODE=1`，没有向签名 Runtime release 写入字节码缓存。

## Fortune 真太阳时公共事实与七政观察点脱敏（2026-08-17）

- 授权本机真实资料 smoke 发现 Fortune 的公开 `calendar_normalization` 绑定到了目标民用日的原始日历对象：既没有展示本命真太阳时状态，又可能把出生时刻、地点和坐标带入公开 ViewModel。V53 Fortune 现在从 `birth_fact_layer.calendar_normalization` 生成与 Bazi 同源的公共白名单摘要，目标周期仍保持已声明的 `civil_day` 语义。
- `FortuneCalendarNormalization`、独立 `fortune-facts-view/v1`、`reading-document/v1` 与 Web 类型均改为关闭式嵌套合同；`civil_datetime`、`instant_utc`、`location`、经纬度及其它未声明字段会 fail-closed，不能再经 projector/Schema 透传。
- 同一矩阵继续发现七政公开 `ephemeris.observer`、`ephemeris.instant_utc` 和 `ming_shen` 重复携带观察点原始输入。公开七政合同现在只保留 ephemeris 引擎/坐标系摘要和已计算的命度、身度、间隔、恒星时等结果；Runtime 内部仍使用原始观察点完成天体与宫位计算，天体位置、宫位、四余与来源 trace 没有被删除。
- V53 已重新签名并通过 startup inspector：`220/220` 文件、`14/14` Provider、55 个参考包、1328 条证据；release manifest SHA-256 为 `bb07e75a6f439599cd62a6e3570e11312076efaf06f162e74d6c7bd3fed61971`，describe digest 为 `3f8863b313f62a2b773720c98193486a096f6dfbf8ba3335f8b1819e596e8ad1`，capability shape 仍为 `3bf92ce5d12005be6d50c01a76161e1754f49c210d6c064cb6a0e91d95db19ed`；release 内无 `.pyc`/`__pycache__`。
- 授权个人资料仅在自动清理的本机临时目录和进程内运行，未记录具体资料值；16 个产品入口全部完成真实 `Runtime → Worker → Accepted → Typed ReadingDocument`，结果为 `16/16 accepted-typed-redacted`，Fortune 明确返回 `local_apparent_solar-v1 / apparent_solar_applied`，所有公开 ViewModel 均未命中出生时刻、地点、经纬度或 `/input/`。仓库合成 golden 矩阵 `1 passed`，真实 public-core `6 passed`。
- 最终 `make check`：Backend `981 passed / 129 skipped`，Ruff 通过，mypy 142 个源文件无错误；Web `72 files / 460 tests`、Admin `33 files / 123 tests`，两端 lint/typecheck/production build 全通过，`git diff --check` 通过。该项只修真实算法事实接线与公开隐私边界，不新增旺衰、用神、成败、应期、吉凶或具体事件 verdict；测试服务器同步与用户 P4-007 浏览批准在后续条目单独记录。

## P4-007 Fortune/七政公共事实测试站发布（2026-08-17）

- 新 app release 为 `/opt/fateradar/releases/ui-preview-20260817-public-privacy`，新 Runtime 为 `/opt/fateradar/shared/mingli-master-v53-time-check-20260817-public-privacy`；旧 app/Runtime 均保留。切换前的 `/etc/fateradar/test.env` 与旧 current target 保存在 `/opt/fateradar/shared/cache/public-privacy-20260817/`。
- 第一次远端 inspector 调用在执行前失败，原因是旧版 rsync 把本机工作区的 `backend/` 目录模式 `0700` 带入新 release，服务用户无法穿越目录；已将本轮 app 目录恢复为与旧 release 相同的 `0755`，业务文件保持 `0644`，Runtime 目录/文件保持 `fateradar:fateradar/0700`。修正后服务用户 inspector 为 `220 files / 14 providers / 55 reference packs / 1328 evidence`，describe/shape 与本地 pin 完全一致。
- 原子切换后的 readiness 轮询前 8 次因冷启动返回 `502`，随后在 30 秒窗口内恢复，没有触发回滚。最终 `/api/v1/health/live`、`/api/v1/health/ready`、`/bazi`、`/qizheng`、`/app/fortune/today`、`/app/fortune/week`、`/tools/time-check` 均为 `200`；API/Worker/Web/Admin/Nginx 全 active，API/Worker `NRestarts=0`，切换后错误级日志为空。
- 6 个应用/Schema 文件的远端 SHA-256 与本地逐字节一致。远端 synthetic one-shot 黑盒确认 Fortune 为 `fortune-facts-view/v1 / local_apparent_solar-v1 / apparent_solar_applied`；七政 ephemeris 只含 `schema_version, engine, coordinate_convention`，命身只含推导结果字段，两个 ViewModel 的原始输入脱敏断言均通过。
- 本次上传源只有签名 Runtime、应用代码与 Schema，没有上传授权个人 smoke 资料、姓名、密码、SMTP/API/支付凭据。浏览入口：[今日解读](http://106.14.10.235:18080/app/fortune/today)、[近七日解读](http://106.14.10.235:18080/app/fortune/week)、[七政四余](http://106.14.10.235:18080/qizheng)。测试站仍用于 P4-007 用户浏览批准，不代表正式裁决、真实模型/支付或 P12 生产准入。

## 六爻求财唯一可见用神爻受限裁决（2026-08-17，本地）

- `HJC-R009` 已核验的裁决范围仍是“求财以妻财为主、子孙为辅，兼看兄鬼父”。本轮只在 Runtime 盘内恰有一个 `visible_line` 妻财候选时，以“已核验角色 + 盘面唯一性”定位具体爻位；示例卦 `(6, 7, 8, 9, 6, 7)` 裁定第 4 爻。该结果只回答主用神爻的身份，不判断旺衰、救应、成败、吉凶或应期。
- 多个可见妻财爻返回 `unresolved_multiple_visible_lines`，盘内没有可见妻财爻时返回 `unresolved_no_visible_line`；两者的 `specific_line_selection` 都必须为 `null`。这是有意边界：《增删卜易》“两现章”正文同时记录古法排序及相反验例，当前不能把“动优先/旺优先/不空不破优先”写成无条件固定权重；伏神或变爻也不能未经另条核验规则自动升为主用神。
- Backend 新增关闭式 `LiuyaoSpecificLineAdjudication`、`LiuyaoRoleAdjudication` 与 `LiuyaoUsefulSpiritSelection`，联合校验顶层与嵌套爻位一致；`liuyao-chart/v1` Schema 和 Web ViewModel 类型同步闭合。页面与 Wenshi 合参信号现在显示“第 N 爻（盘内唯一可见妻财爻）”，多候选仍明确显示未裁定，页面不自行排序。
- Runtime 三类卦例与篡改拒绝回归、Backend 投影/Wenshi 合参、Web 展示共通过 `7 + 32` 项定向测试；真实冻结 Runtime 公开核心 `1 passed`，真实 14 Provider Worker→Accepted→Typed ReadingDocument 矩阵 `1 passed`，六爻深读/求财定向 `2 passed`。Ruff、Backend 受影响 mypy、Web typecheck 通过；Runtime release 无 `.pyc`/`__pycache__`。
- 本地 V53 仍为 `220/220` 签名文件，release manifest SHA-256 为 `066aa9a9fe0f887f6b1e5cab48e56b7ef1096c6b143db640e56a4109acfac6e1`；HJC-R009 的证据作用域也已改为“允许唯一可见候选定位、禁止多候选/非可见候选排序及结果裁决”，证据索引重建检查保持 `1328` 条且通过。describe digest 与 capability shape 未改变。本轮未上传测试服务器，也未使用或写入个人资料、密码、SMTP/API/支付凭据。
- 六爻剩余核心缺口是：多现/伏神/变爻取舍的正式来源裁决、月日旺衰与空破冲合的综合权衡、动变生克和救应、成败与应期。上述完成前，P10-006/P10-009、P11 深读和 P12 准入继续保持未完成。

## 六爻用神两现且一动一静的取爻裁决（2026-08-17，本地）

- 修正 `ZR-04-04` 旧规则摘要：不再声称“两静一律取临日月、再取近世”。核验原文 `fulltext.md#L5895` 明确“两爻俱动或俱静择旺；仅一爻发动取动爻”，`fulltext.md#L1076` 同时记录旬空/月破的相反占验，因此 Runtime 只激活“恰有两个可见候选且仅一个发动”的窄分支；同动或同静仍等待完整旺衰综合裁决。
- `specific_line_adjudication` 新增可见候选数、发动候选数、两组爻位及独立取爻来源。卦例 `(6, 6, 6, 6, 6, 7)` 的可见妻财为第 3、6 爻，仅第 3 爻发动，Runtime 以 `ZR-04-04` 裁定第 3 爻；两静卦例 `(6, 6, 7, 7, 6, 7)` 保持 `unresolved_multiple_visible_lines`。唯一可见与无可见分支继续按原边界运行。
- Backend Pydantic、`liuyao-chart/v1`、Web ViewModel、结果页与 Wenshi 投影已同步；用户可看到“妻财两现，仅此爻发动，按核验规则取用”以及 `ZR-04-04`，但页面仍明确不判断旺衰、救应、成败或应期。错误的候选计数、发动爻子集、状态/取爻不一致或缺来源会 fail-closed。
- 经典证据清单同时修复 `HJC-R009` 将真实换行误写成字面 `\\n` 的既有锚点问题；带研究原文的 1328 条严格证据编译通过，`build_evidence_index.py --check` 通过。Runtime `6 passed`，Backend 投影 `2 passed`，Web `33 passed` 且 typecheck 通过；真实 startup/public core `1 passed`，旧唯一可见与新两现一动的 Worker→Accepted→Typed ReadingDocument 各 `1 passed`。Ruff、mypy、JSON 语法检查均通过。
- V53 release 仍为 `220/220`，无 `.pyc`/`__pycache__`，当前 manifest SHA-256 为 `a8e93987facbc2fec25677a5fd5ea67d5edeb7cd9157b6b2f1b18a2c342b7ad0`；describe digest `3f8863b313f62a2b773720c98193486a096f6dfbf8ba3335f8b1819e596e8ad1` 与 capability shape `3bf92ce5d12005be6d50c01a76161e1754f49c210d6c064cb6a0e91d95db19ed` 未改变。本轮未上传测试服务器，也未使用个人资料或任何凭据。
- 六爻下一层缺口缩小为：两爻同动/同静时的完整旺衰取舍、伏神/变爻取用、月日空破冲合与动变救应、成败、应期。P10-006/P10-009 因此继续 `IN_PROGRESS`，不能把本次具体爻身份裁决写成事件结果。
