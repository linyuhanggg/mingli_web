# 时间语义与真太阳时重构（V5.1）

基线 HEAD：`2586700`。本分支：`codex/mingli-v51-portable-conversation-core-20260730`。

本文档记录时间语义与真太阳时（地方视太阳时）重构的现状调用图、最终架构、
三种口径定义、均时差算法来源与误差、13 Provider 时间语义矩阵、profile 数据
路径、兼容与状态升级行为、测试证据，以及明确不支持的内容。文档以代码真实
数据流为准，不沿用旧计划文档的推测。

## 1. 现状调用图（重构前）

重构前 `calendar_core.normalize_calendar` 只支持两种口径：
`civil` 与 `longitude_mean_solar-v1`。`true_solar_time.equation_of_time`
显式写为字符串 `"not_applied"`，所谓“太阳时”仅做经度平太阳时修正，并非完整
真太阳时。

时间字段的真实数据流（按代码建立）：

```
Command.facts / RuntimeContext.subject_profiles
  -> ReadingRequest.birth_data（出生类）或 request.metadata（事件类）
    -> Provider.calculate()
      -> bazi/liuren/ziwei/fortune adapter
        -> calendar_core.normalize_calendar(civil_datetime, timezone, location,
             longitude, latitude, coordinate_source, zi_hour_policy,
             time_basis_policy)
          -> {time_basis, ganzhi, calendar_digest, ...}
```

重构前的缺陷：

- **Liuren、Ziwei、Fortune natal** 静默丢弃 `time_basis_policy`，始终按
  `civil` 归一化。用户/profile 选择平太阳时或视太阳时，仍得到民用时日历事实。
- `adapter_validate` 的 Liuren 校验硬编码 `time_basis_policy="civil"` 重算
  digest，使非民用 Liuren 日历被判为 digest 不匹配。
- bazi CLI argparse 的 `--time-basis-policy` choices 仅含旧两值，拒绝
  `local_apparent_solar-v1`。
- 选择视太阳时但缺坐标时，`normalize_calendar` 抛 `ValueError`，经子进程包裹
  变成 `RuntimeError`，最终落到 `Stopped(reason="error")`，而非结构化 NeedInput。
- Provider 各自决定时间口径，generic core 无单一权威；manifest 不声明时间语义，
  无法机器校验“声明支持却未消费”或“消费却未声明”。

## 2. 最终架构

**共享 Calendar Module 是唯一时间换算权威。** 所有 Provider 的时间字段都经
`calendar_core.normalize_calendar` 归一化为同一份 digest-bound 日历事实；
没有任何 Provider 自行调用 sxtwl 或重算时柱。

`normalize_calendar` 输出 `time_basis` 结构块（schema 升至
`mingli-calendar-normalization-v2`）：

| 字段 | 语义 |
|---|---|
| `policy` | 所选口径 |
| `standard_meridian_degrees` | 标准时区对应标准经线 |
| `longitude_correction_seconds` | 经度平太阳修正（已应用） |
| `equation_of_time_seconds` | 均时差（视 − 平），仅视太阳时口径计算 |
| `total_correction_seconds` | 经度修正 + 均时差 |
| `local_mean_solar_datetime` | 地方平太阳时 |
| `local_apparent_solar_datetime` | 地方视太阳时（= effective） |
| `algorithm` | 均时差算法块（仅视太阳时口径非空） |
| `boundary` | 最近时辰边界、距离、是否改变时柱、是否在误差范围内 |

共享事实同时保留民用 `solar_date/lunar_date` 与口径修正后的
`effective_solar_date/effective_lunar_date`。前者用于审计用户输入，后者供真正依赖
修正后历日的算法消费；因此跨午夜时不会出现“时柱已换日、农历日仍停在前一天”
的半修正状态。

`boundary` 块保证接近时辰边界时仍返回确定性结果与明确边界提示，不变成空回复。

