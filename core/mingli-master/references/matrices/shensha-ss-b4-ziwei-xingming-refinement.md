# SS-B4 紫微 / 星命同名神煞消歧矩阵

generated_at: 2026-07-05  
matrix_version: v0.1  
batch_id: SS-B4  
source_status: distilled_from_ready_ziwei_xingming_packs

本文件是 `shensha-distillation-backlog.md` 的第四批落地产物。它不替代《紫微斗数全书》《太微赋》《飞星紫微斗数原旨/斗数观测录》《果天经/果老星宗》的单书 reference pack；它只回答：紫微、星命里和八字/择日/六壬同名的神煞或星曜，怎样依赖事实层，怎样防止串台。

## 来源状态

| Pack | 角色 | 当前口径 |
|---|---|---|
| `ziwei/ziwei-doushu-quanshu` | 紫微主权威层 | 当前本地 Wikisource 三卷 scope；用于星曜、辅煞、四化、十二宫、大限小限流年等主线 |
| `ziwei/taiwei-fu` | 早期赋文语义层 | 可作天马、羊陀、空亡、桃花、白虎等赋文语义旁证；不覆盖主权威层 |
| `ziwei/feixing-ziwei-doushu-yuanzhi` | 民国观测注释层 | 只在完整紫微盘事实层之后使用，不能作为古典主线 |
| `xingming/guotian-jing` | 星命主权威层 | ready，但有托名/版本风险；用于七政四余盘内天刑、天马地驿、阳刃、咸池、空亡、劫亡、三刑六害等 |
| `xingming/xingming-suyuan`, `xingming/xingxue-dacheng` | 星命支撑层 | 本批只作源流与 adapter 边界旁证，未单独提升为 SS-B4 主来源 |

`xingming/minghai-quanbian`、`xingming/qizheng-quanshu-dacheng`、`xingming/qizheng-siyu-tianjing` 仍是 acquisition/OCR/书名考证状态，不进入解释规则。

## 必要事实层

紫微神煞或辅星必须先有 `tool.ziwei.bindisk` 或等价事实层：

- 历法标准化、农历日期、闰月状态、性别/顺逆口径
- 十二宫、命宫、身宫
- 主星、辅星、煞曜、杂曜
- 四化、庙旺陷、会照夹拱
- 大限、小限、流年、流曜/流煞
- `source_trace`

星命神煞必须先有 `tool.xingming.bindisk` 或等价事实层：

- 历法标准化、出生/事件时间地点时区
- ephemeris 来源与版本
- 十一曜、罗喉、计都、紫气、月孛等天文位置
- 十二宫、命宫、命度、度主、宫主、身主
- 神煞位置、顺逆/迟留等运动状态
- `source_trace`

缺这些字段时，只能说明缺项，不能断事。

## 使用总则

1. 紫微的擎羊、陀罗、禄存、化禄、天马、红鸾、天喜、天刑、白虎、大耗等首先是星曜/流曜/宫位组合字段，不等于八字神煞。
2. 星命的阳刃、天马地驿、咸池、空亡、劫亡、三刑六害等首先是七政四余天文盘字段，不等于八字或择日起例。
3. `feixing-ziwei-doushu-yuanzhi` 只作民国观测注释层；不能因为它有案例语气，就让每次运势都落成“财务、回款、收尾”的模板。
4. 单个星曜、单个神煞、单个流煞都不能独立定吉凶；必须合看宫位、四化、会照、限运或星命天文盘结构。
5. 古籍中的伤灾、官非、疾病、丧吊等敏感凶辞只能作为传统文本指向，不能说成现实事实。

## 条目精修

