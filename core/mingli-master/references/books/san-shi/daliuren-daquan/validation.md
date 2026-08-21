# 《大六壬大全》Validation Report

**validated_at**: 2026-07-10

**pack_status**: `static_evidence_validation_passed`

**formal_cast_status**: `deterministic_cast_enabled_interpretation_uncalibrated`

**scan_collation_status**: `pending`

## 结论

本包已从“行号切片即完成”的旧状态重建为可审计证据包：完整来源已登记，两套十二卷已分别建图，核心规则有精确短引、前置条件、执行、停止和 adapter 字段，关键内部冲突不再静默抹平。

静态来源与格式校验已经通过；本地大六壬 adapter v2 也已完成结构计算与全空间不变量测试。这里的“通过”仍不表示影印逐页校勘、模型解释盲测或现实预测准确率已经通过。

## 已执行校验

| check | result | detail |
|---|---|---|
| required pack files | PASS | 要求的 10 个文件齐全；另保留 1 个兼容 `section-map.md` |
| YAML parse | PASS | `source-manifest.yaml` 可由 Ruby Psych 解析 |
| cangjie manifest schema | PASS | 必填字段 0 缺失；`complete_chapter_set` 为允许状态；`distillation_allowed=true` |
| JSON parse | PASS | `test-prompts.json` 可由 Ruby JSON 解析 |
| manifest local files | PASS | 17/17 文件存在且 SHA-256 与 manifest 一致 |
| normalized checksum | PASS | `4c5ec0c8ea1f7b36deaf1db317cfa4407b090ad4ed909a3b8a431dced0a25d9d` |
| normalized line count | PASS | 13800 |
| scan checksum | PASS | `38d40b5cb9beb1282ea33c794224cee148012c8c1fcba7b2f3952901f816f2db` |
| scan file type | PASS | `DjVu multiple page document` |
| Kanripo checksums | PASS | 提要、12 卷与 Readme 共 14/14 匹配 |
| Kanripo core witness spot-check | PASS | 元首/重审、昴星、别责、八专五日、返吟及 WYG 卷五课经题均命中 |
| quote registry IDs | PASS | 53 条、53 个唯一 ID、无重复 |
| exact quote hit | PASS | 53/53 在声明的 normalized 精确行内连续命中 |
| cangjie quote limit | PASS | 53/53 均不超过 150 字 |
| normalized container quote coverage | PASS | N01-N12 均至少有一条 exact quote |
| quote reference integrity | PASS | pack 内引用的 53 个 DLQ ID 全部存在，无悬空 ID |
| executable rule schema | PASS | 16/16 卡均有 source layer、quote、line、adapter fields、preconditions、execution、stop/exception、conflicts |
| procedure schema | PASS | 8/8 流程均有 evidence、preconditions、steps、adapter fields、output、stop/exception |
| source-layer vocabulary | PASS | 规则使用的 4 类 layer 全部在 manifest 注册，无未知 layer |
| test schema | PASS | 19 个唯一测试：12 should-trigger、3 should-not-trigger、4 edge-case |
| local adapter core | PASS | `mingli-master.liuren_fact_adapter` 2.0.1；九宗门算法为主，720 表仅作旁证 |
| full combination invariants | PASS | 60 日 x 12 时支 x 12 月将，共 8,640 组合均通过独立 validator |
| 720-table audit | PASS with conflicts | 720/720 格式有效；发现 4 条课名和 16 条涉害三传结果冲突，古法算法优先 |
| classical fixtures | PASS | 元首、重审、比用、涉害、昴星、别责、八专、伏吟、反吟均有回归课例 |
| model blind evaluation | NOT RUN | `evaluation_status=not_run`，不伪称通过 |

## 十二容器短引覆盖

| normalized container | quote count |
|---|---:|
| N01 | 11 |
| N02 | 2 |
| N03 | 2 |
| N04 | 2 |
| N05 | 3 |
| N06 | 1 |
| N07 | 18 |
| N08 | 1 |
| N09 | 1 |
| N10 | 1 |
| N11 | 6 |
| N12 | 1 |

该表只证明每个容器进入证据索引，不等于各容器规则密度相同，也不等于全文逐句蒸馏。

## 红线复核