**Provider 时间语义由 manifest 声明，generic core 不维护按 Provider ID 分支的
时间规则。** 每个 manifest 声明 `time_semantics`：`role`、`input_time`、
`supported_policies`、`default_policy`、`unsupported_fallback`、
`coordinates_required_policies`。base provider 的 `_missing_time_basis_inputs`
仅读该声明：选择需要坐标的口径但缺坐标时，`prepare()` 返回结构化非空
`ProviderNeedInput`（longitude/latitude/coordinate_source）。

## 3. 三种口径的精确定义

记 `civil` 为带时区的民用时间，`standard_meridian = standard_offset_hours × 15`，
`longitude_offset = longitude − standard_meridian`。

- **`civil`**：不施加太阳修正。`longitude_correction_seconds = 0`，
  `equation_of_time_seconds = 0`，`effective = civil`。缺坐标不阻止排盘。
- **`longitude_mean_solar-v1`**：地方平太阳时。
  `longitude_correction_seconds = round(longitude_offset × 240)`（4 分钟/度）。
  `effective = civil + longitude_correction` = `UTC + longitude/15`。
  需要实测坐标。
- **`local_apparent_solar-v1`**：完整地方视太阳时 / 真太阳时。
  `equation_of_time_seconds = round(EoT(UTC_instant))`，
  `total = longitude_correction + EoT`，
  `effective = civil + total`。

均时差符号约定：

```
equation_of_time = apparent_solar_time − mean_solar_time
total_correction = longitude_correction + equation_of_time
effective_time   = civil_time + total_correction
```

## 4. 均时差算法来源、版本、有效范围与误差

- 算法 ID：`astronomy-engine-apparent-solar-eot-v1`
- 版本：`astronomy-engine-2.1.19`
- 来源：astronomy-engine 的视太阳时角（Greenwich 观测点 `HourAngle(Sun, t)`），
  内含光行差、章动与 ΔT。EoT 与观测经度无关：
  `EoT = apparent_solar_time − mean_solar_time`，
  `apparent = (hour_angle + 12) mod 24`，`mean = UTC_time_of_day mod 24`。
- 有效范围：`1900-01-01..2100-12-31`（`equation_of_time_seconds` 对年份越界直接 raise，不静默计算）
- 误差：`uncertainty_seconds = 30`。这是经独立 oracle（Meeus/NOAA 近似，本身为约 30s 误差的近似算法）交叉验证后能承诺的边界；astronomy-engine 理论精度更高，但未用更高精度独立源验证前不对外宣称。该值同时参与时辰边界 `within_uncertainty` 判定。

**独立 oracle**（不调用生产实现）：

1. 测试内独立 Meeus/NOAA 近似纯函数（与生产不同算法族），交叉校验符号与量级，
   容差 45s。
2. 冻结公开常量：年度极值（2 月约 −14.2′、11 月约 +16.4′、5 月约 +3.7′、
   7 月约 −6.3′）与零点（4/15、6/13、9/1、12/25 附近）。
3. 用户报告回归案例区间（均时差 +14′~+16′、视太阳时 05:20–05:22）。

astronomy-engine 与 Meeus 近似在回归案例上吻合至约 2s（889s vs 887s）；独立
oracle 容差为 30s（Meeus 近似本身的误差量级）。

## 4.1 公开接口与 profile 数据路径

公开 `execute(Command)` 只路由 manifest 声明的 input_fields。每个消费时间的
manifest 现声明 `longitude/latitude/coordinate_source/time_basis_policy/
coordinate_accuracy_meters/zi_hour_policy`（出生类映射 `birth_data.*`，事件类映射
`metadata.*`），故一份
携带完整坐标与时间口径的 Command 能端到端到达 Provider，不再被静默丢弃。

缓存友好的 `describe` 公开每个能力的结构化 `time_semantics`，宿主只需传递 opaque
policy ID；宿主不解释算法、不重算时间，也不复制 Provider 规则。

`RuntimeContext.subject_profiles` 必须按 manifest input field id 建键（如
`birth_datetime_or_four_pillars`、`longitude`、`time_basis_policy`）；旧槽位名
（如 `birth_datetime` 单独用于八字、`true_solar_time_policy`）不满足公开能力的
必填输入组，会重复要求出生资料。内联 facts 与 profile 同路径产生相同的
`calendar_digest`、四柱与 prepared brief（见 `test_provider_time_policy_matrix.
PublicInterfaceTimeSemanticsTests`）。

