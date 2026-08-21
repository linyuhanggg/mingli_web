# SS-B3 六壬神煞与天将边界精修矩阵

generated_at: 2026-07-05  
matrix_version: v0.1  
batch_id: SS-B3  
source_status: distilled_from_ready_liuren_packs

本文件是 `shensha-distillation-backlog.md` 的第三批落地产物。它不替代《大六壬大全》《六壬指南》《大六壬秘本》的单书 reference pack，也不把白虎、天乙、青龙、朱雀、玄武等名目变成独立断事器；它只回答：六壬课内神煞、十二天将、类神应该怎样进入事实层，怎样防止串到八字、紫微、择日或风水里。

## 来源状态

SS-B3 只使用已经在本地成 pack 的六壬来源：

| Pack | 角色 | 当前口径 |
|---|---|---|
| `san-shi/daliuren-daquan` | 主权威层 | 四库本/维基文库整理源，D2 source evidence layer ready；负责起例、九宗法、神将释、课体、毕法赋、课经集导航 |
| `san-shi/liuren-zhiyin` | 入门与神煞指南层 | CTP 五章重建，含卷四“大六壬神煞指南”；适合解释神煞不可孤用 |
| `san-shi/liuren-miben` | 秘本类象补充层 | CTP 抄录本 17 卷 ready；适合补月将、天将、类象、五要权衡、疾病等历史占法 caveat |

## 上下游依赖

1. 《大六壬大全》优先回答“六壬主干课法、课体、十二天将、类神、毕法/课经如何定位”。
2. 《六壬指南》优先回答“入门框架、心印/指掌纲领、卷四神煞为什么不能孤用”。
3. 《大六壬秘本》只补类象、秘本歌诀和专项占法，不压过《大六壬大全》。
4. 涉及具体课、某事吉凶、神煞是否发动、白虎/天乙是否主事时，必须先有本地 `mingli-master.liuren_fact_adapter` v2 的完整事实层，并通过 validator。

## 必要事实层

六壬神煞不是自由文本层，而是 `liuren_plate_fact_layer` 字段。最少需要：

- `calendar_normalization`
- 占事原文、事项类别、起课口径
- 日辰/日干支、占时
- 月将
- 天地盘
- 四课三传
- 十二天将
- 类神匹配
- 空亡、五行生克、刑冲破害、旺相休囚
- 课内神煞命中与 `source_trace`

缺这些字段时，只能停在缺项说明，不能断事。

## 使用总则

1. 六壬白虎、青龙、朱雀、玄武、天后、太常、太阴等首先是天将/类神，不等于择日黄黑道名目。
2. 六壬天乙/贵人不等于八字天乙贵人；昼夜贵人口径冲突需保留版本说明。
3. 伏吟/反吟在六壬中是课体/起例结果，不等于八字流年同柱重复。
4. 单个神煞、单个天将、单个类神都不能独立定吉凶。
5. 医疗、官讼、丧病、灾祸等古代占辞只能说“传统文本如何论”，不能说成现实事实。

## 条目精修

