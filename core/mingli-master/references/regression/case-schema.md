# Blind Case Schema

Known-answer cases use separate files throughout prediction and scoring.

## Input

An input contains the system, anonymized subject facts, exact question, answer
options where applicable, source identity, and split. It must not contain an
answer key, observed result, later feedback, or a field that reveals them.

## Outcome

An outcome uses the same `case_id` and contains the published or later observed
answer plus provenance quality. Only the scoring process may open this file.

## Split

Cases sharing one person, chart, event, article, or source thread stay in one
split. This prevents paraphrases and follow-up questions from leaking the same
answer across development and evaluation sets.

## Prediction

The prediction process writes a digest-bound immutable record before the
outcome path is accepted. Re-running an identical prediction is idempotent;
changing its verdict or evidence raises a conflict.

## Metrics

Report directional accuracy, coverage, abstention, unsupported-claim rate, and
chart correctness separately. Do not calculate Brier score until confidence is
expressed as a calibrated numeric probability rather than a verbal bucket.
