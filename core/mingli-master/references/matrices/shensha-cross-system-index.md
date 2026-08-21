# 神煞跨体系索引 (shensha-cross-system-index)

> source_status: derived_from_ready_packs_v0
> generated_at: 2026-07-05
> matrix_version: v0.2
> scope: 八字、早期禄命、择日、六壬、紫微、星命/七政四余、风水/阳宅中高频同名神煞的消歧与加载路由。

## 0. 使用边界

神煞不是独立 oracle。本文件只回答两个问题：

1. 用户提到某个神煞时，它可能属于哪个体系。
2. 主 skill 应该加载哪一本 ready pack，并把它放在多大权重。

如果问题是“神煞相关应看哪些书 / 哪些书能继续蒸馏 / 哪些来源还不能用”，先读 `references/matrices/shensha-entry-source-profile.yaml`、`references/matrices/shensha-quote-trace.yaml`、`references/matrices/shensha-source-book-matrix.md` 和 `references/matrices/shensha-source-book-matrix.yaml`。本文件只管名称与体系消歧，具体条目的 `book_priority` / `source_pack_role` 以 entry source profile 为准，可追溯锚点以 quote trace 为准，书籍 readiness 以 source-book matrix 为准。

神煞结论必须依附完整事实层：

- 八字：必须已有 `tool.bazi.paipan` 等价输出，含四柱、藏干、十神、月令、调候/季节标记。
- 择日：必须已有 `mingli-master.selection.v1` 确定性输出，含候选日、建除、黄黑道、宜忌、神煞、冲犯、方位避忌。
- 六壬：必须已有课式事实层，含四课三传、天地盘、神将、日辰、月将、年命等。
- 紫微：必须已有紫微命盘事实层，含宫位、星曜、四化、大限/流年。
- 星命/七政四余：必须已有星命天文排盘事实层，含七政四余、度数、宫位/垣局映射和现代星历校正。
- 风水/阳宅：必须已有宅向、命卦或宅卦、门灶床房位、外形冲煞、动工/修补用事等事实层。
- 禄命纳音：只作源流与旁证，不能替代现代子平格局、调候、旺衰判断。

## 1. 总权重策略

| 体系 | 神煞权重 | 一线来源 | 使用说明 |
|---|---:|---|---|
| 八字子平 | 辅助层 | `bazi/sanming-tonghui`; `luming-nayin/wuxing-jingji`; `luming-nayin/li-xuzhong-mingshu` | 先看月令、格局、旺衰、调候、十神；神煞只用于事项标签、应象、例外提示。 |
| 早期禄命/纳音 | 源流层 | `li-xuzhong-mingshu`; `luoluzi-sanming`; `wuxing-jingji`; `yuzhao-shenying` | 很多神煞源流在此更密集；只可说明历史口径和旁证，不覆盖子平主线。 |
| 择日 | 计算层 | `selection/xieji-bianfang-shu`; `selection/xingli-kaoyuan` | 神煞是择日事实层核心之一；没有历算输出不得选日。 |
| 六壬 | 课内语义层 | `san-shi/daliuren-daquan`; `san-shi/liuren-zhiyin` | 神煞必须与干支、神将、刑克、课传同参；不可移植到八字或择日结论。 |
| 紫微斗数 | 星曜/限运层 | `ziwei/ziwei-doushu-quanshu`; `ziwei/taiwei-fu`; `ziwei/feixing-ziwei-doushu-yuanzhi` | 同名词多是星曜、流煞或格局，不等同八字神煞。 |
| 星命/七政四余 | 天文盘内层 | `xingming/guotian-jing` | 仅在星命天文排盘内使用；《果天经/果老星宗》ready 但有托名/版本风险，旧度数表不得当现代星历。 |
| 风水/阳宅 | 方位/宅局层 | `fengshui/yangzhai-shishu`; `fengshui/yangzhai-sanyao`; 后续候选《阳宅爱众篇》 | 八宅游年九星、门灶床房位、外形冲煞只在宅局事实层内使用；不可当作命盘神煞。 |

## 2. 高频神煞消歧表

