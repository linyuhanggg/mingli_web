# 路由矩阵 (routing-matrix)

> 主 skill `mingli-master` 收到用户问题后的第一步：把自然语言问题映射到「问题类型 → 体系 → reference pack → 所需工具」。
> 本矩阵不写最终结论，只写"加载哪些 pack、需要哪些事实层工具"。

## 0. 路由总规则

1. **先分类，再加载**。先识别问题类型（人生结构 / 短事 / 择时 / 环境 / 旁证），再决定主体系。
2. **能不上多体系就不上**。同一问题原则上只加载 1-2 个体系的 pack；只有用户明确要求合参时才加载第 3 个。
3. **事实层必须先备好**。如果排盘/起卦/起课/历算等工具的输入不齐，**直接进入降级流程**（输出条件性回答），不让 LLM 脑补盘面。
4. **现代流派不参与一线判断**。仅在用户明确点名某派别时，从对应 pack 的 `modern_notes` 引用。
5. **未 ready 的 pack 不得加载**。`status != ready` 的 pack 视为不存在。

## 1. 问题类型识别（路由关键词）

| 问题类型 | 触发关键词（中文） | 主体系 | 默认架构层 |
|---|---|---|---|
| 长期人生结构 | 命运、命盘、八字、四柱、一辈子、人生、性格、整体 | 八字子平 (+ 紫微) | 命盘主线 |
| 大运流年 | 大运、流年、本命年、几岁、何时、运势 | 八字子平 | 命盘主线 |
| 紫微年度主题 | 紫微、宫位、命宫、迁移宫、夫妻宫、官禄、四化 | 紫微斗数 | 命盘主线 |
| 婚恋配对 | 八字合婚、合八字、姻缘、夫妻宫、桃花 | 八字 + 紫微 | 命盘主线 |
| 财运结构 | 财星、正财、偏财、财运、求财方向 | 八字 | 命盘主线 |
| 单事成败 | 这件事能不能成、对方什么态度、谈判、面试、签约、考试 | 大六壬（自然默认；用户明确指定六爻/梅花时遵从指定体系） | 短事决策 |
| 失物寻人 | 找不到、丢了、人在哪、失踪 | 大六壬（自然默认；用户明确指定六爻时用增删卜易/卜筮正宗） | 短事决策 |
| 临场快速判断 | 我现在该不该、马上、今天、这一刻 | 大六壬（自然默认；用户明确点名梅花时用梅花易数） | 短事决策 |
| 复杂人事推演 | 复杂人事、来意、多方关系、阴谋 | 大六壬 | 短事决策 |
| 择时方位策略 | 选时辰、什么方位、哪个方向出门、谈判方位 | 奇门遁甲 | 短事决策 |
| 宏观时势 | 国运、大趋势、几年周期 | 太乙（默认不触发，需用户明确要求）| 短事决策（低频）|
| 择日 | 哪天搬家、开工、入宅、安床、签约、婚嫁、出行 | 择日（协纪辨方+星历考原）| 环境择时旁证 |
| 阳宅风水 | 户型、卧室、厨房、门、灶、装修、楼层 | 风水阳宅 | 环境择时旁证 |
| 理气坐向 | 坐向、玄空、三元、三合、八宅、元运 | 风水理气 | 环境择时旁证 |
| 阴宅形峦 | 祖坟、阴宅、龙脉、砂水、葬法 | 风水形峦 | 环境择时旁证 |
| 相貌旁证 | 看面相、长相、气色、骨相 | 相法 | 环境择时旁证（旁证）|
| 七政四余 / 星命 | 七政、星宗、果老、星平合参 | 星命 | 命盘主线（专门）|

## 2. 体系 → 加载 pack（按优先级）

### 2.1 八字子平

> **2026-06-17 catalog 状态**：八字 7 个 D2 reference pack 均已通过 §L.9，`status: ready`。以 `references/catalog/catalog.json` 为 authoritative loader；本矩阵只写路由策略。

| 子问题 | 优先 pack | 备选 pack |
|---|---|---|
| 综合检索 / 入门索引 / 百科查找 | `bazi/sanming-tonghui/index.md`（ready）| `bazi/yuanhai-ziping/index.md`（ready）|
| 子平法源流 / 术语雏形 / 经验断语回查 | `bazi/yuanhai-ziping/index.md`（ready）| `bazi/sanming-tonghui/index.md`（ready）|
| 月令格局 / 成败救应 / 相神 / 顺逆用 | `bazi/ziping-zhenquan/index.md`（ready）| `bazi/yuanhai-ziping/index.md`（ready）|
| 旺衰 / 气势 / 通关 | `bazi/ditiansui-chanwei/index.md`（ready）| `bazi/sanming-tonghui/index.md`（ready）|
| 调候 | `bazi/qiongtong-baojian/index.md`（ready）| `bazi/ditiansui-chanwei/index.md`（ready，用于寒暖燥湿旁证） |
| 神煞 | `bazi/sanming-tonghui/terms.md` §8 神煞组 | `luming-nayin/wuxing-jingji` |
| 具体章节 / 原文短引 | `bazi/sanming-tonghui/chapter-map.md` + `quote-index.md` | — |
| 判断规则查表 | `bazi/sanming-tonghui/rules.md` | — |
| 可操作流程 | `bazi/sanming-tonghui/procedures.md` | — |
| 覆盖率 / 版本状态 | `bazi/sanming-tonghui/validation.md` | — |
| 早期禄命 / 纳音 | `luming-nayin/li-xuzhong-mingshu` | `luming-nayin/luoluzi-sanming` / `luming-nayin/wuxing-jingji` |

