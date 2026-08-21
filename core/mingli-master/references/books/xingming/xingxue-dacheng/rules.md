# rules: 星学大成

> 只收可定位、可操作、且不要求语言模型自由计算的规则。涉及排盘、起卦、罗盘、星度、历法者只写 adapter 要求。

| id | title | plain_language_rule | source_anchor | adapter_requirements | confidence |
|---|---|---|---|---|---|
| XXDC-M01 | 十二宫事实次序 | 以宫分依次列命、财帛、兄弟、田宅、男女、奴仆、妻妾、疾厄、迁移、官禄、福德、相貌十二宫；仅用于核对宫位事实。 | fulltext.md L921 | `xingming_chart.houses` | source |
| XXDC-R001 | 星命先立十二宫三盘 | 先定十二宫，再分天盘、地盘、人盘；人盘重四柱填实与空虚。 | fulltext.md L53-L70 | `tool.xingming.bindisk.full_chart` | source |
| XXDC-R002 | 星度与宫位必须工具化 | 周天度数、十一曜行度、二十八宿度数等只可作为古籍规则源，实际星位由 adapter 给出。 | fulltext.md L53-L101 | `tool.xingming.astronomy_ephemeris` | source |
| XXDC-R003 | 禄主星看七强、照命、顺行、庙旺 | 天元禄主宜在七强、照命、顺行、庙旺、长生临官帝旺宫；弱陷留逆则福不纯。 | fulltext.md L111-L120 | `xingming_chart.star_strength_profile` | source |
| XXDC-R004 | 福财星合看福德财帛迁移 | 福财星照福德为上，身命次之，男女宫亦可为上吉；陷弱伏逆须降权。 | fulltext.md L121-L135 | `xingming_chart.fude_caibo_profile` | source |
| XXDC-R005 | 观星节要先看身命二主 | 先以身命二主落宫，按空实、强弱、夹拱、冲驀判人品出处高下，再看福禄恩官田财。 | fulltext.md L1037-L1054 | `xingming_chart.body_life_lords` | source |
| XXDC-R006 | 十二宫足以尽一生事项 | 命为主、财为养命源、妻妾对冲命宫、疾厄迁移官禄福德相貌各有次序。 | fulltext.md L1033-L1095 | `xingming_chart.house_meanings` | source |
| XXDC-R007 | 空实夹拱是琴堂法核心 | 吉星坐实、三方左右夹拱有力为贵；煞星的刃夹拱为祸，空实冲合要分吉凶星。 | fulltext.md L1042-L1207 | `xingming_chart.empty_solid_clamp_profile` | source |
| XXDC-R008 | 迟留伏逆需按星曜状态判 | 迟、留、伏、逆分别影响有用星和煞星力量；不可用静态星度替代动态状态。 | fulltext.md L1095-L1207 | `tool.xingming.planet_motion_state` | source |