## 4.2 边界与精度强制

- `equation_of_time_seconds` 对 1900–2100 之外的年份直接 raise。
- `coordinate_accuracy_meters` 校验有限且非负（拒绝 NaN 与正负无穷）。
- 时辰边界 `within_uncertainty = |distance| ≤ EOT_uncertainty + 坐标时间不确定度`，
  坐标时间不确定度 ≈ `accuracy_meters / (463.8·cos(lat))` 秒；百公里级坐标误差会使
  跨时辰案例落入不确定区间。
- Provider 收到 manifest 未声明支持的口径时，base provider 返回
  `ProviderUnsupported`（→ `Stopped(unsupported)`），不静默降级。
- 任一嵌套共享历法事实落在不确定边界内时，brief 返回一个
  `limit.unresolved_time_boundary`；公开中文来自 message catalog，generic core
  不硬编码领域术语。该限制适用于 Fortune 的本命层，而目标周期仍保持 civil。

## 5. 13 Provider 时间语义矩阵

| Provider | role | supported_policies | default | 缺坐标(需坐标口径) | 消费字段来源 |
|---|---|---|---|---|---|
| bazi | pillar_clock | 三种 | civil | NeedInput | birth_data |
| ziwei | pillar_clock | 三种 | civil | NeedInput | birth_data |
| liuren | pillar_clock | 三种 | civil | NeedInput | metadata |
| luming-nayin | pillar_clock | 三种 | civil | NeedInput | birth_data |
| xingming | physical_instant | 三种 | civil | NeedInput | birth_data |
| liuyao | civil_schedule | 三种 | civil | NeedInput | metadata |
| meihua | civil_schedule | 三种 | civil | NeedInput | metadata |
| qimen | pillar_clock | 三种 | civil | NeedInput | metadata |
| taiyi | civil_schedule | 三种 | civil | NeedInput | metadata |
| fortune | civil_schedule | 三种 | civil | NeedInput(natal) | profile(natal)/reference(target) |
| selection | civil_schedule | civil | civil | 不适用（civil_only） | reference（候选日，硬编码 civil） |
| physiognomy | not_applicable | — | civil | 不适用 | 无时间输入 |
| fengshui | not_applicable | — | civil | 不适用 | 无时间输入 |

说明：

- **bazi/ziwei/liuren/luming-nayin/xingming/liuyao/meihua/qimen/taiyi/fortune**
  的计算中都保留实际消费的 v2 共享历法事实；测试直接核对其中的 policy，不以
  “任意 digest 变化”替代语义验证。
- **bazi/ziwei/liuren/luming-nayin/qimen**：构造跨时辰案例，公开盘面中的实际时柱、
  `time_index`、宫位或盘局必须随有效时间变化。
- **xingming**：天体位置使用 `instant_utc`（物理 UTC 瞬间）与观测坐标，严禁因
  真太阳时移动物理天体瞬间；policy 改变共享历法口径与边界元数据，但相同物理
  瞬间的天体经纬度和宫位必须保持一致。
- **ziwei**：排盘基于 `calendar["effective_datetime"]`（视太阳时口径下即真太阳时），
  非民用时；跨时辰修正会改变 `time_index` 与宫位，跨午夜时同时使用修正后的日期。
- **liuyao/meihua/taiyi**：指定投掷的六爻主卦与同年太乙年盘应保持不变；按时间
  起卦的梅花盘消费修正后的时辰和 `effective_lunar_date`，跨时辰或跨午夜时按真实
  生效资料变化。不能用“所有主结果必须变化”的错误断言逼迫算法改写正确结果。
- **fortune**：natal 继承 subject profile 的时间口径并保留自己的 calendar；目标
  日、日层扩展和参考周期始终 civil，二者不混用。
- **selection**：择日按社会时间评估候选日，硬编码 civil，不读取请求中的
  `time_basis_policy`，故诚实声明 `civil_only`，非“接受后忽略”。
