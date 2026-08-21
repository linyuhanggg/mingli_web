# 相法 (physiognomy)

## Packs

| pack | title | best for | do not use for | caveat |
|---|---|---|---|---|
| `physiognomy/bingjian` | 冰鉴 | 神骨视角的"内在精神"分类（澄清到底 / 尖巧喜淫 / 别才深思 / 隐流败器）; 刚柔视角的内外刚柔（五行外刚柔 + 喜怒伏跳深浅之内刚柔）; 情态四分（弱态 / 狂态 / 疏懒态 / 周旋态）的人物气质画像 | 命盘事实计算（不与 bazi/ziwei/xingming 同层）; 富贵贫贱铁口判断（仅作旁证，不作硬判）; 健康、寿命、子嗣、女命断语（走 safety-redlines） | - Batch D1 完成全书覆盖型文件组创建。源文件：references/fulltext/physiognomy/bingjian/fulltext.md。 - source_status 维持 partial：清刊本影印未对校。 - 本书全文短，rules.md 抽取覆盖率高；但每条 rules 必须带 caveats "仅作旁证参考，不参与命盘... |
| `physiognomy/liuzhuang-xiangfa` | 柳庄相法 | 明代相法中骨相、五官、五岳、六府、气色、形局的原典参考; 与《神相全编》《麻衣神相》对读，区分相法术语层与后世汇编层; 作为相法 skill 的 source-layer primary 证据，不作现实人格/健康判断 | 医疗、寿夭、生育、刑伤、贫贱、婚姻确定判断; 对真人外貌作价值评判或歧视性归因; 手相/面相现代咨询的唯一依据 | CTP 行表 618 行已抽取为 normalized fulltext；chapter-map 按 136 个机器识别标题覆盖。 quote-index 短引均应 exact-ish 命中 fulltext。 |
| `physiognomy/mayi-shenxiang` | 麻衣神相 | 麻衣系相法的五官、十二宫、骨肉、四肢、气色、石室神异赋、金锁赋术语索引; 与《神相全编》《柳庄相法》对读，区分相法原典/汇编/现代附益; 作为相法史与术语解释的 source-layer 证据 | 医疗、寿夭、刑伤、贫贱、婚配、生育等现实硬断; 对真人外貌、身体特征作价值评判或歧视性归因; 将第 1 页或第 12-14 页现代附益当作古籍原文 | 已完整抓取 mayixf01-mayixf14 并生成 normalized fulltext；reference pack 覆盖 14 个网页单元。 短引均取自 normalized source；现代附益层单独标注，不进入一线规则。 |
| `physiognomy/shenxiang-quanbian` | 神相全编 | 全身部位、五官、五岳四渎、五星六曜、六府三才三停的传统相法术语溯源; 形神气声、骨肉、气色等相术总纲的原文证据检索; 神异赋、岩电道人神眼经、麻衣金锁赋、银匙歌、袁柳庄诸赋等长赋篇名与短引定位 | 命盘事实计算; 对真人照片、视频或外貌作判断; 富贵贫贱、寿夭、灾厄、婚育、子嗣、疾病的硬断 | D2 修订完成：source_lines=5109，structural_units=410，chapter-map 全部 done，quote-index 每单元一条精确短引。source_risk 保留：当前源为古今图书集成辑录本，不是独立十二卷本。 |

## Runtime use

This card is capability and source metadata for selecting the transaction
system before `prepare`. During a live reading, use only the bounded evidence
returned by the transaction; do not load packs or run a separate corpus search.

The executable route is the dedicated `observation_driven_ready` provider. A
vision-capable caller may transcribe neutral visible observations with semantic
region, capture quality, occlusion, and uncertainty. The provider itself never
receives raw media, performs vision, identifies a person, fills an unseen
region, or treats different captures/lighting as equivalent. Private subject,
asset, capture, hash, and region-anchor provenance remains in the transaction
record and cannot enter the public basis, intake question, or answer.

Live evidence is limited to exact rules activated by the provider from
《柳庄相法》《神相全编》and the admitted historical transcription layer of
《麻衣神相》. Compilation and mixed-transcription layers do not count as
independent votes; disagreements and later accretions remain explicit.
`physiognomy/bingjian` is not an active provider source. Even an explicit 相法
request authorizes only visible facts, uncertainty, terminology, method, and
edition comparison—not a person-specific wealth, personality, health,
lifespan, identity, protected-attribute, or future verdict.
