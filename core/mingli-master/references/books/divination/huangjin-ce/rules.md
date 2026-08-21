# rules: 黄金策

> 只收可定位、可操作、且不要求语言模型自由计算的规则。涉及起卦、装卦、纳甲、世应、六亲、旬空、飞伏、六神、应期者只写 adapter 要求。

## HJC-M001 动始变终

- **plain_language_rule**: 占卦以动爻为变化之始、变卦为变化之终。
- **source_chapter**: 总断千金赋
- **adapter_requirements**: 存在动爻与变卦的六爻盘
- **caveats**: 仅作动变方法，不授权具体事项吉凶。
- **verification_status**: verified

| id | title | plain_language_rule | source_anchor | adapter_requirements | confidence |
|---|---|---|---|---|---|
| HJC-R001 | 日辰月建是六爻总权重 | 断卦先看日辰、月建对用神、世应、动爻的生克冲合与旺衰；不能只凭卦名或单个神煞下结论。 | fulltext.md L26-L27 | `calendar_normalization + liuyao_plate.day_month_strength` | source |
| HJC-R002 | 世应分己他 | 世为自己/本方，应为对方/他人；世应相合相生利互动，世应受伤、俱空或冲克则关系不稳。 | fulltext.md L30-L36 | `liuyao_plate.shi_ying_relations` | source |
| HJC-R003 | 动变分始终 | 动爻主事情发动，变爻主后势或结果；动变比和、进退、回头克等决定进展。 | fulltext.md L30-L31, L72-L73 | `liuyao_plate.moving_lines + changed_lines` | source |
| HJC-R004 | 用神有气为成事底线 | 用神有气且无明显损伤，所问有成；主象徒存但被伤，谋事不遂。 | fulltext.md L38-L39 | `selected_yongshen + strength + damage_flags` | source |
| HJC-R005 | 伤需救，空合冲墓要看条件 | 用神受伤须有救应；空、合、冲、墓、旺衰不能孤立解释，要看是否逢冲可用、合破无功、墓冲而发。 | fulltext.md L40-L56 | `void_status + combinations + clashes + tomb + rescue_flags` | source |
| HJC-R006 | 神煞低于生克制化 | 吉凶神煞、六神取象只能作旁证；核心判断仍以生克制化、用神旺衰和世应动变为主。 | fulltext.md L114-L121 | `shensha_index + liuyao_plate.core_relations` | source |
| HJC-R007 | 天时先取父财，不凭水火 | 天时占以父母主雨、妻财主晴为主要取象，再看子孙日月、兄弟风云、官爻雷电及四季五行。 | fulltext.md L132-L140 | `question_class=weather + liuyao_plate.six_kin + season_profile` | source |
| HJC-R008 | 婚姻以阴阳世应财鬼为纲 | 婚姻先看阴阳、六合六冲、世应合冲生克，再看财鬼是否空亡刑害。 | fulltext.md L407-L431 | `question_class=marriage + shi_ying + wife_wealth + officer_ghost` | source |
| HJC-R009 | 求财以财福为主，兼看兄鬼父 | 求财先看财爻与子孙；财旺福兴利，财空福绝不利；父兄皆动、兄鬼克世多阻。 | fulltext.md L962-L982 | `question_class=finance + wealth_line + child_line + sibling_officer_relations` | source |
| HJC-R010 | 求财应区别财来就我与我去寻财 | 财来生世或就世较易，我去寻财、世持动兄、财被日伤则难；应期看生衰旺合。 | fulltext.md L974-L994 | `wealth_to_self_relation + day_damage + timing_markers` | source |
| HJC-R011 | 家宅分内外与门路 | 家宅以卦内为宅、卦外为人，合为门、冲为路，再看宅、门、世应、日月之间的生克冲合。 | fulltext.md L1017-L1021 | `question_class=house + inner_outer + door_road_symbols` | source |
| HJC-R012 | 家宅财鬼并看兴衰 | 宅无破而逢生则宅兴财旺；有财无鬼多耗散，有鬼无财多灾生，有人制鬼则鬼动无妨。 | fulltext.md L1039-L1045 | `house_domain_profile + wealth_ghost_control` | source |
| HJC-R013 | 求名仕宦父官为主 | 求名看父母文书与官鬼名位；父官旺相有助，财动、福动、兄弟竞发常成阻。 | fulltext.md L879-L895 | `question_class=exam_or_office + parent_line + officer_line + competitors` | source |
| HJC-R014 | 词讼须详世应与官父 | 词讼先看世应输赢，世宜旺生、应宜休囚；官鬼为问官，父母为文书案卷，子孙主和解消散。 | fulltext.md L1318-L1353 | `question_class=legal_dispute + shi_ying + officer_parent_child_lines` | source |
| HJC-R015 | 出行看行李盘缠世应间爻 | 出行以父母为行李、妻财为盘缠，世看自身承受，应看谋成，间爻看路途同伴。 | fulltext.md L1577-L1604 | `question_class=travel + parent_line + wealth_line + shi_ying + interval_lines` | source |
| HJC-R016 | 行人归期寻主象 | 行人问归期，先找主象/用爻；用爻动则身已动，安静则未思归，生克合冲伏藏决定迟速与阻滞。 | fulltext.md L1617-L1644 | `question_class=missing_or_traveler + selected_yongshen + movement + hidden_visible` | source |
| HJC-R017 | 病症医药章节只作传统取象 | 病症、病体、医药章节可记录六亲、五行、卦宫、六神如何取象，但不得输出为现代诊断、疗法或用药建议。 | fulltext.md L590-L714 | `health_topic_gate + liuyao_plate_if_user_explicitly_casts` | source_boundary |

## Rule Use Boundary

- 若缺少 `calendar_normalization`、本卦/变卦、动爻、世应、六亲、纳甲、日辰、月建、旬空、六神、飞伏等事实层，停止解释。
- 本 pack 适合回答“这个六爻问题该读哪一章、哪些爻/关系最关键”，不负责起卦和装卦。
- 神煞相关条目只能在六爻事实层内使用；若用户问八字神煞或择日神煞，必须改走对应系统。
