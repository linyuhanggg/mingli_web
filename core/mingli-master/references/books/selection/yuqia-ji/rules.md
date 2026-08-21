# 玉匣记 — Rules

> 全书判断规则。前缀 `JR-` = Yuqia-Ji Rule（玉匣记规则；J=玉匣 jiá xiá）。
> 所有规则 `verified: false`；具体日期吉凶必须转 mingli-master.selection.v1。
> 规则定位：本书是"民俗禁忌日的代表汇编"；全部规则属"民俗参考"层。

---

## JR-01 总纲：民俗参考定位

- **rule_id**: JR-01
- **rule_statement**: 本书为民间通书系经典；其规则定位是"民俗信仰与禁忌日的汇编"，与官方典籍冲突时以官方为准。所有规则均为民俗参考，不构成事实判断。
- **source_chapter**: front
- **applicable_to**: 主 skill 在引用本 pack 任何规则时
- **caveats**: 文化参考，非事实判断
- **verified**: false

## JR-02 玉匣记日期通则（许真君）

- **rule_id**: JR-02
- **rule_statement**: 本书核心组"许真君日期"逐月列出宜祭祀 / 沐浴 / 修真 / 上章 / 用事 / 起造 / 出行 / 嫁娶等的吉日。具体日子由 tool 根据农历输出。
- **source_chapter**: theory/01-yuqia-riqi
- **applicable_to**: 道教信仰下的择日参考
- **caveats**: 文化参考，非事实判断
- **verified**: false

## JR-03 三元五腊日

- **rule_id**: JR-03
- **rule_statement**: 三元：上元正月十五（天官诞）、中元七月十五（地官诞）、下元十月十五（水官诞）。五腊：天腊正月初一、地腊五月初五、道德腊七月初七、民岁腊十月初一、王侯腊十二月初八。诸日宜祭祀斋戒。
- **source_chapter**: theory/03-sanyuan-wula
- **applicable_to**: 道教节日 / 祭祀择日
- **verified**: false

## JR-04 二十八宿值日吉凶歌

- **rule_id**: JR-04
- **rule_statement**: 二十八宿按七曜（日月火水木金土）周而复始配日；本书有"角木蛟亢金龙氐土貉…"长歌，逐宿配吉凶事项；与协纪辨方书卷五口径基本一致。
- **source_chapter**: theory/08-28xiu-jixiong
- **applicable_to**: 日吉凶的星宿层判定
- **verified**: false

## JR-05 彭祖百忌

- **rule_id**: JR-05
- **rule_statement**: 彭祖百忌歌：天干十忌（甲不开仓 / 乙不栽植 / …）+ 地支十二忌（子不问卜 / 丑不冠带 / …）；按当日干支匹配避忌事项。
- **source_chapter**: folk/16-pengzu-baiji
- **applicable_to**: 民间日常用事的快速避忌口诀
- **caveats**: 文化参考，非事实判断
- **verified**: false

## JR-06 杨公十三忌

- **rule_id**: JR-06
- **rule_statement**: 每年农历十三个固定日为杨公忌（正月十三、二月十一、三月初九、四月初七、五月初五、六月初三、七月初一/廿九、八月廿七、九月廿五、十月廿三、十一月廿一、十二月十九）；忌一切用事。
- **source_chapter**: folk/17-yanggong-ji
- **applicable_to**: 民间通用避忌
- **caveats**: 文化参考，非事实判断；具体日期由 tool 输出。
- **verified**: false

## JR-07 月忌日

- **rule_id**: JR-07
- **rule_statement**: 农历每月初五、十四、廿三三日为月忌日；忌一切用事，尤忌远行。
- **source_chapter**: folk/18-yueji
- **applicable_to**: 月内通用避忌
- **caveats**: 文化参考，非事实判断
- **verified**: false

## JR-08 十恶大败日

- **rule_id**: JR-08
- **rule_statement**: 十恶大败日为八字 / 择日双系大凶日；干支组合：甲辰、乙巳、丙申、丁亥、戊戌、己丑、庚辰、辛巳、壬申、癸亥（一说异于此）；取义"十干受死"。
- **source_chapter**: folk/06-shi-edabai
- **applicable_to**: 八字命理 + 择日双用
- **caveats**: 文化参考，非事实判断
- **verified**: false

## JR-09 伏断 / 上下兀 / 上朔 / 火星 / 长短星

- **rule_id**: JR-09
- **rule_statement**: 伏断日（伏神断神共值）/ 上兀日 / 下兀日 / 上朔日 / 火星日 / 长星日 / 短星日，皆民俗凶日；具体起例由 tool 输出。
- **source_chapter**: folk/07-fuduan-ri ~ folk/11-changduan-xing
- **applicable_to**: 民间通用避忌
- **caveats**: 文化参考，非事实判断
- **verified**: false

## JR-10 九土鬼日（忌动土）

- **rule_id**: JR-10
- **rule_statement**: 九土鬼日为忌动土的民俗凶日；与起造 / 修造 / 葬埋的择日通则联用。
- **source_chapter**: folk/12-jiutu-gui
- **applicable_to**: 起造 / 动土避忌
- **caveats**: 文化参考，非事实判断
- **verified**: false

## JR-11 人神所在日（医疗禁忌）⚠️

