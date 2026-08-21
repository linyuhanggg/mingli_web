---
slug: tianyu-jing
file: rules
---

# 天玉经 规则集

> 以下规则是“古籍语义抽取”，不直接用于现实风水判断。凡涉及坐向、水口、挨星、零正神，均依赖工具或人工校勘。

## TYR-01: 三卦总纲

- **source_chapter**: shang-sanban
- **rule**: 以江东、江西、南北三卦组织二十四龙，并以父母关系解释阴阳会合。
- **source_anchor**: fulltext.md L5-L19
- **caveats**: 版本中对江东/江西/南北的解释多为注解层；不得只凭 LLM 套用于实地坐向。
- **verified**: false

## TYR-02: 天卦与地卦分用

- **source_chapter**: shang-sanban
- **rule**: 天卦偏向“以地支从天干”的水之用，地卦偏向“以天干从地支”的山水相对之用。
- **source_anchor**: fulltext.md L23-L31
- **caveats**: 此为注解阐释，不等同于所有玄空派统一口径。
- **verified**: false

## TYR-03: 父母阴阳前后相兼

- **source_chapter**: shang-sanban
- **rule**: 父母不同则阴阳异路，前兼后与后兼前分属两路，用于解释向首与龙家的不同作用。
- **source_anchor**: fulltext.md L33-L35
- **caveats**: 必须保留“向首/龙家”二分，不能合并成单一口诀。
- **verified**: false

## TYR-04: 玄空取地卦倒加天卦

- **source_chapter**: shang-sanban
- **rule**: 文中以地卦倒加天卦、随流神阴阳顺逆起九星，称为玄空八卦。
- **source_anchor**: fulltext.md L47-L49
- **caveats**: 仅作源流锚点；实际起星必须由工具处理。
- **verified**: false

## TYR-05: 三阳六秀二神

- **source_chapter**: shang-sanban
- **rule**: 三阳水朝并流归墓地、六秀入局不出本卦二神，是文本中的水中小贵格框架。
- **source_anchor**: fulltext.md L51-L53
- **caveats**: “富贵”“入朝堂”等为古代价值语汇，现代使用只作文献理解。
- **verified**: false

## TYR-06: 零正神坐向边界

- **source_chapter**: shang-sanban
- **rule**: 文中以正神/零神区分立向与发水，强调支神、干神在水法中的不同位置。
- **source_anchor**: fulltext.md L81-L87
- **caveats**: 各派零正神定义差异大；master skill 必须调用流派上下文。
- **verified**: false

## TYR-07: 二十四山分两路

- **source_chapter**: shang-sanban
- **rule**: 二十四山分阴阳顺逆两路，需辨五行主、交战与公位。
- **source_anchor**: fulltext.md L93-L95
- **caveats**: “交战”只作传统理气术语，不作现代因果陈述。
- **verified**: false

## TYR-08: 挨星仍以三合五行为本

- **source_chapter**: zhong-aixing
- **rule**: 文中称挨星虽贵，但注解强调仍以三合五行生旺墓绝作为判断根基。
- **source_anchor**: fulltext.md L126-L130
- **caveats**: 这是本底本注解口径；与后世玄空飞星派可能不完全一致。
- **verified**: false

## TYR-09: 天地父母三般卦为玄空大卦源头

- **source_chapter**: zhong-aixing
- **rule**: 天卦、地卦、父母卦构成三般卦框架；文中把玄空大卦归为此经诀。
- **source_anchor**: fulltext.md L136-L138
- **caveats**: 可作为《地理辨正》系阅读路由，但不直接裁判各派真伪。
- **verified**: false

## TYR-10: 四龙公位

- **source_chapter**: zhong-aixing
- **rule**: 折水以子寅辰乾丙乙等四组配长男、二男、三男、四男等公位。
- **source_anchor**: fulltext.md L164-L166
- **caveats**: 公位语汇为古代宗族叙事，不作现代家庭判断。
- **verified**: false

## TYR-11: 四金墓与借库/自库

- **source_chapter**: xia-lingshen
- **rule**: 下篇把辰戌丑未四墓、借库、自库纳入富贵贫乏的水法解释。
- **source_anchor**: fulltext.md L198-L200
- **caveats**: 仅保留为术语关系，不输出现实吉凶断语。
- **verified**: false

## TYR-12: 倒排父母与顺排父母

- **source_chapter**: xia-lingshen
- **rule**: 文中以倒排父母为真龙，顺排父母到子息则退；注解进一步解释四龙折水顺逆。
- **source_anchor**: fulltext.md L238-L246
- **caveats**: 同篇存在顺逆并存之说，validation 必须标明待校勘与流派裁判。
- **verified**: false

## TYR-13: 收山出杀为玄空小五行相关诀

- **source_chapter**: xia-lingshen
- **rule**: 结尾把翻天倒地归玄空大卦，把收山出杀归为另一路诀法。
- **source_anchor**: fulltext.md L252-L254
- **caveats**: 仅作源流索引；具体操作由工具和流派规则裁判。
- **verified**: false

## TYR-14: 外编四经五行分阴阳

- **source_chapter**: waibian-jiuxing
- **rule**: 外编以乾丙乙与子寅辰等分属金，艮庚丁卯巳丑分属水，并以坤壬辛与午申戌、甲癸与亥酉未等分属木火，归为阴阳天地卦与四经五行。
- **source_anchor**: fulltext.md L256-L258
- **caveats**: 该分法需与内传、青囊系和三合/玄空不同版本互证；不得单独作为计算规则。
- **verified**: false

## TYR-15: 外编零正神口径

- **source_chapter**: waibian-jiuxing
- **rule**: 外编明确提出“正神上山，零神下水”，并以支神为正、干神为零解释山水分用。
- **source_anchor**: fulltext.md L260-L280
- **caveats**: 零正神为后世玄空争议术语，master skill 必须按所选流派裁判。
- **verified**: false

## TYR-16: 外编九星形势

- **source_chapter**: waibian-jiuxing
- **rule**: 外编将寻龙与星峰形势绑定，强调贪、巨、武、祿、文、廉、破、辅弼等九星各有形体、护送、关峡、穴法。
- **source_anchor**: fulltext.md L345-L457
- **caveats**: 此处偏形势派语汇，需与《撼龙经》《疑龙经》互证；不作现实勘测结论。
- **verified**: false
