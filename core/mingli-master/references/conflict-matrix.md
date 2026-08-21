# Conflict Matrix

Use this file when two systems, books, adapters, or schools disagree. Do not average contradictions away. Preserve the disagreement, name the layer, and lower the confidence bucket unless historical calibration for this exact conflict type says otherwise.

## Conflict Rules

| Conflict | First response | Confidence policy |
|---|---|---|
| Adapter outputs disagree | Stop before interpretation. Compare input, timezone/location, calendar rule, true-solar-time policy, adapter version, and rule profile. | No final reading until one fact layer is selected or the disagreement is reported as unresolved. |
| Bazi 调候 vs 格局 vs 气势 | Declare the lens. Use `qiongtong-baojian` for 调候, `ziping-zhenquan` for 格局, `ditiansui-chanwei` for 气势/通关; do not mix as if one rule. | If lenses point to the same conclusion, confidence can rise. If they diverge, keep `textual_mixed`. |
| Bazi vs Ziwei | Treat them as independent natal systems only after both fact layers are complete. | Agreement is corroboration, not proof. Disagreement lowers interpretation confidence. |
| Divination vs natal chart | Short-event divination answers the immediate question; natal chart supplies background tendency. | For tactical yes/no timing, divination usually has priority if its fact layer is complete. |
| Selection vs personal bazi | Selection calendar facts decide the candidate-date layer; personal bazi adds constraints and avoidances. | Do not recommend a day if either the selection fact layer or personal constraint layer is incomplete. |
| Fengshui 形峦 vs 理气 | Keep visible form, compass/period, and school variables separate. | Do not let a strong 理气 pattern override missing layout facts. |
| 阴宅 vs 阳宅 | Treat as different use cases. | Never transfer burial-land rules into home/office advice without explicitly marking the analogy. |
| Original text vs commentary vs modern school | Original text is evidence; commentary is interpretation; modern school is lineage or usage note. | Modern lineage cannot override missing original-text support. |

## Output Pattern

```text
Conflict layer: fact | source | school | interpretation | calibration
Side A: source/tool/profile and claim
Side B: source/tool/profile and claim
Decision: choose A | choose B | preserve disagreement | stop pending fact-layer repair
Confidence effect: unchanged | lowered to textual_mixed | unscorable
```

## Practical Default

If the user wants a direct answer, give the direct traditional indication only after the selected fact layer and source route are explicit. If the conflict changes the recommendation, state it in one sentence under boundary notes instead of hiding it.