| 名称 | 可能别名 | 可用体系 | 第一来源 | 计算/定位锚 | 权重 | 禁止串台 |
|---|---|---|---|---|---|---|
| 天乙贵人 | 天乙贵神、贵人、贵神 | 八字、禄命、六壬 | `sanming-tonghui` 卷三；`wuxing-jingji` WX-T39；`li-xuzhong-mingshu` LX-02-02；`daliuren-daquan` LT-201 | 八字/禄命按干支贵人位；六壬为十二天将之首，昼夜贵人口径另行确定 | 八字辅助；六壬课内核心 | 八字天乙贵人 != 六壬天乙贵人。六壬昼夜贵人以《星历考原》《协纪辨方书》订正口径优先。 |
| 游年九星/天乙巨门 | 生气、延年、天乙、伏位、五鬼、六煞、祸害、绝命 | 风水/阳宅/八宅 | `yangzhai-shishu` YZS-T005~YZS-T011；`yangzhai-sanyao` 八宅条目；后续《阳宅爱众篇》 | 以宅向/命卦/门灶床房位起游年九星 | 宅局辅助或核心方位层 | 八宅天乙巨门不是八字天乙贵人，也不是六壬天乙天将；五鬼六煞也不能移植成命盘神煞。 |
| 天德/月德 | 天月德、天德合、月德合 | 八字、禄命、择日、六壬 | `sanming-tonghui` 神煞组；`xieji-bianfang-shu` 月神；`xingli-kaoyuan` KR-11；`liuren-zhiyin` LZ-Q040 | 多按月令/月份轮转；择日另含合神 | 吉神辅助；择日可入必算项 | 八字贵人/择日吉神/六壬月煞同名不同算法。 |
| 文昌 | 文星 | 八字、禄命、紫微 | `sanming-tonghui`; `li-xuzhong-mingshu` 文星贵神；`ziwei-doushu-quanshu` ZW-T021 | 八字/禄命按干支贵神；紫微为星曜 | 学业文气辅助 | 八字文昌 != 紫微文昌星。 |
| 太极贵人 | 太极贵、太極貴人 | 八字、禄命源流 | `sanming-tonghui` R-03-08；`wuxing-jingji` 九流/太极贵人旁证 | 以日干/年干查地支；禄命中可作九流/术数倾向旁证 | 智慧、玄学、学习倾向轻辅助 | 不等于学历、职业或玄学能力保证。 |
| 三奇贵人 | 三奇、天上三奇、地下三奇、人中三奇 | 八字、禄命、奇门易混 | `sanming-tonghui` R-03-07；`wuxing-jingji` WX-T46；`luoluzi-sanming` LZ-03 | 八字/禄命按天干组合、顺布等条件；奇门三奇另属盘局 | 稀有格局辅助 | 八字三奇贵人 != 奇门乙丙丁三奇。 |
| 学堂/词馆 | 学堂词馆、學堂詞館 | 八字、禄命 | `sanming-tonghui` R-03-09；`wuxing-jingji` WX-T54/WX-05-07 | 八字按日干查支；禄命多取五行长生位 | 文章、学业、表达辅助 | 不可单独断考试、学历、文才上限。 |
| 德秀 | 德秀贵人 | 八字 | `sanming-tonghui` R-03-11 | 多按月支查天干 | 气质、容貌、品性轻辅助 | 不替代十神、格局和现实观察。 |
| 天医 | 天醫 | 择日、六壬、部分八字口径 | `xieji-bianfang-shu` 祭祀/医疗用事；`daliuren-daquan` DL-Q0028 等 | 择日按用事日神；六壬见逐月/课内神煞 | 医疗/解厄事项辅助 | 不能把择日天医当成命盘健康保证。 |
| 禄/禄神/禄存/化禄 | 干禄、天禄、天元禄、地元禄、人元禄 | 八字、禄命、紫微、星命 | `sanming-tonghui`; `wuxing-jingji` WX-T40/42；`li-xuzhong-mingshu` LX-T54；`ziwei-doushu-quanshu` 禄存/化禄；`guotian-jing` 禄神/化禄 | 八字干禄/禄马；禄命干禄源流；紫微为禄存或四化禄；星命依天文盘 | 财禄/职位辅助 | 八字干禄、紫微禄存/化禄、星命禄神/化禄不是同一算法；风水九星禄存另属形峦/宅局名物。 |
| 驿马/天马 | 马、月驿、岁驿、天馬 | 八字、禄命、择日、六壬、紫微、星命 | `sanming-tonghui` vol-03/yima；`wuxing-jingji` WX-T41；`xieji-bianfang-shu` 出行；`daliuren-daquan`; `taiwei-fu` TT-L03；`guotian-jing` 天马地驿 | 八字/禄命常按三合局冲位；择日按出行历算；六壬按课内神煞；紫微为天马星；星命依天文盘 | 动迁、出行、变化 | 天马/驿马是最高风险同名词之一，必须先问体系。 |
| 将星 | 月将、将神 | 八字、禄命、六壬 | `sanming-tonghui` vol-02/jiangxing-huagai；`luoluzi-sanming` LZ-T19 | 八字多取三合局中位；六壬月将为课式核心 | 八字辅助；六壬核心事实 | 八字将星 != 六壬月将。 |
| 华盖 | 华盖贵神、轩盖 | 八字、禄命、六壬、紫微格局旁证 | `sanming-tonghui`; `wuxing-jingji` WX-T52；`li-xuzhong-mingshu` LX-T23；`daliuren-daquan` 轩盖课 | 八字/禄命多取三合墓位；六壬按课名/神位组合 | 文艺、孤高、宗教气象辅助 | 不能只见华盖就断孤僻或宗教。 |
| 金舆 | 金輿、金舆贵人、金舆捧栉 | 八字、禄命、紫微 | `sanming-tonghui` R-03-06；`wuxing-jingji` WX-T53；`taiwei-fu` TT-P11 | 八字/禄命按干支神煞；紫微为格局名 | 车驾、迁动、礼遇轻辅助 | 八字金舆 != 紫微金舆捧栉。 |
| 咸池/桃花 | 桃花煞、天姚、犯水桃花 | 八字、六壬、紫微、星命 | `sanming-tonghui` vol-02/xianchi；`daliuren-daquan` DL-Q0032 等；`taiwei-fu` 桃花犯主；`feixing-ziwei-doushu-yuanzhi` FZ-T15；`guotian-jing` 咸池 | 八字多取三合沐浴位；紫微按星曜/宫位组合；星命依天文盘 | 情感、审美、人缘辅助 | 八字咸池 != 紫微贪狼/天姚/咸池星曜象；星命咸池另需星命事实层。 |
| 红鸾/天喜 | 紅鸞、喜神 | 八字、紫微、六壬 | `sanming-tonghui` 红鸾天印；`feixing-ziwei-doushu-yuanzhi` FZ-R05/R07；`daliuren-daquan` DL-Q0050 等 | 八字为神煞/杂格；紫微为限运星曜组合；六壬为月煞 | 婚恋喜庆辅助 | 不可每次问运势都机械输出婚恋/财务。 |
| 羊刃/阳刃 | 阳刃、擎羊、流羊 | 八字、禄命、紫微、星命 | `sanming-tonghui` vol-03/yangren 与卷六阳刃格；`wuxing-jingji` WX-T94；`taiwei-fu` TT-K01；`feixing-ziwei-doushu-yuanzhi` FZ-T16；`guotian-jing` 阳刃 | 八字按阳干刃位；紫微为擎羊/流羊星煞；星命依天文盘 | 强硬、刑伤、冲动辅助 | 八字羊刃格 != 紫微擎羊/流羊；星命阳刃不得移植到八字。 |
| 空亡 | 旬空、天中、截路空亡 | 八字、禄命、紫微、星命 | `sanming-tonghui` R-03-04；`wuxing-jingji` WX-T66；`li-xuzhong-mingshu` 截路空亡；`taiwei-fu` TT-M06；`guotian-jing` 空亡 | 八字/禄命按旬空；紫微按落空亡位；星命依天文盘 | 落空、虚耗、变化辅助 | 空亡不是必凶；星命空亡与八字旬空/天中不是同一算法。 |
| 劫煞 | 刼煞、劫亡 | 八字、禄命、择日、六壬、星命 | `sanming-tonghui` R-03-13；`wuxing-jingji` WX-T62；`xieji-bianfang-shu` 年家三煞；`daliuren-daquan` 起例；`guotian-jing` 劫亡 | 八字/禄命多按三合局；择日按年/月家；六壬按课内表；星命依天文盘 | 凶煞辅助 | 不同体系算法不同，不能汇总加分。 |
| 亡神 | 元亡 | 八字、禄命、六壬 | `sanming-tonghui` vol-03/jiesha-wangshen；`wuxing-jingji` WX-T63；`luoluzi-sanming` LZ-T92；`daliuren-daquan` | 八字/禄命按三合局；六壬按课内神煞 | 失脱、孤立、隐忧辅助 | 不能单独断灾。 |
| 灾煞/岁煞/三煞 | 災煞、三煞方 | 八字、择日、六壬 | `sanming-tonghui` R-03-14；`xieji-bianfang-shu` XR-03/三煞方；`daliuren-daquan` | 八字多为三合沐浴位；择日为年家/方位避忌；六壬课内表 | 择日/动土权重高；八字辅助 | 八字灾煞 != 择日三煞方。 |
| 孤辰/寡宿 | 孤寡 | 八字、禄命、择日、六壬 | `sanming-tonghui`; `wuxing-jingji` WX-T95/96；`xieji-bianfang-shu` 嫁娶忌；`daliuren-daquan` | 多按年支/三会组查；择日按嫁娶忌日 | 婚恋/孤独辅助 | 不能单独断婚姻必坏。 |
| 魁罡 | 天罡河魁 | 八字、禄命 | `sanming-tonghui` R-06-01；`li-xuzhong-mingshu`; `yuzhao-shenying` 天罡/河魁 | 八字以特定日柱为核心；禄命多为支神/肃杀象 | 性情/格局辅助 | 年柱或他柱见魁罡不等同日魁罡格。 |
| 十恶大败 | 十惡大敗 | 八字、择日 | `sanming-tonghui` R-03-17；`xieji-bianfang-shu` 日神/通用忌 | 八字按年柱查日柱；择日为通用凶日 | 八字辅助；择日较高 | 不能把命盘十恶大败和某日择日忌直接合并。 |
| 日贵/日德 | 日貴、日德、日贵格、日德格 | 八字 | `sanming-tonghui` R-06-21；`yuanhai-ziping` 论日贵/论日德；`shenfeng-tongkao` 批判旧说 | 特定日柱贵格，刑冲破害则减力 | 日柱特格辅助 | 不等同普通天乙贵人或天月德；张神峰批判层需保留。 |
| 天罗/地网 | 罗网 | 八字、禄命 | `sanming-tonghui` vol-03/tianluo-diwang；`luoluzi-sanming` LZ-T62 | 常以辰巳、戌亥等罗网位查 | 束缚/阻滞辅助 | 不属于择日黄黑道。 |
| 元辰/大耗/小耗 | 元辰、大耗、小耗 | 八字、择日、紫微、六壬 | `sanming-tonghui` R-03-12；`xingli-kaoyuan` 月凶神；`xieji-bianfang-shu` 大耗日；`feixing-ziwei-doushu-yuanzhi` FZ-T14 | 八字按年支查元辰；择日按月凶/日神；紫微为星曜组合 | 耗损、支出、失脱辅助 | 不要每次运势都强行说财务。 |
| 太岁/岁君/岁破 | 太歲、岁神、岁君 | 八字、择日、六壬、紫微、太乙 | `xingli-kaoyuan` KR-08；`xieji-bianfang-shu` 年神；`daliuren-daquan` DL-Q0023；`ziwei-doushu-quanshu` ZW-T060 | 年支/年神；六壬岁君；紫微流年太岁 | 流年、方位、课式均重要 | 太岁在各体系是“年位/年君”概念，不是同一条规则。 |
| 白虎 | 白虎星、虎 | 择日、六壬、紫微、禄命 | `xingli-kaoyuan` 年神/黑道；`daliuren-daquan` LT-208；`taiwei-fu`; `yuzhao-shenying` | 择日年神/黑道；六壬天将；紫微流煞/星煞；禄命干神 | 凶象辅助；六壬类神较强 | 六壬白虎天将 != 择日白虎日/方。 |
| 丧门/吊客 | 喪門、弔客 | 六壬、紫微、禄命 | `daliuren-daquan` 病占/逐月神煞；`liuren-miben`; `taiwei-fu`; `luoluzi-sanming` LZ-T83 | 六壬课内神煞；紫微流年小煞；禄命岁命前后辰 | 丧吊、病耗辅助 | 必须有事实层触发，不能裸断丧事。 |
| 官符/病符 | 官府、官符杀、病符、死符、天官符 | 紫微、择日、六壬、禄命 | `xingli-kaoyuan` XK-Q131/XK-Q229/XK-Q245；`xieji-bianfang-shu` XJ-Q0043；`taiwei-fu` TT-X05；`wuxing-jingji` WX-Q563/WX-Q565 | 择日为年/月/日神避忌；紫微为流年小煞；禄命为岁命神煞 | 法务/疾病旁证 | 不作现代法律/医疗事实判断。 |
| 天刑 | 天刑星、黑道天刑 | 紫微、择日、六壬、星命 | `ziwei-doushu-quanshu` ZW-T035；`feixing-ziwei-doushu-yuanzhi` FZ-T17；`xingli-kaoyuan` 黄黑道；`daliuren-daquan`；`guotian-jing` 天刑 | 紫微星曜；择日黑道六神；六壬课内神煞；星命依天文盘 | 刑伤/法务辅助 | 同名差异很大，先分体系。 |
| 黄道/黑道 | 六黄道、六黑道 | 择日、禄命少量术语 | `xingli-kaoyuan` KR-14；`xieji-bianfang-shu` 黄黑道 | 按月建逐日轮配 | 择日核心 | 不是天文学黄道，也不是八字主线。 |
| 建除十二神 | 建除、除满平定执破危成收开闭 | 择日 | `xieji-bianfang-shu` XR-04；`xingli-kaoyuan` 月建/月破 | 按月支起建逐日轮排 | 择日核心 | 不用于命盘断人生。 |
| 月破/月厌/月害 | 月厭、受死 | 择日、六壬 | `xingli-kaoyuan` KR-12；`xieji-bianfang-shu`; `daliuren-daquan` | 择日按月神；六壬课内月煞 | 择日忌项；六壬课内辅助 | 不可从月破日直接断个人命局。 |
| 四废/四离/四绝 | 四廢 | 择日、六壬 | `xingli-kaoyuan` KR-13；`xieji-bianfang-shu`; `daliuren-daquan` DL-Q0034 | 节气/季节或课内表 | 择日忌项 | 只对用事/起课有效，不是出生命盘铁断。 |
| 金神七煞 | 金神、七煞方 | 择日、六壬、八字杂项 | `xingli-kaoyuan` KR-09；`xieji-bianfang-shu` 年神；`daliuren-daquan` 起例 | 择日由年干推方；六壬课内表 | 动土修造避忌 | 择日金神 != 八字金神格。 |
| 大将军 | 博士对宫 | 择日 | `xingli-kaoyuan` KR-10；`xieji-bianfang-shu` 年神 | 年支三方/对冲口径 | 方位避忌 | 与八字“将星/将军箭”等不可混用。 |
| 月空/母仓/解神 | 月空、母仓日、解神 | 择日、六壬 | `xingli-kaoyuan` KR-11；`xieji-bianfang-shu`; `daliuren-daquan` | 月吉神或课内神煞 | 择日吉神 | 不迁移为八字命盘贵人。 |
| 青龙/朱雀/六合/勾陈/玄武/太常/太阴/天后 | 十二天将、十干支神 | 六壬、禄命、择日黄黑道 | `daliuren-daquan` 神将释；`yuzhao-shenying` 干支神；`xingli-kaoyuan` 黄黑道 | 六壬为天将；禄命为干支神；择日为黄黑道神 | 六壬核心；其他体系辅助 | 同名不能横向等同。 |
| 三刑/六害 | 刑害 | 八字、禄命、择日旁证、星命 | `wuxing-jingji` WX-T64/65；`yuzhao-shenying`; `sanming-tonghui`；`guotian-jing` 三刑六害 | 地支关系；星命依天文盘 | 结构辅助 | 不是神煞孤断，必须看全局；星命三刑六害不得直接并入八字地支刑害。 |
| 伏吟/反吟 | 返吟 | 禄命、六壬/奇门常见 | `luoluzi-sanming` LZ-07-03；`wuxing-jingji` WX-T100/WX-10-04；`daliuren-daquan` LT-108/LT-109 | 禄命看岁运与元命同位/冲返；六壬为起课宗法 | 变动/重复辅助；六壬课法核心 | 禄命岁运伏吟反吟、六壬伏吟反吟、奇门反吟伏吟不可互换。 |