**当前提示**：`sanming-tonghui`、`yuanhai-ziping`、`ziping-zhenquan`、`ditiansui-chanwei`、`qiongtong-baojian`、`shenfeng-tongkao`、`mingli-yueyan` 均为 ready pack，可被主 skill 按需加载。旧单文件 `references/books/bazi/ziping-zhenquan.md` 只作 legacy stub，不作为入口。

#### 何时加载《渊海子平》（ready）

- 问题涉及"子平法是怎么来的"、"徐子平法 vs 李虚中法的差异"等**源流型**问题。
- 需要回查十神、月令、格局雏形等**早期术语**定义。
- 需要比对《三命通会》哪些段落是承袭、哪些是改易。
- 格局 / 调候 / 旺衰精修派 pack 都不可用时，本书是最后一道防线（但不作主结论）。
- **当前 `status: ready`**：本书已返工为文件组，可加载。

**不加载**：

- 用户已经问得很具体（"格局成败" / "调候用神" / "旺衰气势"），应直接路由到精修派 pack。
- 用户要求现代命理结论。

#### 何时加载《子平真诠》（ready）

- 问题为"月令格局成败救应"的**精细判断**。
- 需要取格、看相神、看救应、看顺逆用。
- 用户提问中出现"格局" / "用神"（格局派） / "相神" / "成败" / "救应" / "顺逆" 等关键词。
- **当前 `status: ready`**：加载 `references/books/bazi/ziping-zhenquan/index.md` 文件组；不要加载旧单文件 stub。

**不加载**：

- 用户问旺衰 / 气势 / 通关 / 病药 → 转 `bazi/ditiansui-chanwei/index.md`。
- 用户问调候 → 转 `bazi/qiongtong-baojian/index.md`。
- 用户问神煞 → 转 `bazi/sanming-tonghui/terms.md` §8。
- 引用徐乐吾评注时，必须在输出中单独标注 `[徐评]`。

#### 八字枢纽 pack 的分工简表（catalog 49 ready 后）

| pack | path | status | 核心职责 | 不替代 |
|---|---|---|---|---|
| `bazi/sanming-tonghui` | `references/books/bazi/sanming-tonghui/index.md` | ready | 综合汇编 / 百科查找 / 神煞汇总 | 格局精修、调候、旺衰 |
| `bazi/yuanhai-ziping` | `references/books/bazi/yuanhai-ziping/index.md` | ready | 子平法骨架 / 术语源流 / 经验断语回查 | 格局精修、调候、旺衰 |
| `bazi/ziping-zhenquan` | `references/books/bazi/ziping-zhenquan/index.md` | ready | 格局成败救应精修 | 调候、旺衰、神煞 |
| `bazi/ditiansui-chanwei` | `references/books/bazi/ditiansui-chanwei/index.md` | ready | 旺衰 / 气势 / 通关 / 病药 | 格局取法、纯调候 |
| `bazi/qiongtong-baojian` | `references/books/bazi/qiongtong-baojian/index.md` | ready | 调候 / 寒暖燥湿 | 格局取法、神煞 |
| `bazi/shenfeng-tongkao` | `references/books/bazi/shenfeng-tongkao/index.md` | ready | 张神峰辨伪 / 后出实务对照 | 子平源流入口 |
| `bazi/mingli-yueyan` | `references/books/bazi/mingli-yueyan/index.md` | ready | 清代实务辨证 / 后出对照 | 原典主轴 |

### 2.2 紫微斗数

入口：`ziwei/ziwei-doushu-quanshu` → 必要时补 `ziwei-doushu-quanji` / `ziwei-doushu-jielan`。

### 2.3 六爻 / 梅花

| 子问题 | pack |
|---|---|
| 标准断卦实务 | `divination/bushi-zhengzong` + `divination/zengshan-buyi` |
| 术语溯源 / 纳甲法 | `divination/huo-zhu-lin` |
| 临场快速 / 体用 / 外应 | `divination/meihua-yishu` |

### 2.4 三式

| 子问题 | pack |
|---|---|
| 六壬课式 | `san-shi/liuren-daquan`（需起课工具）|
| 奇门择时 | `san-shi/qimen-dunjia-tongzhi`（需排盘工具，必须声明飞盘/转盘；当前底本为 Taiyi 网页转写 + CTP/NLC 锚点）|
| 太乙宏观 | `san-shi/taiyi-shenshu`（默认 **不加载**，需用户明确触发）|

### 2.5 择日

