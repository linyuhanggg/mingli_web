# rules: 青囊奥语

> 本 pack 只把短篇口诀转成可追溯的判断约束和 adapter 需求；不允许语言模型手算玄空、挨星、二十四山或水法。

| id | title | plain_language_rule | source_anchor | adapter_requirements | confidence |
|---|---|---|---|---|---|
| QNA-R001 | 二十四山分组必须有流派表 | 坤壬乙、艮丙辛、巽辰亥、甲癸申等星名分组不可凭记忆套用，必须绑定具体青囊/玄空流派表。 | fulltext.md L11-L12 | `tool.fengshui.qingnang_star_profile`; `tool.fengshui.luopan.degrees_to_24_mountains` | source |
| QNA-R002 | 雌雄玄空要合山水读 | 书中连续说雌雄、山水、玄空；理气判断不得只看坐山，须同时给山、水、向、水口。 | fulltext.md L13-L16 | `site_mountain_water_profile`; `xuan_kong_school_profile` | source |
| QNA-R003 | 颠倒顺逆会改变吉凶 | 二十四山的顺逆、颠倒是珠宝/火坑差异来源，必须由 adapter 明确顺逆口径。 | fulltext.md L17-L18 | `xuan_kong_directional_sequence`; `school_version` | source |
| QNA-R004 | 十义缺一不成真情 | 龙身行止、来脉明堂、城门、天心十道、流神来去等十项须合观；缺关键项时不能强断。 | fulltext.md L19-L23 | `terrain_profile`; `mingtang_profile`; `water_flow_profile`; `tianxin_axis_profile` | source |
| QNA-R005 | 向放水须辨生旺休囚 | 向中放水是否吉，取决于生旺休囚，须由水法/元运/二十四山事实层给出。 | fulltext.md L27-L31 | `tool.fengshui.water_life_cycle_profile`; `period_or_school_context` | source |
| QNA-R006 | 出入水有进退旺三类 | 从外出入名进，从内生出名退，出入克入名旺；但方向和克入关系必须由工具判定。 | fulltext.md L32-L34 | `water_in_out_profile`; `five_phase_relation_profile` | source |
| QNA-R007 | 龙歇脉寒不可轻易被旁山救助抵消 | 若脉息不生旺、龙歇脉寒，书中说他山救助亦空劳；要把龙脉事实层作为硬前提。 | fulltext.md L35-L36 | `dragon_vein_vitality_profile`; `supporting_mountain_profile` | source |
| QNA-R008 | 本篇作源头证据，不作单独 oracle | 篇末强调再辨星辰、真微妙；实际输出须与青囊序/天玉/都天/地理辨正和现场事实合读。 | fulltext.md L37-L38 | `source_crosscheck_required` | source |
