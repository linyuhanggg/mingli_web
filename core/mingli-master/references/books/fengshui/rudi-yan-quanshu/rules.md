# rules: 入地眼全书

> 只收可定位、可操作、且不要求语言模型自由计算的规则。涉及排盘、起卦、罗盘、星度、历法者只写 adapter 要求。

| id | title | plain_language_rule | source_anchor | adapter_requirements | confidence |
|---|---|---|---|---|---|
| RDY-R001 | 巒頭先于理气 | 先熟看巒頭，再细玩理气；舍巒頭而重理气会导致登山茫然。 | fulltext.md L21-L31 | `terrain_profile + compass_profile` | source |
| RDY-R002 | 龙以少祖与父母山为近切 | 寻龙须辨祖宗；去穴近者关祸福近，少祖、父母、入首是重点。 | fulltext.md L167-L177 | `terrain_lineage_profile` | source |
| RDY-R003 | 砂水有情处方为龙 | 水来合处为面，砂头向内为面；砂水有情处是龙，无情处非龙。 | fulltext.md L167-L177 | `terrain_sand_water_affection_profile` | source |
| RDY-R004 | 形象水法优先 | 水法总以形象为第一；斜飞直冲虽合理气吉方，仍须避。 | fulltext.md L205-L213 | `water_shape_profile + luopan_profile` | source |
| RDY-R005 | 龙为根本，水为用 | 寻龙立穴水为先，但龙为根本水为用，二者不可偏废。 | fulltext.md L213-L219 | `dragon_water_combined_profile` | source |
| RDY-R006 | 单清过脉优先 | 多处龙法强调单清过脉、地局端正、砂水全备；兼带煞气须详辨。 | fulltext.md L33-L166 | `terrain_line_purity_profile` | source |
| RDY-R007 | 阳宅需门路灶宫星合看 | 卷十专论阳宅门路灶与宫星生克，不能只看门或灶单项。 | fulltext.md L231-L255 | `yangzhai_layout_profile` | source |