事实层入口：`references/matrices/selection-fact-layer-profile.md` / `.yaml`。
官方裁判：`selection/xieji-bianfang-shu`，起例背景：`selection/xingli-kaoyuan`。
通书参考：`selection/yuqia-ji`、`selection/donggong-zeri`（仅限大众通书风格问题，且必须声明可能与官方框架冲突）。

所有择日问题先按 `selection-fact-layer-profile.yaml` 识别用事 profile：普通择日、嫁娶、修造动土、安葬、出行上任、开业交易、医疗、民俗对照。缺 profile 要求的事实层字段时，不得选日或排序。

### 2.6 风水

| 子问题 | pack |
|---|---|
| 阴宅 / 形势 | `fengshui/zangshu` → `fengshui/hanlong-jing` → `fengshui/yilong-jing` |
| 阳宅基础 | `fengshui/yangzhai-sanyao` |
| 玄空补充 | `fengshui/shenshi-xuankong-xue` |
| 理气（三元/玄空类）| `fengshui/qingnang-jing` + `fengshui/qingnang-xu` + `fengshui/tianyu-jing` + `fengshui/dutian-baozhao-jing`，注释层 `fengshui/dili-bianzheng` |

### 2.7 相法

入口：`physiognomy/shenxiang-quanbian`。  
实务：`physiognomy/liuzhuang-xiangfa`。  
源流：`physiognomy/mayi-shenxiang`。  
整理：`physiognomy/renxiang-shuijing`。  
**只能作旁证层**，不参与命盘/卜筮硬判断。

## 3. 必备工具映射（事实层）

| 体系 | 必需输入 | 必需工具（外部脚本/服务）|
|---|---|---|
| 八字子平 | 出生年月日时（公历）、出生地（经纬度或时区）、性别、是否真太阳时 | 八字排盘工具（干支、藏干、十神、大运、流年）|
| 紫微斗数 | 同上 | 紫微排盘工具（命盘、宫位、星曜、四化、限运）|
| 七政四余 | 同上 + 现代天文星历 | 星命排盘工具（七政四余位置、宫度）|
| 六爻 | 起卦时间、起卦方式（铜钱/数字/时间起卦）、所问之事 | 起卦工具 + 装卦工具（六亲、六神、世应、动爻）|
| 梅花 | 起卦依据（数字、时间、外应物） | 起卦工具（先天/后天起卦法均可）|
| 大六壬 | 占课时间（年月日时）、月将、用神类别 | 起课工具（四课三传、贵神、天地盘）|
| 奇门 | 占用时间、用事方向、流派（飞盘/转盘）| 排盘工具（九宫、八门、九星、八神、奇仪）|
| 太乙 | 占用时间、用事范围 | 排盘工具（太乙式）|
| 择日 | 用事类型、当事人八字（嫁娶等可选但影响 couple-specific 判断）、可选日期范围、地点/时区；动土/安葬/出行方位按 profile 必需 | 历算工具（干支、神煞、宜忌、黄黑道、值日）+ `selection-fact-layer-profile.yaml` 的用事字段校验 |
| 风水形峦 | 现场照片 / 地形图 / 卫星图 | 不需要 LLM 计算；需观察输入 |
| 风水阳宅 | 户型图、坐向、楼层、建筑年代 | 罗盘/坐向记录工具 + 元运表（如玄空必需）|
| 风水理气 | 同阳宅 + 流派 + 元运 | 玄空/三元/三合/八宅排盘工具 |
| 相法 | 正面照片 / 侧面照片 / 描述 | 不需要计算；只做旁证 |

**强约束**：上表所列「必需输入」缺失时，主 skill 必须降级输出；不允许 LLM 自行编盘。

## 4. 跨体系合参规则

| 用户场景 | 默认主体系 | 允许补充 |
|---|---|---|
| 婚恋长期 | 八字 | 紫微（夫妻宫）|
| 婚恋一时 | 六爻 | — |
| 财运长期 | 八字 | 紫微（财帛宫）|
| 单笔交易 | 六爻 / 奇门 | — |
| 搬家 | 择日 | 风水阳宅（坐向影响）|
| 装修 | 风水阳宅 | 择日（动工日）|
| 长期决策（换工作）| 八字（大运流年） | 六爻（节点决策）|

跨体系合参时必须声明各自结论的适用边界，不得糅合。

## 5. 停止编造场景

| 场景 | 处理 |
|---|---|
| 用户问"何时世界末日"等宏观异常问题 | 不因题材拒绝；若用户明确要太乙/宏观时势，则转太乙；否则要求限定问题、时间范围和体系 |
| 用户提供模糊出生时间（无时辰）| 八字降级（无时柱）；紫微无法排盘，必须明确告知 |
| 用户没有起卦时间 | 停止编造卦/课/局；要求补起卦时间或提供已起好的盘 |
| 用户问求医吃药 | 不因题材拒绝；只按命理文本直说病象/疾厄倾向，不伪装成现代诊断或处方 |
| 用户问股票/赌博点位 | 不因题材拒绝；必须有盘/课/局事实层，按传统体系直断倾向，不编造盘面 |
| 用户问他人隐私（开盘别人）| 可按用户给出的事实层直断；不要伪造缺失资料 |