| red line | status |
|---|---|
| 不从局部摘要伪装整书 | PASS：normalized 完整容器 + Kanripo 完整十二卷 |
| 不把结构行号写成 100% 蒸馏 | PASS：旧 261 done 已撤销，规则明确 selective |
| 原典、提要、现代合成分层 | PASS |
| 每条可执行规则有精确出处 | PASS |
| 不让 LLM 手算历法与课盘 | PASS：DLR-00 / DLP-02 至 DLP-05 强制 adapter |
| 冲突不静默裁判 | PASS：柔日别责、天乙 profile、卷次、毕法编号均显式 |
| 天乙正文俗例与四库订正分开 | PASS |
| 实际起课必须走本地确定性 adapter | PASS：本地 v2 + 独立 validator + gate 均已接入 |

## 已发现并修正的旧错误

1. **元首/重审**：修正为上克下元首、下贼上重审；normalized 兵占反置另列冲突。
2. **昴星**：按阳日酉上、阴日酉下和明确的中末字段，不用“虎视”别名驱动算法。
3. **别责**：阳日规则与阴日规则拆开；阴日支本身/上神的书内“存疑”由两个显式 profile 保留，输出同时记录采用项与备选项。
4. **八专**：由旧八日表改为本书明载五日；有克先论克，无克才顺逆数三。
5. **天乙贵人**：删除全局“昼某夜某”的静默简化，改为显式 profile 和来源表。
6. **依赖**：删除对兄弟书和外部 conflict matrix 的强制权威依赖；删除未定义工具作为事实来源。
7. **覆盖状态**：撤销“261/261 done”与虚假完成率，拆成结构、短引、规则、影印校勘四种指标。

## 剩余风险

### R1 文渊阁页图尚未建立

第 0808 册有 987 页，但尚未标出《大六壬大全》起讫页并把 Kanripo 页叶映射到扫描页。当前不得给扫描页码。

### R2 两套卷次未最终裁定

normalized 与 Kanripo/WYG 的卷次和篇幅差异显著，尤其 N04/N05、课经卷界和分野位置。`chapter-map.md` 的交叉表是工作映射，不是最终版本学结论。

### R3 表格和盘式失真

卷一神煞、贵神图、卷六分野、课经课盘等依赖空格或图式；纯文本压平后不能直接硬编码。

### R4 井栏与柔日别责仍需更多独立金标

adapter 已按课经、订讹与 WYG 见证实现返吟井栏，并为柔日别责提供两个有来源的显式 profile；基础课例已通过。当前不足是独立于实现和 720 表之外的成套历史金标仍少，因此这两支的算法置信度低于元首、重审和普通比用。

### R5 天乙订正表不在本包内完整展开

四库提要说明存在订正，但完整逐日干 mapping 应从《星历考原》《协纪辨方书》各自 reference pack 取得。当前只能要求 profile 明示，不能凭提要补表。

### R6 规则覆盖是选择性的

16 张规则卡没有穷尽全部神煞、类神、兵占、课经课体和毕法一百法。未卡片化内容应继续走“原文定位 -> 规则卡 -> 测试”的流程，不能直接由模型概括成新规则。

### R7 没有现代统计准确率证据

当前只能验证来源忠实度、排盘可复现性和规则实现一致性。若要回答“预测准确率”，还需独立的预注册样本、时间戳、真实结果标签、基线和盲评数据集。

## 未执行项

- 文渊阁影印逐页、逐图、逐疑字校勘。
- 对全部 19 个 prompt 的独立模型盲测。
- 传统贵人 profile 与订正 profile 的双盘 golden fixtures。
- 柔日别责、涉害复等、返吟井栏的更多独立金标集。
- 现实预测的统计验证。

## 正式解释放行条件

1. adapter 输出 DLP-02 至 DLP-05 的完整字段和 source trace。
2. 元首/重审、昴星、八专、伏吟的基础 fixtures 全过。
3. 柔日别责必须在 JSON 中明示 profile 与异文备选；返吟井栏必须给出专分支 trace。
4. 天乙贵人 profile 必须写入 JSON；双 profile 结果可并列复算。
5. 全空间测试无崩溃、无无声 fallback、无不可能的干支时。
6. 在第 1 至 5 项通过时可做传统解释；19 个 prompt 的独立盲测和现实统计校准状态仍必须标为 `not_run/uncalibrated`，不得包装成预测准确率。