## 3. 输出流程

当用户问“某个神煞是什么意思”：

1. 先定位体系：八字命盘、择日用事、六壬课、紫微盘，还是古籍源流。
2. 查 `shensha-name-disambiguation.yaml`，确定同名风险。
3. 查 `shensha-entry-source-profile.yaml`，确定该条目在该体系的 P0/P1 书目、`source_pack_role` 和 acquisition-only 限制。
4. 查 `shensha-quote-trace.yaml`，优先使用 `first_line_quote_index_hit`；若只有 layer hit 或 second-pass gap，必须先人工检查 pack 文件，不可直接晋升为断语。
5. 加载本表中对应第一来源的 `terms.md` / `rules.md` / `quote-index.md`。
6. 若用户给的是实际命盘/日课/课式，先验证事实层，再解释该神煞在该体系中的权重。
7. 明确说明“它能说明什么”和“它不能单独说明什么”。

当用户问“我命里有哪些神煞”：

1. 只在完整八字事实层存在时回答。
2. 先列常见且有作用的神煞，再列缺失的重要神煞。
3. 每个神煞给一句现实翻译；不要堆冷门星名。
4. 不让神煞覆盖格局、调候、大运流年。

当用户问“择日/出行/动土/婚嫁”：

1. 神煞属于事实层，不是解释层；没有 `mingli-master.selection.v1` 完整输出则停止。
2. 必须同时看建除、黄黑道、宜忌、冲犯、方位避忌。
3. 出行至少补驿马/天马、往亡/归忌、四离四绝/杨公忌、黄道吉时。