- **physiognomy / fengshui**：无时间输入，`not_applicable`。

矩阵校验规则（`test_provider_time_policy_matrix` + `test_public_time_semantics`）：
声明支持的口径必须出现在真实共享历法事实中；需要改变盘面的算法核对精确公开
字段；物理不变量和年／指定投掷不变量反向锁定；消费的口径必须被声明；不适用者
不被强行加入真太阳时。生产验收只通过 `ReadingInterface.execute(Command)`，直接
Provider 调用仅用于结构审计。

## 6. profile 数据路径

`_default_profile_changes` 在无内联 `birth_data` 且 `goal.use_default_profile=True`
时，将 `RuntimeContext.subject_profiles["current_user"]` 整体复制为 `birth_data`
（保留 `time_basis_policy` 与坐标）。因此同一份出生资料：

- 直接放入 `Command.facts`（内联 birth_data）
- 来自 `RuntimeContext.subject_profiles`

经同一路径进入 `Provider.calculate`，产生相同的 `calendar_digest`、四柱与
Provider calculation identity（见 `test_time_basis_profile_consistency`）。

规则：profile 已有可信坐标与来源时自动复用，不重复询问；profile 仅有地点字符串
无坐标时，选择视太阳时不会假装已做真太阳时（缺坐标即 NeedInput / 失败，不静默
民用）；`civil` 缺坐标不阻止排盘。地址字符串不等同于坐标，核心不凭字符串猜经纬度。

## 7. 兼容与状态升级行为

- `SCHEMA_VERSION` 升至 `mingli-calendar-normalization-v2`。`CONVENTION_VERSION`
  保持 `1.0.2`（节气/立春约定未变）。
- `civil` 与 `longitude_mean_solar-v1` 的 `effective_datetime` 与 `true_solar_time.status`
  行为不变；`true_solar_time` 现报告数值修正而非字符串 `"not_applied"`。
- `local_apparent_solar-v1` 为新增口径；旧调用不传该参数时默认 `civil`，行为不变。
- `coordinate_accuracy_meters` 为新增可选字段（默认 null）。
- `effective_solar_date/effective_lunar_date` 为 v2 共享历法的追加字段；原
  `solar_date/lunar_date` 继续表示民用输入日期，避免把审计输入与算法生效日期混为
  一个字段。
- manifest 新增 `time_semantics` 块（仅追加，未重格式化现有内容）；
  `manifest_digest` 随之变化并由 catalog 动态重算。

## 8. 测试证据

| 提交 | 测试 | 覆盖 |
|---|---|---|
| f4ed6e0 | `test_calendar_solar_semantics`（29） | 三口径、均时差符号/极值/零点、独立 Meeus oracle、莆田回归、边界跨时辰、digest 稳定性、坐标/时区边界 |
| 4f77c98 | 实现使上述测试转绿 | — |
| e1f7b08 | `test_time_basis_profile_consistency`（7） | 内联==profile、不串用、不假装真太阳时、bazi/ziwei/liuren 消费 policy |
| 0e08cbb | manifest 声明 + base NeedInput | — |
| 16a9f41 | `test_provider_time_policy_matrix`（10） | 13 manifest 矩阵、声明==消费、NeedInput、describe、cross-host 同构 |
| 48738bb | 公开接口 input_fields + profile 文档 | Command 端到端携带坐标/时间口径；profile 按 field_id 建键 |
| afe1ce4 | bazi 输出一致性 + ziwei 用 effective | bazi 无 applied/not_applied 矛盾；ziwei 排盘随 policy 变化 |
| 76bc4ac | 边界与精度强制 | 不支持口径返回 Unsupported；EoT 范围强制；坐标精度校验与参与边界 |
| 7660105 | 原始 13-provider 矩阵 | 首次覆盖公开 Command；其中“所有关键结果必须变化”的断言过强，本轮已修正 |
| 本轮接管 | `test_public_time_semantics`（23）+ 更新后的 Provider 矩阵 | 10 个涉时 Provider 真实公开接口、缺坐标 NeedInput、紫微跨时辰/跨日期、梅花跨日期、星命物理不变量、六爻/太乙不变量、梅花/奇门变化、Fortune 双时钟、坐标误差公开限制、Describe/Prepare CLI 同构 |