| Entry | 六壬用途 | 一线来源 | 必要事实层 | 禁止外推 |
|---|---|---|---|---|
| `shensha-tianyi-guiren` 天乙贵人 | 十二天将核心/贵人取用 | `daliuren-daquan`, `liuren-zhiyin` | 昼夜贵人、天将布列、四课三传 | 不等于八字天乙 |
| `shensha-tiande-yuede` 天德/月德 | 课内吉神支持 | `daliuren-daquan`, `liuren-zhiyin` | 日辰、课传、旺衰 | 不等于择日起例层 |
| `shensha-yima-tianma` 驿马/天马 | 动象、行人、出行类象 | `daliuren-daquan` | 月将、三传、类神 | 不等于八字/紫微/择日天马 |
| `shensha-xianchi-taohua` 咸池/桃花 | 情欲/关系类象 | `daliuren-daquan`, `liuren-miben` | 课传与类神 | 不等于命盘桃花 |
| `shensha-hongluan-tianxi` 红鸾/天喜 | 喜庆/婚姻支持象 | `daliuren-daquan` | 课传与占事主题 | 不等于紫微红鸾天喜 |
| `shensha-jiangxing-huagai` 将星/华盖 | 权柄/遮蔽类象 | `daliuren-daquan` | 课式组合 | 不作命局性格定论 |
| `shensha-jiesha-wangshen-zaisha` 劫煞/亡神/灾煞 | 阻隔、损失、凶象支持 | `daliuren-daquan` | 刑冲克害、旺衰、空亡 | 不单独断灾 |
| `shensha-guchen-guasu` 孤辰/寡宿 | 离合/孤隔辅助象 | `daliuren-daquan` | 事项类别与课式 | 不进入八字婚姻 inventory |
| `shensha-tianyi-medical` 天医 | 医事/救解辅助象 | `daliuren-daquan` | 医事 caveat、课式组合 | 不等于八宅天乙巨门 |
| `shensha-taisui` 太岁/岁君/岁破 | 岁神/时间背景 | `daliuren-daquan` | 年月日时背景 | 不等于紫微太岁或择日太岁方 |
| `shensha-baihu` 白虎 | 十二天将/疾病丧服等类神 | `daliuren-daquan`, `liuren-zhiyin`, `liuren-miben` | 天将、三传、刑克、旺衰 | 不等于择日白虎；不可单断血光 |
| `shensha-guanfu-bingfu` 官符/病符 | 官讼/疾病辅助象 | `daliuren-daquan` | 课传组合与现实 caveat | 不作现代法律/医疗事实判断 |
| `shensha-sangmen-diaoke` 丧门/吊客 | 丧病/阻滞象 | `daliuren-daquan`, `liuren-miben` | 完整课式 | 不单项断丧病寿夭 |
| `shensha-tianxing` 天刑 | 刑伤象 | `daliuren-daquan` | 刑冲克害与天将 | 不等于紫微/星命/择日天刑 |
| `shensha-yuepo-yueyan` 月破/月厌/月害 | 月家关系与阻隔 | `daliuren-daquan` | 月将/月神、课传 | 不用来直接断个人运势 |
| `shensha-side-fei-lijue` 四废/四离/四绝 | 节令背景辅助 | `daliuren-daquan` | 占时节令、课式 | 不等于择日四离四绝 |
| `shensha-jinshen-qisha` 金神七煞 | 金杀/阻隔类辅助 | `daliuren-daquan` | source trace 与课式 | 不等于八字金神格或择日金神七煞 |
| `shensha-yuekong-mucang-jieshen` 月空/母仓/解神 | 空、藏、解类辅助 | `daliuren-daquan` | 月将、课传、神将 | 不迁移为八字贵人或择日吉神 |
| `shensha-twelve-generals` 十二天将 | 六壬核心事实层 | `daliuren-daquan`, `liuren-zhiyin`, `liuren-miben` | 天将布列、四课三传 | 不等于择日十二神；不能单独定吉凶 |
| `shensha-fuyin-fanyin` 伏吟/反吟 | 六壬课体/起例结果 | `daliuren-daquan`, `liuren-zhiyin` | 工具识别课体 | 不等于八字伏吟反吟 |

## 回答层融入规则

- 神煞源流问题：可以说明六壬语义边界，但不做现实断事。
- 具体六壬问事：先运行 `scripts/liuren_fact_adapter.py` 并通过事实层校验，再按《大六壬大全》为主、《六壬指南》《大六壬秘本》为辅解释。
- 缺事实层：停止解释，只列缺少的 adapter 输出。
- 串台问题：明确说“这个名目在六壬里只属于课式/天将/类神，不并入八字、紫微或择日”。

## 后续神煞书籍队列

用户后续要继续看“神煞相关书籍”时，先按 `shensha-distillation-backlog.md` 的 SS-B10 做书目核验：已 ready 的《三命通会》《五行精纪》《星历考原》《协纪辨方书》《大六壬大全》《果天经》等可以继续二次精修；《星平会海/命海全编》《七政全书大成》《阳宅爱众篇》一类未完成 OCR/manifest 的来源只能做 acquisition，不进入规则层。
