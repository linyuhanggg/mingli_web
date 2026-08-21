# rules: 阳宅十书

> 只收可定位、可操作、且不要求语言模型自由计算的规则。涉及罗盘、历法、择日、福元、游年、门尺、图形符法者只写 adapter 要求。

| id | title | plain_language_rule | source_anchor | adapter_requirements | confidence |
|---|---|---|---|---|---|
| YZS-R001 | 阳宅先看外形大局 | 宅外来龙、明堂、山水道路是第一层；外形大局不善时，不能只凭内部布局判全吉。 | fulltext.md L25-L36 | `tool.fengshui.site_profile`; `tool.fengshui.terrain_context` | source |
| YZS-R002 | 冲口与不洁/冲煞场所列为禁居 | 当冲口、寺庙、祠社窑冶官衙、故军营战地、正当水流、山脊冲、大城门口、狱门、百川口等，书中列为不居。 | fulltext.md L41-L44 | `site_surroundings_profile`; `modern_safety_and_legal_context` | source |
| YZS-R003 | 门前水塘、屋箭、井门、路桥冲门须入外形风险 | 门前新塘、屋箭、井当大门、水路桥梁四面交冲等被列为阳宅外形忌象，须作为环境风险项而不是单一断语。 | fulltext.md L56-L89 | `site_shape_water_road_profile`; `door_axis_profile` | source |
| YZS-R004 | 福元错配会改写阳宅判断 | 书中认为福元一错，东四修西、西四修东，则外形内形俱吉也无用；因此八宅类判断必须先有生年/福元事实层。 | fulltext.md L767-L774 | `tool.fengshui.fuyuan_or_eight_mansion`; `birth_year_or_profile` | source |
| YZS-R005 | 东四位/西四位分组必须保留 | 东四位生人以震巽坎离为吉方系统，西四位生人以乾坤艮兑为吉方系统；不得把两组平均化。 | fulltext.md L1039-L1041, L1132-L1134 | `tool.fengshui.eight_mansion_profile` | source |
| YZS-R006 | 大门只是一节，分院隔门要重起 | 不能概以大门定全宅吉凶；宅中有墙隔断并开门时，游年与穿宫应从该门重起。 | fulltext.md L1582-L1594 | `layout_graph`; `door_sequence`; `courtyard_or_room_partition_profile` | source |
| YZS-R007 | 大游年九星先分星名与吉凶 | 生气贪狼、延年武曲、天乙巨门为吉星核心；祸害禄存、六煞文曲、五鬼廉贞、绝命破军等为凶星系统。 | fulltext.md L1247-L1255 | `tool.fengshui.eight_mansion_stars` | source |
| YZS-R008 | 方位与层数都要看，不可只看门向 | 大游年主方位，也主层数；方位虽吉但层数高下错配，吉也可能变凶。 | fulltext.md L1577-L1581 | `layout_floor_or_depth_profile`; `eight_mansion_star_by_layer` | source |
| YZS-R009 | 吉星宜高大，凶星宜低小 | 穿宫层数中，吉星位置宜高大，凶星位置宜低小；但吉星落凶方时仍不可简单高大化。 | fulltext.md L1674-L1680 | `room_height_mass_profile`; `star_direction_conflict_profile` | source |
| YZS-R010 | 开门修门先看福元旺合吉星，再看形煞与择日 | 安门专主福元旺合吉星，同时要避直冲尖射、砂水斜割、恶石、神庙等乘杀入门，并须慎选月日。 | fulltext.md L1766-L1784 | `tool.fengshui.door_profile`; `tool.selection.calendar_profile` | source |
| YZS-R011 | 修门择日禁忌不可手推 | 天德月德满成开日、门光星、天牢黑道、三煞、胎神等需要完整择日事实层；不能只凭文本直接挑日期。 | fulltext.md L1772-L1823 | `mingli-master.selection.v1`（经唯一生产事务入口调用）; `door_work_use_case` | source |
| YZS-R012 | 放水必须辨九星水法与阴阳山水 | 书中称阳宅阴宅俱以水法取效，水法一差则前法俱坏；须分九星水来去、阴阳山水、天干/地支水。 | fulltext.md L1881-L1935 | `tool.fengshui.water_flow_profile`; `tool.fengshui.luopan.degrees_to_24_mountains` | source |
| YZS-R013 | 四路黄泉分杀人与救人 | 辰戌丑未见破军水为凶，见巨门水为救；必须先有二十四山与水路事实层。 | fulltext.md L1937-L1945 | `water_star_profile`; `twenty_four_mountains_profile` | source |
| YZS-R014 | 宅内形要把堂廊天井门路厨灶同看 | 宅内形涉及堂屋、廊屋、天井、门路、龙虎、碓磨、厨灶等，不能只看一个房间或单一门向。 | fulltext.md L2015-L2078 | `interior_layout_profile`; `functional_room_profile` | source |
| YZS-R015 | 选择第九先起命前五神 | 修造择日线中，书中明确先起命前五神，再进入九宫建宅、行年建宅等；必须走择日 adapter。 | fulltext.md L2197-L2244 | `tool.selection.calendar_profile`; `birth_year_or_mingqian_wushen_profile` | source |
| YZS-R016 | 太阴太阳过宫仅作择日事实层字段 | 太阴/太阳过宫图局属于选择第九图表信息，不得由语言模型从图像或记忆手推。 | fulltext.md L2593-L2601 | `tool.selection.taiyin_taiyang_guogong` | source |
| YZS-R017 | 符镇不进入一线可执行规则 | 论符镇含大量符图；本 pack 可说明其在书中用于“宅兆既凶，又岁月难待”的传统语境，但不转写符形、不指导现实执行。 | fulltext.md L2616-L3015 | `image_asset_review_required`; `no_llm_symbolic_transcription` | source |
| YZS-R018 | 地利不凌驾命运与德行层 | 书末问答称地利仅足以挽回天时之半，宅法不可执定；回答时需把阳宅读法作为传统倾向而非现实保证。 | fulltext.md L3007-L3015 | `boundary_note_required` | source |
