# SS-B2 官方择日神煞精修矩阵

generated_at: 2026-07-05
matrix_version: v0.1
batch_id: SS-B2
source_status: distilled_from_ready_selection_packs_and_qoder_manifests

本文件是 `shensha-distillation-backlog.md` 的第二批落地产物。它不替代单书 reference pack，也不把黄道、建除、天德、太岁等单项神煞升级为独立择日器；它只回答：官方择日神煞在 `mingli-master` 里应怎样分层、怎样进入事实层、怎样防止“只凭一个好神/凶神就选日子”。

## 来源状态

SS-B2 只使用已经有完整本地文本和 D2 pack 的选择类来源：

| Pack | 角色 | 当前口径 |
|---|---|---|
| `selection/xingli-kaoyuan` | 官方起例层 | Qoder manifest 为 normalized ready；Codex pack validation 为 D2 ready；适合查年神/月神/日时神、黄黑道、二十八宿、四离四绝等起例 |
| `selection/xieji-bianfang-shu` | 官方裁判层 | Qoder manifest 为 normalized ready；Codex pack validation 为 D2 ready；适合做用事宜忌、辨讹、冲突裁判 |
| `selection/yuqia-ji` | 民俗通书对照层 | ready，但版本众多；只能作 folk comparison |
| `selection/donggong-zeri` | 民间月日表对照层 | ready，但异本风险仍在；只能作 folk comparison |

## 上下游依赖

1. `星历考原` 优先回答“此神煞如何起例、属于年神/月神/日神/时神还是用事项”。
2. `协纪辨方书` 优先回答“该用事是否宜忌、民间通书是否有讹、冲突时如何裁判”。
3. `玉匣记`、`董公择日` 只能回答“民俗通书如何说”，不得压过官方层。
4. 涉及具体日期、时辰、方位、候选排序时，必须先有 `mingli-master.selection.v1` 的完整确定性事实层。

## 使用总则

1. 择日中神煞是 `selection_fact_layer` 字段，不是自由解释层。
2. 不得只凭黄道、黑道、建除、天德、月德、天医、驿马、太岁、白虎、金神七煞、大将军等单项因子选日或判日。
3. 至少同时看：历法标准化、候选日逐日记录、建除、黄黑道、二十八宿、年/月/日/时神煞、用事宜忌、冲犯/避忌、方位避忌（如相关）、source_trace。
4. 用事不同，权重不同：嫁娶、动土、安葬、出行、开业、医事各自读取 `selection-fact-layer-profile.yaml` 的 event profile。
5. 医事、丧葬等敏感用事只作传统文化参考，不替代现实医疗、法律、工程、安全安排。

## 条目精修

| Entry | 择日用途 | 一线来源 | 必要事实层 | 禁止外推 |
|---|---|---|---|---|
| `shensha-tiande-yuede` 天德/月德 | 通用吉神、嫁娶/起造等加分 | `xingli`, `xieji` | 月神、日神、用事 profile | 不单凭天月德定吉日 |
| `shensha-yima-tianma` 驿马/天马 | 出行/上任择日字段 | `xieji`, `xingli` | 出行 profile、黄道吉时、往亡/归忌 | 不等于八字/紫微/星命天马 |
| `shensha-jiesha-wangshen-zaisha` 劫煞/亡神/灾煞 | 年/月家凶煞与方位避忌 | `xieji`, `xingli` | 年神/月神、方向或坐山 | 不移植为个人命局断灾 |
| `shensha-guchen-guasu` 孤辰/寡宿 | 嫁娶忌项 | `xieji` | 婚嫁 profile、双方四柱（若做 final selection） | 不单独断婚姻坏 |
| `shensha-shie-dabai` 十恶大败 | 通用凶日/婚嫁商事医事避忌 | `xieji`, `xingli` | 日神、用事宜忌、冲突裁判 | 不等于命盘十恶大败 |
| `shensha-yuanchen-dahao` 元辰/大耗/小耗 | 月凶/耗损类参考 | `xingli`, `xieji` | 月神、日神、用事 profile | 不要机械套成财务损失 |
| `shensha-tianyi-medical` 天医 | 医事/求嗣祈福相关吉神 | `xingli`, `xieji` | 医事 profile、医疗边界 | 不等于八宅天乙巨门或健康保证 |
| `shensha-taisui` 太岁/岁破 | 年神、方位、岁破避忌 | `xingli`, `xieji` | 年神方位、方向/坐山 | 不等于紫微流年太岁或六壬岁君 |
| `shensha-baihu` 白虎 | 年神/黑道凶神 | `xingli`, `xieji` | 年神、黄黑道、用事宜忌 | 不等于六壬白虎天将 |
| `shensha-guanfu-bingfu` 官符/病符 | 年/月/日神避忌 | `xingli`, `xieji` | 年月日神、用事 profile | 不作现代法律/医疗事实判断 |
| `shensha-tianxing` 天刑 | 黑道凶神/刑伤象 | `xingli`, `xieji` | 黄黑道与日时神 | 不等于紫微天刑、星命天刑 |
| `shensha-huangdao-heidao` 黄道/黑道 | 日时吉凶基础字段 | `xingli`, `xieji` | 日黄黑道、十二时辰黄黑道 | 不能单独选日 |
| `shensha-jianchu` 建除十二神 | 用事基础字段 | `xieji`, `xingli` | 月建、逐日建除、用事宜忌 | 不用于命盘断人生 |
| `shensha-yuepo-yueyan` 月破/月厌/月害 | 月家避忌 | `xingli`, `xieji` | 月神、用事 profile | 不从月破日直接断个人运 |
| `shensha-side-fei-lijue` 四废/四离/四绝 | 节气交替避忌 | `xingli`, `xieji` | 节气上下文、用事 profile | 不脱离具体用事泛称百事凶 |
| `shensha-jinshen-qisha` 金神七煞 | 动土/修造方位避忌 | `xingli`, `xieji` | 年干、方位、动土 profile | 不等于八字金神格 |
| `shensha-dajiangjun` 大将军 | 年家方位避忌 | `xingli`, `xieji` | 年神方位、坐山/方向 | 不与八字将星混用 |
| `shensha-yuekong-mucang-jieshen` 月空/母仓/解神 | 月吉神、解厄/孳息类参考 | `xingli`, `xieji` | 月神、用事 profile | 不迁移为八字贵人 |
| `shensha-twelve-generals` 青龙/朱雀/六合/勾陈/玄武/太常/太阴/天后 | 择日黄黑道/日时神名物 | `xingli`, `xieji` | 黄黑道与时神 | 不等于六壬十二天将 |

