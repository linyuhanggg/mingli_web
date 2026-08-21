# rules: 火珠林

> 只收可定位、可操作、且不要求语言模型自由计算的规则。涉及排盘、起卦、罗盘、星度、历法者只写 adapter 要求。

## HZL-M001 先看世应

- **plain_language_rule**: 六爻审卦先核世应位置，再进入后续深浅判断。
- **source_chapter**: 断易总法
- **adapter_requirements**: 已排出世应的六爻盘
- **caveats**: 仅作读盘顺序，不授权吉凶结论。
- **verification_status**: verified

| id | title | plain_language_rule | source_anchor | adapter_requirements | confidence |
|---|---|---|---|---|---|
| HZL-R001 | 六爻断事先分公私财官 | 公用取官鬼，私用取妻财；官用以父母辅，财用以子孙辅。 | fulltext.md L91-L104 | `question_classification + liuyao_plate` | source |
| HZL-R002 | 财官须看旺相与辅体 | 财官旺相、有辅体发动或生世为可用；休囚、克破、无辅则力薄。 | fulltext.md L40-L51 | `liuyao_plate.with_season_strength` | source |
| HZL-R003 | 乱动卦取旺爻并看生世 | 乱动时先看世上旁爻、世下亲爻，再以最旺或发动生世之爻为用。 | fulltext.md L52-L77 | `liuyao_plate.moving_lines + strength` | source |
| HZL-R004 | 世应动爻克辅为忌 | 财官持世虽可许，但应爻或动爻克所用辅爻则事难成。 | fulltext.md L78-L90 | `liuyao_plate.shi_ying_moving_relations` | source |
| HZL-R005 | 出现主久，伏藏主暂 | 财官出现旺相宜久远；伏藏有气虽可取，多利短时或暂成。 | fulltext.md L105-L118 | `liuyao_plate.visible_hidden_spirits` | source |
| HZL-R006 | 家宅以财福为主 | 家宅占专看财、子孙与内三爻宅象，再合青龙、龙德、刑冲克制。 | fulltext.md L724-L736 | `liuyao_plate.house_domain_profile` | source |
| HZL-R007 | 起造迁移以财静人安为纲 | 起造迁移喜子孙、财爻旺相持世；忌官鬼、父母、妻、子、兄弟独发扰宅。 | fulltext.md L748-L760 | `liuyao_plate.house_move_domain` | source |
| HZL-R008 | 阳宅爻位需分内外 | 内卦二爻为宅，外卦六爻看动；宅下伏鬼、父空、财动等均有特定宅象。 | fulltext.md L761-L770 | `liuyao_plate.house_line_symbols` | source |
