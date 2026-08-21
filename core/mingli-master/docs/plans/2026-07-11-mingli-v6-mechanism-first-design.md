# Mingli v6 Mechanism-First Design

## Problem

The deployed daily-fortune v5 path is internally consistent but semantically wrong.

- It maps ten gods to behavior lenses and then to fixed life domains such as communication and documents.
- Its writing brief supplies public vocabulary, human-experience phrases, and action verbs.
- Its public gate requires a whole-day contour, multiple phases, a human-feeling sentence, and a behavior-changing action even when the chart supports none of those details.
- Its evidence retriever cannot read the nested fortune fact schema correctly. For a 己土日主 born in 戌月 it selected 三春甲木, 七月丙火, and a longevity rule instead of 三秋己土 and 岁运合参.
- The main skill has grown from a lightweight router into a large prompt and policy document. Formal live readings can consume hundreds of thousands of prompt tokens through repeated skill loads, JSON dumps, source reads, and gate repairs.

The result is a bad inversion: labels choose the answer first, and classical books are asked to support it afterward.

## Chosen Architecture

### Preserve

- The 54 local D2-ready reference packs and their full local source corpus.
- Deterministic Bazi and Da Liu Ren adapters.
- User-provided chart validation for systems without an installed calculator.
- Source identity, applicability, conflict, and hash checks.
- The hash-bound final public copy.

### Retire

- Daily-fortune v5 life-domain hypotheses.
- Ten-god-to-scene mappings.
- Public vocabulary and action-vocabulary lists.
- Mandatory morning/afternoon/evening prose.
- Mandatory human-experience and action sentences.
- Style gates that attempt to write the answer by keyword.
- BM25 as the authority for whether a classical rule applies.
- Subagent delegation, repeated skill loads, and duplicate complete JSON output during a reading.

## Runtime Lanes

### Quick

For today/tomorrow fortune and compact follow-ups.

1. Calculate natal facts, active luck, target year/month/day, lunar date, ten gods, hidden stems, branch relations, and Tiaohou anchors.
2. Compile a deterministic mechanism stack.
3. Resolve only applicable classical rules.
4. Give the model one compact analysis bundle.
5. Generate one natural answer and run a fact/source-only public check.

### Formal

For complete Bazi, compatibility, Da Liu Ren, and other full readings.

Use the same fact -> mechanism -> applicable rules -> conflict adjudication -> natural synthesis flow, with a larger evidence allowance where the question requires it.

### Research

For book history, original text, version, and school questions.

Skip personal chart calculation and load the relevant reference-pack layers or fulltext context directly.

## Mechanism Stack

The near-time adapter must emit facts and mechanisms, not prose hints.

- natal baseline: day master, month command, season, element inventory, hidden stems, Tiaohou markers;
- active layers: major luck, year, month, day, and optional queried hours;
- each layer's stem ten god and branch relations to the natal four branches;
- same-branch, clash, combination, harm, punishment, and break relations;
- repeated or competing mechanisms, kept as dependent evidence rather than vote counts;
- explicit uncertainty where favorable/unfavorable use cannot be resolved deterministically.

The model may interpret these mechanisms, but the adapter must never emit messages, files, payments, relationships, vehicles, body symptoms, or other life scenes.

## Classical Rule Resolution

Applicability is a hard filter before ranking.

1. Filter by system and question type.
2. Filter Bazi Tiaohou by natal day master and natal solar-term month group.
3. Filter timing rules to 大运/岁运/流年/流日 layers.
4. Exclude unrelated high-risk topics such as longevity unless the user asks for them.
5. Use BM25 only to rank records that already passed applicability.

For a 己土日主 born in 戌月, Qiongtong evidence must resolve to 三秋己土. 三春甲木 and 七月丙火 are ineligible regardless of semantic score.

## Analysis Bundle

One compiler produces the only context used for language synthesis:

- compact public time/chart basis;
- deterministic mechanism stack;
- applicable rule IDs and short source anchors;
- source conflicts and unresolved questions;
- unsupported factual claims;
- no sentence templates, public vocabulary, or suggested scenes.

Complete source books stay local. Fulltext is opened only when a selected rule needs surrounding context or two sources conflict.

## Public Verification

The public gate verifies truth boundaries, not prose style.

- exact tag and time/chart basis;
- no contradiction of calculated pillars, luck cycle, target date, or named relations;
- at least one decisive mechanism from the current bundle before a formal conclusion;
- no specific event, amount, time, or life domain without user context or a supporting fact/rule;
- no private tool or audit report;
- hash-bound canonical public copy.

It does not require phases, feelings, an action, a score, headings, or a fixed sentence order.

## Token And Tool Budgets

- Router `SKILL.md`: target at most 12 KB.
- Quick-lane added context: target at most 8,000 tokens.
- Formal Bazi added context: target at most 15,000 tokens.
- Complex Da Liu Ren added context: target at most 20,000 tokens.
- Quick lane: at most five tool calls.
- Formal lane: at most eight tool calls unless the user explicitly requests source research.
- No subagents, repeated `skill_view`, or repeated full JSON dumps.

The budgets cover skill-specific added context, not the host model's fixed system prompt.

## Release Safety

- Keep the current runtime unchanged while v6 is built on `rebuild/v6-mechanism-first`.
- Preserve the current production commit as a rollback point.
- Use real historical prompts as a champion/challenger suite.
- Record chart correctness, source applicability, unsupported claims, useful specificity, repetition, tool calls, prompt bytes, and latency.
- Do not deploy unless v6 wins the daily-fortune cases, preserves Bazi/Liuren correctness, and stays within budget.
- Sync the source skill to Codex and both Hermes profiles only after explicit final verification.

## Acceptance Cases

- A broad `算下今天运势` answer names the actual target day and decisive natal/transit mechanisms, without messages/files or a forced three-phase story.
- A 己土戌月 fortune retrieves 三秋己土 and 岁运 rules, never 三春甲木, 七月丙火, or longevity rules.
- A domain-specific question may discuss that domain because the user selected it, not because a ten-god map selected it.
- A complete Bazi screenshot still requires executable chart validation.
- A Da Liu Ren reading still displays the complete lesson and uses all required classical packs.
- Missing Qimen/Ziwei/etc. calculators still stop rather than hand-calculate.
- The final answer remains natural and hash-bound.