| Entry | 紫微/星命用途 | 一线来源 | 禁止外推 |
|---|---|---|---|
| `shensha-wenchang` 文昌 | 紫微文昌星、文学/文书辅助 | `ziwei-doushu-quanshu`, `taiwei-fu` | 不等于八字文昌贵人 |
| `shensha-jinyu` 金舆 | 紫微赋文格局/语义 | `taiwei-fu`, `ziwei-doushu-quanshu` | 不等于八字金舆贵人 |
| `shensha-lushen-lucun` 禄/禄神/禄存/化禄 | 紫微禄存/化禄；星命禄神/化禄 | `ziwei-doushu-quanshu`, `guotian-jing` | 不等于八字干禄或禄命干禄 |
| `shensha-yima-tianma` 驿马/天马 | 紫微天马；星命天马地驿 | `ziwei-doushu-quanshu`, `guotian-jing` | 不等于八字驿马、择日出行马星、六壬动象 |
| `shensha-xianchi-taohua` 咸池/桃花 | 紫微桃花相关星曜；星命咸池 | `ziwei-doushu-quanshu`, `feixing-ziwei-doushu-yuanzhi`, `guotian-jing` | 不等于八字桃花单项 |
| `shensha-hongluan-tianxi` 红鸾/天喜 | 紫微喜庆/婚恋辅助星 | `feixing-ziwei-doushu-yuanzhi`, `ziwei-doushu-quanshu` | 不写成每次运势固定套话 |
| `shensha-yangren` 羊刃/阳刃 | 紫微擎羊/流羊；星命阳刃 | `ziwei-doushu-quanshu`, `taiwei-fu`, `guotian-jing` | 不等于八字羊刃格 |
| `shensha-kongwang` 空亡 | 紫微空亡/天空地劫语义；星命空亡 | `taiwei-fu`, `ziwei-doushu-quanshu`, `guotian-jing` | 不等于八字旬空 |
| `shensha-jiangxing-huagai` 将星/华盖 | 紫微星曜/杂曜辅助 | `ziwei-doushu-quanshu`, `taiwei-fu` | 不用八字三合取法反推紫微盘 |
| `shensha-jiesha-wangshen-zaisha` 劫煞/亡神/灾煞 | 星命损耗阻隔信号 | `guotian-jing` | 不移植为八字/择日/六壬凶断 |
| `shensha-yuanchen-dahao` 元辰/大耗/小耗 | 紫微大耗小耗/耗星 | `feixing-ziwei-doushu-yuanzhi`, `ziwei-doushu-quanshu` | 不等于八字元辰 |
| `shensha-taisui` 太岁/岁君/岁破 | 紫微流年太岁 | `ziwei-doushu-quanshu`, `taiwei-fu` | 不等于择日太岁方或六壬岁君 |
| `shensha-baihu` 白虎 | 紫微流煞/赋文凶象 | `taiwei-fu`, `feixing-ziwei-doushu-yuanzhi` | 不等于六壬白虎天将或择日白虎 |
| `shensha-guanfu-bingfu` 官符/病符 | 紫微流年小煞 | `taiwei-fu`, `ziwei-doushu-quanshu` | 不作现代法律/医疗事实判断 |
| `shensha-sangmen-diaoke` 丧门/吊客 | 紫微流年小煞 | `ziwei-doushu-quanshu`, `taiwei-fu` | 不单项断丧病 |
| `shensha-tianxing` 天刑 | 紫微天刑星；星命天刑 | `ziwei-doushu-quanshu`, `guotian-jing` | 不等于择日黑道天刑或六壬天刑 |
| `shensha-sanxing-liuhai` 三刑/六害 | 星命盘内关系信号 | `guotian-jing` | 不等于八字地支刑害算法 |

## 回答层融入规则

- 神煞源流问题：可以解释紫微/星命的名目边界，不做现实断事。
- 紫微具体问题：先过 `tool.ziwei.bindisk`，再以《紫微斗数全书》为主，《太微赋》为赋文旁证，民国飞星材料只作注释。
- 星命具体问题：先过 `tool.xingming.bindisk` 和现代 ephemeris，再以《果天经/果老星宗》为主；旧表格不得当现代星历。
- 串台问题：直接说明“同名不等于同算法”，并指出所需事实层。

## 后续神煞书籍队列

继续找“神煞相关书籍”时走 `shensha-distillation-backlog.md` 的 SS-B10：先做书目、底本、馆藏、manifest、OCR 状态核验。已 ready 的《三命通会》《五行精纪》《星历考原》《协纪辨方书》《大六壬大全》《果天经》等可以二次精修；《星平会海/命海全编》《七政全书大成》《阳宅爱众篇》一类未完成 OCR/manifest 的来源只能 acquisition，不进入规则层。