- **rule_id**: JR-11
- **rule_statement**: 每日"人神"游某身体部位（如初一在脚拇指、初二在外踝…）；古俗忌该部位针灸 / 手术 / 服药。
- **source_chapter**: folk/14-renshen-suozai
- **applicable_to**: 古代针灸择日
- **caveats**: **重要警告**：本规则为古代民俗，**现代医疗不应据此延误就医**。输出时必须明确提示"请遵从医疗专业意见"。文化参考，非事实判断。
- **verified**: false

## JR-12 探病忌日 ⚠️

- **rule_id**: JR-12
- **rule_statement**: 民俗探病忌日为壬寅 / 壬午 / 庚午 / 甲寅 / 乙卯 / 己卯 等若干日；忌之恐沾凶气。
- **source_chapter**: folk/19-tanbing-ji
- **applicable_to**: 民俗探病避忌
- **caveats**: **重要警告**：本规则为古代民俗，**现代不应据此延误探视、就医、医疗陪护**。文化参考，非事实判断。
- **verified**: false

## JR-13 鹤神方位 / 鹤神日游方

- **rule_id**: JR-13
- **rule_statement**: 鹤神为民俗方位之神；按日逐方游走（"鹤神日游方"）。鹤神所在方位忌兴造 / 出行 / 嫁娶。
- **source_chapter**: folk/21-heshen-fang
- **applicable_to**: 民俗方位避忌
- **caveats**: 文化参考，非事实判断
- **verified**: false

## JR-14 嫁娶吉日（民俗版）

- **rule_id**: JR-14
- **rule_statement**: 民俗嫁娶吉日宜天德 / 月德 / 三合 / 六合 / 不将 / 母仓等吉神；忌十恶大败 / 月厌 / 月破 / 杨公忌 / 月忌日 / 受死 / 八专。与协纪辨方书卷七嫁娶通例基本一致。
- **source_chapter**: folk/28-jiaqu-zaozao
- **applicable_to**: 民俗嫁娶择日
- **caveats**: 文化参考，非事实判断
- **verified**: false

## JR-15 出行吉日（含诸葛逐年出行图）

- **rule_id**: JR-15
- **rule_statement**: 民俗出行宜驿马 / 天马 / 三合 / 六合等；忌往亡 / 归忌 / 月破 / 受死 / 杨公忌 / 月忌日。本书附"诸葛武侯逐年出行图"作年度专项参考。
- **source_chapter**: folk/27-zhuge-chuxing
- **applicable_to**: 民俗出行择日
- **caveats**: 文化参考，非事实判断
- **verified**: false

## JR-16 上官赴任 / 应试赴举吉日

- **rule_id**: JR-16
- **rule_statement**: 上官赴任宜驿马 / 三合 / 月恩 / 鸣吠对；应试赴举宜青龙 / 太常 / 文昌 / 学馆等。专项历法对应古代官场学业。
- **source_chapter**: folk/24-shangguan-furen, folk/25-linzheng-jinshu
- **applicable_to**: 古代官场学业择日
- **caveats**: 文化参考，非事实判断；现代考试 / 任职无可靠对应。
- **verified**: false

## JR-17 安葬吉日（民俗版）

- **rule_id**: JR-17
- **rule_statement**: 民俗安葬宜鸣吠 / 鸣吠对 / 月恩 / 三合；忌重丧 / 复日 / 重日 / 月破 / 月厌 / 楊公忌 / 十恶大败。与协纪辨方书卷七安葬通例基本一致。
- **source_chapter**: folk/28-jiaqu-zaozao
- **applicable_to**: 民俗安葬择日
- **caveats**: 文化参考，非事实判断
- **verified**: false

## JR-18 杂占占断（梦 / 耳鸣 / 眼跳 / 禽鸟）⚠️

- **rule_id**: JR-18
- **rule_statement**: 本书杂占篇收占梦、占耳鸣眼跳、占禽鸟、占灯花等民俗占断；以"梦兆 → 吉凶事项"或"身体征兆 → 吉凶事项"作映射。
- **source_chapter**: zhanbu/01-meng ~ zhanbu/04-yingerlinger
- **applicable_to**: 民俗杂占（民间信仰参考）
- **caveats**: **重要警告**：杂占完全为民俗信仰，无任何科学依据；现代不构成事实判断。仅作文化研究参考。
- **verified**: false

## JR-19 民俗时辰判定（猫眼 / 定寅时）

- **rule_id**: JR-19
- **rule_statement**: 民俗以猫瞳孔形状判时辰（子午圆 / 丑未亥扁 / 寅申巳枣核 等）；定寅时按节气月相调整。
- **source_chapter**: folk/01-time-tools
- **applicable_to**: 民俗时辰判定
- **caveats**: 文化参考，非事实判断；现代以钟表为准。
- **verified**: false

## JR-20 民俗禁忌日的合并应用规则

- **rule_id**: JR-20
- **rule_statement**: 主 skill 输出某日吉凶时，应将"官方层（协纪辨方书 / 星历考原）"作为权重主源，本书禁忌日（彭祖百忌 / 杨公忌 / 月忌日 / 十恶大败 等）作为补充避忌；不重复计算同一神煞的口径差异。
- **source_chapter**: cross-pack
- **applicable_to**: 主 skill 的择日聚合层
- **caveats**: 文化参考，非事实判断
- **verified**: false

---

**说明**：共 20 条规则。本书规则的核心特色是"民俗禁忌日大全"；具体某日某事的吉凶判断必须转 `mingli-master.selection.v1`。涉及医疗的禁忌日（JR-11 / JR-12）必须额外强提示遵循医疗专业意见。