## 4. 待补神煞相关书籍/专题

以下只作为后续 acquisition backlog；未有完整原文前不得升级为一线 reference：

| 候选方向 | 候选书/专题 | 预期用途 | 当前策略 |
|---|---|---|---|
| 八字神煞专题 | 《三命通会》卷三神煞细校、《渊海子平》神煞段、《五行精纪》神煞卷 | 子平/禄命神煞源流对照 | 已有 ready pack，后续做章节级二次精校；条目优先级见 `shensha-entry-source-profile.yaml`。 |
| 禄命神煞源流 | 《李虚中命书》、《珞琭子三命消息赋》、《玉照神应真经》、《兰台妙选》 | 早期神煞、禄马贵神、刑害罗网 | 已有 ready pack，可继续扩展索引。 |
| 择日神煞 | 《钦定协纪辨方书》、《御定星历考原》 | 年月日时神煞、黄黑道、建除、方位忌 | 已有 ready pack，优先作为计算字段规范。 |
| 六壬神煞 | 《六壬大全》、《六壬指南》、《大六壬秘本》 | 课内神煞与天将类神 | 已有 ready pack，继续补“不可孤用”测试。 |
| 紫微小星/流煞 | 《紫微斗数全书》、《太微赋》、民国《斗数观测录》 | 小星、流煞、限运事件标签 | 已有 ready pack，必须依赖紫微盘事实层。 |
| 通书民间神煞 | 《玉匣记》、《董公择日》 | 大众通书对照 | 只能作通书系 comparison，不覆盖官方择日框架。 |
| 星平/星命神煞 | ready: `xingming/guotian-jing`《果天经/果老星宗》；backlog: 《星平会海》/《新刻星平总会命海全编》 | 果老星宗用于七政四余神煞；星平会海用于诸吉神、诸煞星、小儿关煞补源 | `guotian-jing` 可用但需星命 fact layer 与版本风险提示；`minghai-quanbian` 未 OCR 前不得升为一线。 |
| 阳宅/风水神煞 | 《阳宅爱众篇》、八宅派相关书 | 八宅游年九星、宅门修补择时、庙宇/宅局神煞线索 | 只在风水事实层内使用；不得移植到八字/择日/六壬。 |
| 葬法/墓葬神煞 | 《大汉原陵秘葬经》及墓葬神煞研究 | 墓葬神煞历史源流 | 低频文化史旁证，不做现代个人断语。 |

## 5. 误用红线

- 不因某个神煞单独断寿夭、疾病、牢狱、婚败、发财、灾祸。
- 不把择日神煞当作命盘神煞。
- 不把六壬神将/神煞搬到八字盘。
- 不把紫微星曜当八字神煞。
- 不把八宅游年九星、天乙巨门、五鬼六煞当作八字神煞或六壬天将。
- 不在没有事实层时解释“你命里有/没有某星”。
- 不把同名神煞的多个体系含义相加，制造“越多越准”的错觉。