本轮最终验收使用固定运行时，结果如下：

- 时间语义、公开 Interface、profile、闭世界 brief 与 Skill 最小接口：135/135 通过。
- 不依赖外部全文的原有 Provider、历法、证据扩展、目录驱动回归：105/105 通过。
- release closure、隔离安装、runtime pin 与 launcher 非空失败：41/41 通过。
- 13 个真实 Provider 双执行、输出 binding 与声明一致性：4/4 通过；其中全路由
  双执行测试单独耗时约 35 秒。
- 179 个 Python 文件通过 AST 解析，全部 Provider/message JSON 通过解析，
  `git diff --check` 通过。

莆田涵江回归案例（2000-10-18，05:10 Asia/Shanghai，119.11150E/25.46096N）：

| 量 | 值 |
|---|---|
| 民用时 | 2000-10-18，05:10:00+08:00 |
| 经度修正 | −213 s（约 −3′33″） |
| 地方平太阳时 | 2000-10-18T05:06:27+08:00 |
| 均时差 | +889 s（约 +14.8′；独立 Meeus oracle +887 s） |
| 总修正 | +676 s |
| 完整真太阳时 | 2000-10-18T05:21:16+08:00（落在 05:20–05:22） |
| 三口径时柱 | 均为 丁卯（修正前后同一时辰） |
| 四柱 | 庚辰 / 丙戌 / 己酉 / 丁卯 |

构造跨时辰边界案例（2000-10-18 06:52，同坐标）：civil 06:52 → 卯（丁卯）；
视太阳时 07:03:16 → 辰（戊辰）；`correction_changes_hour_branch = true`。

## 9. 明确不支持的内容

- 不部署到 Codex/Hermes/liujing；不 push；不重启 Gateway；不碰端口 8642/8645。
- 不修改 Hermes release 源码；不新增运行时依赖；不重写 13 个 Provider 与古籍语料。
- 不用城市关键词表/正则解析地址；地址字符串不等同于坐标。
- 不在 generic core/SKILL.md 写域词或地点（域词属于 manifest/locale）。
- 不在生产代码对“莆田涵江”做特判（仅作测试 fixture）。
- 不恢复 observer/guard/delivery veto；`Accepted.public_copy` 仍是最终结果。
- 不新增后置验签或导致空回复的条件；所有失败 Result 非空。
- 选择视太阳时缺坐标返回 NeedInput，不静默退回民用时。

## 10. 未解决与基线已知失败

- 配置的 research root 存在，但其中缺少声明的 `references/fulltext/**` 文件。
  因而 `test_algorithm_source_dependencies` 的 13 个测试中 10 个通过、3 个失败，
  `test_liuren_fact_adapter.test_month_general_audit_uses_an_independent_fixed_oracle`
  也因缺少 `san-shi/liuren-miben/fulltext.md` 失败。五个 source-bound replay 模块
  共运行 46 个测试，结果为 30 通过、8 失败、8 错误；失败集中在六壬、六爻、
  梅花、禄命、星命的全文 hash/anchor 审计。本次未伪造或复制语料制造绿灯。
- `references/matrices/provider-completeness.yaml` 的生成指纹在接管前的
  `5b6bf54` 就已与当时源码不一致（不是本轮引入）。当前仓库发现 1246 个测试，
  其中 canonical live snapshot 会重跑全 Provider 完整性生成；历史记录约需
  6320 秒。本轮曾运行约 19 分钟并确认仍在正常执行慢速择日审计后停止，没有
  宣称完整仓库全绿。恢复可追溯全文后，应单独重跑并原子更新该快照。
- 运行时守卫（`runtime_python.validate_runtime_tree`）拒绝 venv 中预编译
  `.pyc`；测试需以 `MINGLI_PYTHON` 指向 venv 且 `PYTHONDONTWRITEBYTECODE=1`
  运行，否则子进程类测试报 “unchecked runtime bytecode is forbidden”。这是环境
  约束，非代码缺陷。
