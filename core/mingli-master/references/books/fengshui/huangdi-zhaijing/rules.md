# rules: 黄帝宅经

> 只收可定位、可操作、且不要求语言模型自由计算的规则。涉及排盘、起卦、罗盘、星度、历法者只写 adapter 要求。

| id | title | plain_language_rule | source_anchor | adapter_requirements | confidence |
|---|---|---|---|---|---|
| HDZJ-R001 | 宅为人本，先分阴阳 | 凡居处皆可按宅法论，但须先判阴阳宅、移来方向与二十四路，不可只按街向或单一坐向。 | fulltext.md L15-L20 | `tool.fengshui.site_profile` | source |
| HDZJ-R002 | 二十四路是宅法基本坐标 | 宅内按十干十二支四维分二十四路，乾震坎艮辰属阳，巽离坤兑戌属阴。 | fulltext.md L15-L20 | `tool.fengshui.luopan.degrees_to_24_mountains` | source |
| HDZJ-R003 | 阴阳往来一度为吉，重入为凶 | 阴阳往来合天道；再三四度重入被书中视作无气、无魂、无魄。 | fulltext.md L15-L20 | `movement_or_renovation_direction_history` | source |
| HDZJ-R004 | 修宅次第先刑祸后福德 | 先修刑祸、后修福德为吉；先修福德、后修刑祸为凶。 | fulltext.md L21-L21 | `renovation_sequence + direction_profile` | source |
| HDZJ-R005 | 五虚五实为阳宅形体初筛 | 宅大人少、门大内小、墙院不完等为虚；宅小人多、门小、墙院完全等为实。 | fulltext.md L15-L20 | `site_layout_profile` | source |
| HDZJ-R006 | 宅以形势为身体 | 宅体以形势、泉水、土地、草木、屋舍、门户合观，不以单一门向断全宅。 | fulltext.md L21-L25 | `site_shape_water_building_profile` | source |
| HDZJ-R007 | 月生气死气用于修造时机 | 每月生气/死气方不同；修月生气方则福来，犯死气方则有灾。 | fulltext.md L21-L27 | `tool.selection_or_fengshui.calendar_month_direction_profile` | source |
