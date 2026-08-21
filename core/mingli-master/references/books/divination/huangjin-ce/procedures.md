# procedures: 黄金策

## Required Fact Layer

在读取本 pack 进行判断前，必须已有完整六爻事实层：

| field | required | notes |
|---|---:|---|
| `calendar_normalization` | yes | 起卦时刻、时区、农历/干支、节气月界、日辰月建。 |
| `casting_method` | yes | 起卦方法；用户手工卦、铜钱卦、时间卦等须标明。 |
| `original_hexagram` | yes | 本卦。 |
| `changed_hexagram` | yes | 变卦；无动爻也须显式说明。 |
| `moving_lines` | yes | 动爻/交重。 |
| `shi_ying` | yes | 世应所在爻。 |
| `six_kin` | yes | 父母、兄弟、子孙、妻财、官鬼。 |
| `najia` | yes | 纳甲、地支、五行。 |
| `void` | yes | 旬空。 |
| `six_spirits` | yes | 青龙、朱雀、勾陈、螣蛇、白虎、玄武。 |
| `flying_hidden_spirits` | conditional | 伏神/飞神；若该盘无伏神，须显式说明。 |
| `selected_yongshen` | yes | 可由 adapter 或 rule-profile 给出候选；模型不得自由杜撰。 |

## Loading Procedure

1. **Classify the question.** 将用户问题映射到 `chapter-map.md` 的具体章节。若是求财/合作/回款，用 `求財`；婚恋正式短占用 `婚姻`；出行用 `出行`；行人/消息用 `行人`；法律纠纷用 `詞訟`。
2. **Confirm the fact layer.** 若缺少必填字段，停止并列出缺项；不要以农历日、时辰或普通日历锚点代替六爻盘。
3. **Choose the chapter and yongshen.** 读取对应章节在 `terms.md` 和 `rules.md` 的用神说明。章节没有明确规则时，只做 fulltext 上下文检索，不强行输出。
4. **Apply the general hierarchy.** 先看日辰/月建，再看世应，再看用神旺衰受伤，再看动变，再看空墓合冲，再看六神神煞旁证。
5. **Apply topic rules.** 按章节规则判断关键象：求财看财福兄鬼父；婚姻看阴阳世应财鬼；出行看父母行李、妻财盘缠、间爻路途；词讼看世应官父子孙。
6. **Preserve risk boundary.** 病、讼、逃亡、盗贼、兵灾等章节只能输出“传统文本如何取象”，不得替代医疗、法律、安全或现实调查。
7. **Return source-aware synthesis.** 输出需分清事实层、文本依据、综合判断、边界；若引文，优先用 `quote-index.md` 的短引。

## Stop Conditions

- 没有正式起卦事实层，却要求六爻结论。
- 只给出时间、农历、干支、神煞、卦名之一，缺少世应/六亲/动爻/日月等核心字段。
- 用户问八字、紫微、择日、六壬、风水神煞，却试图加载本 pack 的六爻神煞。
- 用户要求医疗诊断、法律定罪、现实失踪定位等现代事实结论。

## Adapter Contract

`mingli-master` 可接受的六爻 adapter 输出至少应包含：

```json
{
  "tool": "tool.divination.qiguagua",
  "calendar_normalization": {},
  "casting_method": "",
  "original_hexagram": "",
  "changed_hexagram": "",
  "moving_lines": [],
  "shi_ying": {},
  "six_kin": {},
  "najia": {},
  "void": {},
  "six_spirits": {},
  "flying_hidden_spirits": {},
  "selected_yongshen": []
}
```

若 adapter 输出缺字段，先补事实层，再读《黄金策》。
