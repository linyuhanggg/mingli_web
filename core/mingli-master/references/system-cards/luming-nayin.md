# 早期禄命 / 纳音 (luming-nayin)

## Deterministic provider

- Provider: `mingli-master.luming-nayin.v1`; mode: `calculation`.
- Inputs: birth datetime/timezone/location through the shared calendar core, or four validated sexagenary pillars.
- Facts: all sixty Jiazi Nayin rows; Li Xuzhong stem-Lu/branch-Ming/Nayin-Shen profile; Luoluzi stem/branch/hidden-human profile; explicitly selected Taiyuan convention; source-named Lu/Ma/Gui relations.
- Source roles: 《李虚中命书》《珞琭子三命消息赋》《五行精纪》 constrain calculation; 《兰台妙选》 is interpretation-only.
- Boundary: these facts remain an independent early-Luming lineage. They are not translated into modern Bazi Ten Gods and do not produce a verdict without current evidence adjudication.

## Packs

| pack | title | best for | do not use for | caveat |
|---|---|---|---|---|
| `luming-nayin/lantai-miaoxuan` | 兰台妙选 | 纳音取象格局的系统样本; 三元（天元/地元/人元）与四柱、胎元、禄马贵人并看的早期禄命法; 与《李虚中命书》《玉照神应真经》《五行精纪》对读，辨析子平法之前的格局语言 | 现代八字排盘或十神强弱计算; 医疗、寿夭、刑伤、贫贱等真人硬断; 将取象格名直接套用为确定结论 | D2 覆盖对象为三篇：上篇、中篇、下篇。quote-index 短引全部应能在 normalized fulltext exact-ish 命中。 版本风险：东里底本为现代整理 HTML；CTP/Wikisource/影印本逐字校对仍待补。 |
| `luming-nayin/li-xuzhong-mingshu` | 李虚中命书 | 六十甲子纳音五行性质判别（金溺水下、火出水上等十二音五行轻重）; 天乙贵神、贵合贵食、紫虚局之识别; 三元九命（天元干禄/地元支命/人元纳音身）总纲 | 现代职业、寿命、疾病、婚配的预测断语; 紫微星曜/宫位/四化系统（属于 references/ziwei/）; 子平日主格局之"用神/喜忌"系统（属于 references/bazi/） | 四庫全書本；正文與注文混排，蒸餾端須區分原文/注。 |
| `luming-nayin/luoluzi-sanming` | 珞琭子三命消息赋 | 早期禄命赋文研究：理解"以干为禄、以支为命"的核心方法论; 干支生克规则、向背、休囚、刑冲克破、合化的赋文化表达; 三才三元（天元/人元/支元）配合判读吉凶 | 现代寿夭/疾病/死亡断语（书中"建禄而夭寿""魂归岱岭""魄往酆都"等仅作文化研究参考）; 替代医学诊断、法律咨询、婚姻指导; 直接铁口断官杀、断财禄、断子嗣 | 維基文庫整理本；原賦與徐子平等注文混排，蒸餾端須分層。 |
| `luming-nayin/wuxing-jingji` | 五行精纪 | 早期禄命学百科式参考：六十甲子纳音/乾神/支神/五行/吉凶贵神/格局/疾病/大运; 术语溯源：贵局/凶煞/进神/天乙/三奇/华盖/金舆/学堂等术语之早期定义; 男女命格局/小儿/僧道/九流/吏卒/形貌/疾病/壽夭分门别类参考 | 现代寿夭/疾病/死亡断语（书中"论疾病""论寿夭"等仅作命书研究参考）; 替代医学诊断、法律咨询、婚姻指导; 直接铁口断官位/财禄/子嗣 | 宋廖中《五行精紀》；Wikisource 單頁全文。 |
| `luming-nayin/yuzhao-shenying` | 玉照神应真经 | 早期禄命断语风格的代表（"以年/胎/月/日/时为主"的多主参看）; 干支神将（青龙/白虎/勾陈/朱雀/玄武等）断语溯源; 与《李虚中命书》《珞琭子三命消息赋》对读 | 排盘事实计算（不替代 tool.bazi.paipan）; 子平法格局成败（应优先《子平真诠》）; 月令调候（应优先《穷通宝鉴》） | - 作者归属（晋郭璞撰系伪托；张顒生平不可考）须在待核验项中。 - 本地 normalized source 已完整取得；与永乐大典/影印本的逐句对校待补。 - 注文与正文层级标注（注文在原文以"注云"或圆括号"〔〕"区隔）需统一。 - 涉及寿夭/盗贼/官刑等极端断语必须严格 reframe。 |

## Runtime use

This card is capability and source metadata for selecting the transaction
system before `prepare`. During a live reading, use only the bounded evidence
returned by the transaction; do not load packs or run a separate corpus search.
