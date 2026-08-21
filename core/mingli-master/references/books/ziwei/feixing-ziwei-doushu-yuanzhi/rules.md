# 華山陳希夷先生飛星紫微斗數原旨 — Rules

> 规则均来自 reviewed fulltext，可追溯到页码。它们是本书的观测/旁证规则，不是基础排盘规则。
> 涉及紫微盘面的任何规则都必须先有 `tool.ziwei.bindisk` 或等价事实层输出。

## FZ-R01 Source Identity Gate

- **source_chapter**: page-002 to page-005
- **rule**: 调用本 pack 时须称其为《華山陳希夷先生飛星紫微斗數原旨 / 斗數觀測錄》民国观测注释层，不得把它冒称为《斗数管见》，也不得当作古法紫微一线原典。
- **applicable_to**: pack routing, citation, provenance checks
- **caveats**: 作者题署和正文书名存在层次差异；题陈希夷不等于可以视为陈希夷亲撰。
- **verified**: true

## FZ-R02 Observation Method Is A Cross-Check, Not A Replacement

- **source_chapter**: page-005
- **rule**: 本书“观测之道”把天气变化、人事起伏、富贵剥复视为可观察对象；用于分析时只能作为对既有盘面事实的旁证和解释框架，不能替代排盘、历法、事实层。
- **applicable_to**: current-event readings, environment/person observation
- **caveats**: 不可把“观测”扩张成无盘无据的自由断语。
- **verified**: true

## FZ-R03 Ziwei Must Start From Complete Chart Facts

- **source_chapter**: page-030
- **rule**: 本书称斗数“先布出身命垣”，说明一切占课和观察须先有身命/盘面定位；没有命身宫、十二宫、星曜、限运等事实，不应使用本 pack 下判断。
- **applicable_to**: all ziwei readings
- **adapter_requirements**: `calendar_normalization`, `tool.ziwei.bindisk` equivalent output
- **verified**: true

## FZ-R04 Yin/Yang House And Physiognomy Are Mutual Evidence

- **source_chapter**: page-008 to page-010
- **rule**: 本书将阴宅、阳宅、相理、命理互相参看；面相高低、痣、骨格等可作为地理/阴阳宅状态的观察线索，地理状态也可作为命盘旁证。
- **applicable_to**: fengshui cross-check, physiognomy cross-check
- **caveats**: 只能作为传统相地观测法；必须有实际方位、地形、住宅、相貌观察，不能凭想象推地。
- **verified**: true

## FZ-R05 Directional Locality Response

- **source_chapter**: page-018 to page-019
- **rule**: 流年吉凶星煞所到方位，书中常以阴阳宅、四邻住户、地主、土地变动、树木墙垣、塋葬起灵等事件相应；使用时应先确认命盘方位与实际空间方位。
- **applicable_to**: house/neighborhood observation, annual-locality check
- **caveats**: 不是“某方一定发生某事”的铁律；应输出为可核验的方位假设。
- **verified**: true

## FZ-R06 Malefic Direction Indicators

- **source_chapter**: page-019
- **rule**: 本书把白虎、喪門、弔客、歲破、大耗、流羊、陀罗等在方位上的作用归为伤病、破败、拆毁、急变、起土、迁动等传统凶象类别。
- **applicable_to**: direction/event cross-check
- **caveats**: 现代输出必须改写为“传统认为此方需注意安全、纠纷、破耗、动土/修缮”之类，不铁口断死病。
- **verified**: true

## FZ-R07 Red-Luan-Da-Hao Pattern

- **source_chapter**: page-012, page-037 to page-038, page-895 to page-902
- **rule**: 红鸾、天喜、咸池与大耗同宫或限运相逢，书中多以婚恋、喜庆、家眷移动、关系变化、消费支出、妻女病耗等案例验证。
- **applicable_to**: relationship and household movement readings
- **caveats**: 不应每次运势都机械说“财务/回款”；只有盘面确有红鸾/天喜/咸池/大耗等组合并且问题相关时才用。
- **verified**: true

## FZ-R08 Ju-Men And Tian-Xing Legal/Public-Gate Symbolism

- **source_chapter**: page-016 to page-018, page-920
- **rule**: 巨门主口舌是非、公门黑暗、法院警署看守律师等象；天刑主刑法、司法、掌权施令、戒师将帅等象。二者在官禄、命身、流年等位置可作为法律/纠纷/公门事务旁证。
- **applicable_to**: legal dispute, public office, conflict readings
- **caveats**: 只能提示传统象义和风险，不能替代法律判断，也不能无盘事实断“必有官非”。
- **verified**: true

## FZ-R09 Twelve-Palace Borrowing For Relatives

- **source_chapter**: page-025 to page-030
- **rule**: 本书用宫位假借看岳父母、子女配偶、叔伯、外孙等关系，例如岳父母可借兄弟/子女等宫位，外孙可由迁移宫与命垣对照并用三合判定。
- **applicable_to**: extended-family questions
- **caveats**: 必须明确标注为“本书假借法”，不要混作所有紫微流派通则。
- **verified**: true

## FZ-R10 One-Matter-One-Chart For Event Divination

- **source_chapter**: page-030 to page-031
- **rule**: 本书尝试把斗数用于占课：一物一事一地一人均有身命，推演一课即该事整体局势，不必另分主客用神。
- **applicable_to**: experimental ziwei divination, object/event questions
- **caveats**: 属本书创新/实验法；优先级低于六爻、梅花、六壬、奇门等本门占事体系。
- **verified**: true

## FZ-R11 Weather Observation Is A Traditional Analogy

- **source_chapter**: page-005, page-034, page-845 to page-852
- **rule**: 本书把天气冷暖风雨阴晴与人事运限类比，且有按日时盘占风雨的案例；可作传统观测样例。
- **applicable_to**: historical method explanation
- **caveats**: 不可替代现代天气预报，也不应在日常命理问答里擅自预测天气。
- **verified**: true

## FZ-R12 Temple/Village Qi Is A Fengshui-Shensha Lead

- **source_chapter**: page-854
- **rule**: 本书观察村镇气脉时先看村头庙宇，庙宇坍塌/重新等被作为村中人事兴衰的旁证，并提到《阳宅爱众篇》诸庙宇神煞表。
- **applicable_to**: later shensha/fengshui corpus acquisition
- **caveats**: 这是一条“神煞书籍线索”，不是已完成的庙宇神煞规则库；后续须找《阳宅爱众篇》或相关神煞表完整底本。
- **verified**: true

## FZ-R13 Delivery Must Separate Evidence And Saying

- **source_chapter**: page-010 to page-011, page-893
- **rule**: 本书强调谈命需因人、语言、心理、社会语境而施说，并区分不敢说、不能说、不可说、不便说、不得不说等情形。用于 `mingli-master` 时应把原书说法、事实依据、现代解释和不确定性分开。
- **applicable_to**: answer style, sensitive cases
- **caveats**: 这不是内容禁忌；是要求表达不混淆证据层级。
- **verified**: true

## FZ-R14 Late Case Material Must Not Override Primary Ziwei

- **source_chapter**: page-997
- **rule**: 书末自称十二宫活用假借等法为“新发明”且由考验得来；因此这些规则须作为本书经验法，不得反向改写《紫微斗数全书》《太微赋》的基础义理。
- **applicable_to**: conflict resolution
- **caveats**: 若与早期原典冲突，以早期 pack 先定本义，再把本书作为案例旁证。
- **verified**: true