## Event Profile Crosswalk

| 用事 | 必读 profile | 一线规则锚 | 额外要求 |
|---|---|---|---|
| 普通择日 | `generic_selection` | `XP-01`, `XR-08`, `KP-04`, `KR-14`, `KR-15`, `KR-17` | 不得只凭黄道/建除 |
| 嫁娶/领证 | `marriage` | `XP-02`, `XR-05`, `KP-06`, `KR-18` | couple-specific final selection 需双方四柱 |
| 起造/动土/装修 | `construction_renovation` | `XP-03`, `XR-02`, `XR-06`, `KP-02`, `KR-08~KR-10`, `KR-20` | 坐山/施工方向为 hard required |
| 安葬/启攒 | `burial_funeral` | `XP-04`, `XR-07`, `KP-06`, `KR-19` | 葬向/坐山影响方位裁判 |
| 出行/上任 | `travel_office` | `XP-05`, `XP-06`, `XR-09`, `KP-05` | 必须含驿马/天马、往亡/归忌、四离四绝/杨公忌、黄道吉时 |
| 开业/交易/纳财 | `business_opening_transaction` | `XP-01`, `XR-08`, `XR-14`, `KP-06`, `KR-17` | 若涉及门向/方位，补方位避忌 |
| 求医/服药/探病 | `medical` | `XP-01`, `XR-16`, `KP-06` | 必须说明不替代医疗判断 |
| 通书冲突/民俗禁忌 | `folk_comparison` | `XP-07`, `XR-17`, `JP-*`, `DP-*` | 民俗书只作 comparison_only |

## 后续神煞书籍队列

后续要继续看神煞相关书籍时，按“可用 pack 二次精修优先，未校勘书只做 acquisition”处理：

| Priority | 书籍/pack | 当前状态 | 后续用途 |
|---|---|---|---|
| S0 | `bazi/sanming-tonghui`、`luming-nayin/wuxing-jingji`、`luming-nayin/li-xuzhong-mingshu` | ready | 八字/禄命神煞源流逐条精修 |
| S0 | `selection/xingli-kaoyuan`、`selection/xieji-bianfang-shu` | ready | 官方择日神煞起例与裁判继续补 quote-index crosswalk |
| S1 | `san-shi/daliuren-daquan`、`san-shi/liuren-zhiyin`、`san-shi/liuren-miben` | ready | 六壬课内神煞与十二天将不可外推测试 |
| S1 | `ziwei/ziwei-doushu-quanshu`、`ziwei/taiwei-fu`、`xingming/guotian-jing` | ready / 版本风险 | 紫微/星命同名神煞消歧 |
| S2 | `xingming/minghai-quanbian`《星平会海/命海全编》 | image_only | OCR 校勘后再抽“诸吉神/诸煞星/小儿关煞” |
| S2 | `xingming/qizheng-quanshu-dacheng` | image_only | 表格 OCR 后补七政四余事实层 |
| S3 | 《阳宅爱众篇》、墓葬神煞资料 | source lead only | 先做书目核验和完整文本获取 |

## 回答层融入规则

- 神煞源流问题：可引用 `xingli-kaoyuan` 起例，但只回答源流，不给日期判断。
- 具体择日问题：必须先过 `selection-fact-layer-profile`，再用 `xieji-bianfang-shu` 作官方裁判。
- 民俗通书问题：可以比较 `yuqia-ji` / `donggong-zeri`，但必须标明民俗对照，不能覆盖官方层。
- 缺事实层：停止解释，只列缺少的 adapter 输出；不得边说缺工具边推荐日期。
