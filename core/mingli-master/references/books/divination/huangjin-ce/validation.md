# validation: 黄金策

## Source Validation

| field | value |
|---|---|
| source_status | `complete_text` |
| source_url | `https://zh.wikisource.org/wiki/%E9%BB%84%E9%87%91%E7%AD%96` |
| manifest | `sources/manifests/huangjin-ce.yaml` |
| raw_source | `sources/raw/divination/huangjin-ce/wikisource_raw.txt` |
| raw_sha256 | `51843f473b7a7a7a6abdd6cfe0dd7905b01fbd38faef6d1184e3cc9b3bd1bf33` |
| normalized_source | `references/fulltext/divination/huangjin-ce/fulltext.md` |
| normalized_sha256 | `6a8569490397634b15c821116ebe21d9eff799c3b8c07c51179c4224a3362e77` |
| normalized_lines | 1759 |
| structural_units | 33 |
| chapter_coverage | 33 done / 0 partial / 0 pending / 0 skipped / 0 unavailable |

## D2 Gates

| gate | status | note |
|---|---|---|
| V0 completeness | pass | Wikisource raw acquired and normalized as a full single-page text. |
| V1 location | pass | Rules and quotes use `fulltext.md Lx` anchors. |
| V2 source fidelity | pass | Rules paraphrase local text only; no modern empirical claims added. |
| V3 operationality | pass | Rules require a formal six-line divination fact layer. |
| V4 lineage boundary | pass | Version notes preserve Liu Ji attribution uncertainty and 《卜筮正宗》 base statement. |
| V5 no calculation hallucination | pass | 起卦/装卦/纳甲/世应/旬空/六神/飞伏 all delegated to adapter. |

## Version And Layer Risks

- Wikisource 页头题刘基，并称“按《卜筮正宗》本，全文载录”；本 pack 只据此标记版本来源，不证明全书作者层。
- 正文中有 `注释:`、`註記:` 等明显后出解释层；rules 只抽正文可定位总纲与章节取法，注释层不作为原典规则。
- 《黄金策》在《卜筮正宗》《增删卜易》等书中被收录或引用时，可能存在编次与字句差异；后续可与影印本/CTP 锚点校对。
- 高风险章节包括病症、病体、医药、征战、词讼、避乱、逃亡、失脱、娼家；只作传统文本取象，不作现代医疗、法律、安全、现实指控。

## Integration Boundary

- 一线用途：六爻/纳甲短事占的分门规则索引。
- 对读用途：与 `huozhu-lin` 比较源流，与 `bushi-zhengzong`、`zengshan-buyi` 比较实务取法。
- 神煞用途：作为六爻内部神煞降权证据；不得迁移到八字、择日、六壬、紫微、风水。

## Remaining Work

1. 与《卜筮正宗》影印或可信校勘本逐段核对文字差异。
2. 若获得独立《黄金策》刊本，补版本差异表。
3. 将正文注释层拆出为 `commentary-notes.md`，避免后续误读为原典。
