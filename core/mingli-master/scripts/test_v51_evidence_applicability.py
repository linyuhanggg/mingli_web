"""Regressions for applicability-first classical evidence retrieval."""

from __future__ import annotations

import importlib
import hashlib
import json
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import reading_evidence_bundle
import reading_source_plan
import build_evidence_index
import generate_classical_evidence_bindings
from reading_engine.contracts import CalculationResult, ReadingRequest
from reading_engine.evidence_rules import EvidenceRule
from reading_engine.fact_index import build_fact_index
from reading_engine.providers import (
    BaziProvider,
    LiurenProvider,
    MeihuaProvider,
    _adapter_evidence_goal,
)


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "references" / "index" / "evidence-rules.jsonl"
READING_ID = "e" * 32


def _fresh_evidence_rules() -> tuple[EvidenceRule, ...]:
    records = build_evidence_index.compile_evidence_rules(
        root=ROOT, enforce_classical_bindings=False
    )
    bindings = generate_classical_evidence_bindings.load_committed()["bindings"]
    for record in records:
        binding = bindings.get(record["rule_id"])
        signature = build_evidence_index.canonical_predicate_signature(
            record["required_fact_predicates"],
            record["excluded_fact_predicates"],
        )
        record_digest = build_evidence_index.canonical_rule_record_digest(record)
        if binding is None:
            record.update(
                runtime_active=False,
                classical_binding_status="inactive_unscoped",
                applicability_signature=signature,
                rule_record_digest=record_digest,
                classical_binding_digest="",
                classical_sources=[],
            )
        else:
            record.update(
                runtime_active=binding["verification_status"] == "verified",
                classical_binding_status=binding["verification_status"],
                applicability_signature=signature,
                rule_record_digest=record_digest,
                classical_binding_digest=binding["binding_digest"],
                classical_sources=binding["classical_sources"],
            )
    return tuple(EvidenceRule.from_dict(record) for record in records)


def _bazi_artifacts(question: str):
    calculation = CalculationResult.create(
        system="bazi",
        provider_id=BaziProvider.provider_id,
        provider_version=BaziProvider.provider_version,
        input_payload={"fixture": "qiongtong"},
        facts={
            "chart_facts": {
                "output": {
                    "day_master": {"stem": "甲"},
                    "month_command": {"branch": "申"},
                    "four_pillars": ["甲子", "壬申", "甲辰", "庚午"],
                    "hidden_stems": {},
                    "ten_gods": {},
                    "seasonal_profile": {},
                    "tiaohou_markers": {},
                }
            }
        },
    )
    goal = {
        "source_packs": ["bazi/qiongtong-baojian"],
        "evidence_questions": [question],
    }
    plan = reading_source_plan.compile_source_plan("bazi", goal, calculation.facts)
    facts = build_fact_index(calculation, reading_id=READING_ID, version=1)
    bundle = reading_evidence_bundle.compile_evidence_bundle(
        goal,
        calculation.facts,
        plan,
        fact_index=facts,
        reading_id=READING_ID,
        version=1,
    )
    return facts, bundle


class EvidenceApplicabilityTests(unittest.TestCase):
    def test_generated_index_contains_only_substantive_records(self) -> None:
        self.assertTrue(INDEX.is_file(), "evidence rule index must be generated")
        rows = [
            json.loads(line)
            for line in INDEX.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertGreater(len(rows), 100)
        self.assertEqual({row["record_kind"] for row in rows}, {"substantive_rule"})
        catalog = json.loads(
            (ROOT / "references" / "catalog" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        indexed_packs = {row["source_pack"] for row in rows}
        ready_packs_with_substantive_rules = {
            f"{item['system']}/{item['slug']}"
            for item in catalog["ready_reference_packs"]
            if f"{item['system']}/{item['slug']}"
            != "san-shi/qimen-dunjia-tongzhi"
        }
        self.assertEqual(ready_packs_with_substantive_rules - indexed_packs, set())
        forbidden = (
            "规则统计",
            "短引统计",
            "source manifest",
            "采集说明",
            "输入校验",
        )
        for row in rows:
            rendered = (
                f"{row['title']} {row['chapter']} {row['quote']}"
            ).casefold()
            self.assertFalse(any(item.casefold() in rendered for item in forbidden))

    def test_rule_contract_round_trips_predicates_and_relationships(self) -> None:
        rules = importlib.import_module("reading_engine.evidence_rules")
        loaded = rules.load_evidence_rules(INDEX)
        qiongtong = next(
            rule
            for rule in loaded
            if rule.source_pack == "bazi/qiongtong-baojian"
            and rule.chapter == "三秋甲木"
        )
        self.assertEqual(
            rules.EvidenceRule.from_dict(qiongtong.to_dict()),
            qiongtong,
        )
        self.assertTrue(qiongtong.required_fact_predicates)

    def test_qiongtong_filters_wrong_day_master_and_month_before_ranking(self) -> None:
        with patch(
            "reading_evidence_bundle.production_evidence_rules",
            return_value=_fresh_evidence_rules(),
        ):
            fact_index, bundle = _bazi_artifacts("三秋甲木怎样取调候")

        self.assertTrue(bundle.evidence)
        rule_ids = {node.rule_id for node in bundle.evidence}
        self.assertIn("bazi/qiongtong-baojian#QR-01-03", rule_ids)
        self.assertNotEqual(
            rule_ids,
            {"bazi/qiongtong-baojian#QTB-M01"},
        )
        self.assertFalse(
            any(
                rule_id.startswith("bazi/qiongtong-baojian#QR-")
                and rule_id != "bazi/qiongtong-baojian#QR-01-03"
                for rule_id in rule_ids
            )
        )
        chapter_node = next(
            node
            for node in bundle.evidence
            if node.rule_id == "bazi/qiongtong-baojian#QR-01-03"
        )
        self.assertEqual(chapter_node.anchor, "fulltext.md L105-L149")
        allowed = {
            fact.fact_id
            for fact in fact_index
            if fact.path.endswith("/day_master/stem")
            or fact.path.endswith("/month_command/branch")
        }
        self.assertTrue(allowed)
        self.assertTrue(
            all(set(node.fact_refs) <= allowed for node in bundle.evidence)
        )

    def test_qiongtong_facts_override_a_wrong_day_master_question(self) -> None:
        calculation = CalculationResult.create(
            system="bazi",
            provider_id=BaziProvider.provider_id,
            provider_version=BaziProvider.provider_version,
            input_payload={"fixture": "wrong-question"},
            facts={
                "chart_facts": {
                    "output": {
                        "day_master": {"stem": "乙"},
                        "month_command": {"branch": "申"},
                    }
                }
            },
        )
        goal = {
            "source_packs": ["bazi/qiongtong-baojian"],
            "evidence_questions": ["三秋甲木怎样取调候"],
        }
        plan = reading_source_plan.compile_source_plan("bazi", goal, calculation.facts)
        facts = build_fact_index(calculation, reading_id=READING_ID, version=1)

        with patch(
            "reading_evidence_bundle.production_evidence_rules",
            return_value=_fresh_evidence_rules(),
        ):
            bundle = reading_evidence_bundle.compile_evidence_bundle(
                goal,
                calculation.facts,
                plan,
                fact_index=facts,
                reading_id=READING_ID,
                version=1,
            )

        self.assertTrue(bundle.evidence)
        rule_ids = {node.rule_id for node in bundle.evidence}
        self.assertIn("bazi/qiongtong-baojian#QR-01-07", rule_ids)
        self.assertNotEqual(
            rule_ids,
            {"bazi/qiongtong-baojian#QTB-M01"},
        )
        self.assertNotIn("bazi/qiongtong-baojian#QR-01-03", rule_ids)

    def test_liuren_method_predicate_excludes_generic_and_wrong_method_rules(self) -> None:
        calculation = CalculationResult.create(
            system="liuren",
            provider_id=LiurenProvider.provider_id,
            provider_version=LiurenProvider.provider_version,
            input_payload={"fixture": "biyong"},
            facts={
                "chart_facts": {
                    "output": {
                        "transmission_method": {"primary": "比用"},
                        "three_transmissions": [
                            {"branch": "亥"},
                            {"branch": "酉"},
                            {"branch": "未"},
                        ],
                        "month_general": {"branch": "午"},
                    }
                }
            },
        )
        goal = {
            "source_packs": ["san-shi/daliuren-daquan"],
            "evidence_questions": ["比用如何确定发用"],
            "counter_evidence_questions": ["何时不能使用比用"],
            "question_dimensions": ["timing"],
        }
        plan = reading_source_plan.compile_source_plan(
            "liuren", goal, calculation.facts
        )
        facts = build_fact_index(calculation, reading_id=READING_ID, version=1)

        bundle = reading_evidence_bundle.compile_evidence_bundle(
            goal,
            calculation.facts,
            plan,
            fact_index=facts,
            reading_id=READING_ID,
            version=1,
        )

        self.assertTrue(any("DLR-03" in node.rule_id for node in bundle.evidence))
        self.assertFalse(any("DLR-00" in node.rule_id for node in bundle.evidence))
        self.assertFalse(any("DLR-02" in node.rule_id for node in bundle.evidence))
        method_fact = next(
            fact.fact_id
            for fact in facts
            if fact.path.endswith("/transmission_method/primary")
        )
        self.assertTrue(
            all(method_fact in node.fact_refs for node in bundle.evidence)
        )
        self.assertIn(
            "no_applicable_counter_evidence",
            {gap.reason for gap in bundle.source_gaps},
        )

    def test_zero_semantic_match_stays_zero_with_a_structured_gap(self) -> None:
        _, bundle = _bazi_artifacts("ZXCV-NO-CLASSICAL-SEMANTIC-MATCH-9981")

        self.assertEqual(bundle.evidence, ())
        reasons = {gap.reason for gap in bundle.source_gaps}
        self.assertIn("zero_applicable_evidence", reasons)
        self.assertIn("no_applicable_counter_evidence", reasons)

    def test_metadata_or_header_text_cannot_become_evidence(self) -> None:
        for question in ("规则统计", "id quote section source anchor"):
            with self.subTest(question=question):
                _, bundle = _bazi_artifacts(question)
                rendered = " ".join(node.assertion for node in bundle.evidence)
                self.assertNotIn("规则统计", rendered)
                self.assertNotIn("| id | quote |", rendered.casefold())

    def test_a_zi_branch_does_not_lexically_bind_or_enable_unbound_rules(self) -> None:
        calculation = CalculationResult.create(
            system="bazi",
            provider_id=BaziProvider.provider_id,
            provider_version=BaziProvider.provider_version,
            input_payload={"fixture": "zi-branch"},
            facts={
                "chart_facts": {
                    "output": {
                        "day_master": {"stem": "甲"},
                        "month_command": {"branch": "子"},
                    }
                }
            },
        )
        goal = {
            "source_packs": ["bazi/ditiansui-chanwei"],
            "evidence_questions": ["格局如何影响事业"],
        }
        plan = reading_source_plan.compile_source_plan(
            "bazi", goal, calculation.facts
        )
        facts = build_fact_index(calculation, reading_id=READING_ID, version=1)

        bundle = reading_evidence_bundle.compile_evidence_bundle(
            goal,
            calculation.facts,
            plan,
            fact_index=facts,
            reading_id=READING_ID,
            version=1,
        )

        self.assertEqual(bundle.evidence, ())
        self.assertIn(
            "zero_applicable_evidence",
            {gap.reason for gap in bundle.source_gaps},
        )

    def test_production_evidence_goal_uses_the_current_intent_frame(self) -> None:
        intent = {
            "subject_refs": ["subject-1"],
            "calculation_object": "natal",
            "question_dimensions": ["timing"],
            "horizon": {"kind": "year", "start": None, "end": None},
            "requested_method": None,
            "requested_granularity": "directional",
            "continuity": {
                "reading_id": None,
                "same_subject": False,
                "same_event": False,
            },
            "facts_present": [],
            "facts_corrected": [],
            "evidence_questions": ["当前流年何时发生变化"],
        }
        request = ReadingRequest(
            query="这段自然语言不参与证据分类",
            action="new",
            system="bazi",
            intent=intent,
            goal={
                "evidence_questions": ["旧问题不得继续参与检索"],
                "question_dimensions": ["stale-dimension"],
                "counter_evidence_questions": ["哪些条件会限制结论"],
            },
        )

        effective = _adapter_evidence_goal(request)

        self.assertEqual(
            effective["evidence_questions"],
            intent["evidence_questions"],
        )
        self.assertEqual(
            effective["question_dimensions"],
            intent["question_dimensions"],
        )
        self.assertEqual(
            effective["requested_dimensions"],
            intent["question_dimensions"],
        )
        self.assertNotIn(request.query, json.dumps(effective, ensure_ascii=False))

    def test_meihua_source_plan_revalidates_with_its_subsystem_identity(self) -> None:
        calculation = CalculationResult.create(
            system="meihua",
            provider_id=MeihuaProvider.provider_id,
            provider_version=MeihuaProvider.provider_version,
            input_payload={"fixture": "meihua-plan"},
            facts={"chart_facts": {"output": {"primary_hexagram": "乾"}}},
        )
        current_goal = {
            "evidence_questions": ["本卦与动爻如何共同判断"],
            "question_dimensions": ["outcome"],
        }
        plan = reading_source_plan.compile_source_plan(
            "meihua", current_goal, calculation.facts
        )
        facts = build_fact_index(calculation, reading_id=READING_ID, version=1)

        bundle = reading_evidence_bundle.compile_evidence_bundle(
            current_goal,
            calculation.facts,
            plan,
            fact_index=facts,
            reading_id=READING_ID,
            version=1,
        )

        self.assertEqual(bundle.system, "meihua")

    def test_matching_dependencies_and_conflicts_are_retrieved_explicitly(self) -> None:
        rules_module = importlib.import_module("reading_engine.evidence_rules")
        source_path = "references/books/san-shi/daliuren-daquan/rules.md"
        source_hash = hashlib.sha256((ROOT / source_path).read_bytes()).hexdigest()

        def rule(
            local_id: str,
            title: str,
            *,
            depends=(),
            conflicts=(),
            unhashable_exclusion: bool = False,
        ):
            return rules_module.EvidenceRule(
                rule_id=f"san-shi/daliuren-daquan#{local_id}",
                local_rule_id=local_id,
                system="liuren",
                source_pack="san-shi/daliuren-daquan",
                source_title="大六壬大全",
                source_layer="primary",
                chapter=title,
                title=title,
                quote=f"{title}的可核验规则",
                source_anchor=f"{source_path}#{local_id}",
                topics=(title,),
                required_fact_predicates=(
                    rules_module.FactPredicate(
                        "/transmission_method/primary", "eq", value="比用"
                    ),
                ),
                excluded_fact_predicates=(
                    (
                        rules_module.FactPredicate(
                            "/unmatched",
                            "same_record_fields",
                            value={"never": "matches"},
                        ),
                    )
                    if unhashable_exclusion
                    else ()
                ),
                exception_rule_ids=(),
                conflict_rule_ids=tuple(conflicts),
                depends_on_rule_ids=tuple(depends),
                record_kind="substantive_rule",
                source_path=source_path,
                source_sha256=source_hash,
                quote_hash=hashlib.sha256(
                    f"{title}的可核验规则".encode("utf-8")
                ).hexdigest(),
            )

        main_id = "san-shi/daliuren-daquan#MAIN-01"
        dependency_id = "san-shi/daliuren-daquan#DEP-01"
        conflict_id = "san-shi/daliuren-daquan#CON-01"
        available = (
            rule(
                "MAIN-01",
                "比用发用",
                depends=(dependency_id,),
                conflicts=(main_id, conflict_id),
                unhashable_exclusion=True,
            ),
            rule("DEP-01", "比用前提"),
            rule("CON-01", "比用限制"),
        )
        calculation = CalculationResult.create(
            system="liuren",
            provider_id=LiurenProvider.provider_id,
            provider_version=LiurenProvider.provider_version,
            input_payload={"fixture": "relationships"},
            facts={
                "chart_facts": {
                    "output": {"transmission_method": {"primary": "比用"}}
                }
            },
        )
        current_goal = {
            "source_packs": ["san-shi/daliuren-daquan"],
            "evidence_questions": ["比用发用"],
        }
        plan = reading_source_plan.compile_source_plan(
            "liuren", current_goal, calculation.facts
        )
        facts = build_fact_index(calculation, reading_id=READING_ID, version=1)

        with patch(
            "reading_evidence_bundle.production_evidence_rules",
            return_value=available,
        ):
            bundle = reading_evidence_bundle.compile_evidence_bundle(
                current_goal,
                calculation.facts,
                plan,
                fact_index=facts,
                reading_id=READING_ID,
                version=1,
            )

        support_ids = {node.rule_id for node in bundle.evidence}
        counter_ids = {node.rule_id for node in bundle.counter_evidence}
        self.assertIn(main_id, support_ids)
        self.assertIn(dependency_id, support_ids)
        self.assertIn(conflict_id, counter_ids)
        self.assertNotIn(main_id, counter_ids)
        self.assertTrue(support_ids.isdisjoint(counter_ids))
        self.assertIn(
            "conflict",
            {relation.relation for relation in bundle.source_relationships},
        )


class GenericProfileCompilerTests(unittest.TestCase):
    """The generic evidence compiler consumes provider profile data only."""

    @staticmethod
    def _fake_rule(
        rule_id: str = "pack.alpha#rule-1",
        *,
        pack: str = "pack.alpha/book-one",
        system: str = "system.alpha",
        role: str = "issue_specific_judgment_rule",
        chapter: str = "chapter-one",
        predicate_suffix: str = "/marker.one",
    ) -> EvidenceRule:
        from reading_engine.evidence_rules import FactPredicate

        return EvidenceRule(
            rule_id=rule_id,
            local_rule_id=rule_id.rsplit("#", 1)[-1],
            system=system,
            source_pack=pack,
            source_title="fixture title",
            source_layer="layer.one",
            chapter=chapter,
            title="fixture rule",
            quote="fixture quote",
            source_anchor="anchor-1",
            topics=("topic.one",),
            required_fact_predicates=(
                FactPredicate(path_suffix=predicate_suffix, operator="present"),
            ),
            excluded_fact_predicates=(),
            exception_rule_ids=(),
            conflict_rule_ids=(),
            depends_on_rule_ids=(),
            record_kind="rule",
            source_path="references/books/pack.alpha/book-one/rules.md",
            source_sha256="0" * 64,
            quote_hash="1" * 64,
            evidence_role=role,
        )

    @staticmethod
    def _fake_fact(path: str = "/facts/marker.one") -> "FactRef":
        from reading_engine.contracts import FactRef

        return FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value="observed",
            provider_id="fixture.provider",
            provider_version="1",
            reading_id=READING_ID,
            version=1,
        )

    @staticmethod
    def _fake_plan(**overrides: object) -> dict:
        plan = {
            "system": "system.alpha",
            "subsystem": None,
            "registry_route": "route.alpha",
            "question_dimensions": ["dimension.one"],
            "requested_dimensions": ["dimension.one"],
            "sources": [
                {
                    "pack": "pack.alpha/book-one",
                    "title": "fixture title",
                    "role": "support",
                }
            ],
            "scope_compatible": True,
        }
        plan.update(overrides)
        return plan

    def test_prerequisites_gate_rules_before_any_ranking(self) -> None:
        rule = self._fake_rule()
        matching = reading_evidence_bundle._eligible_rules(
            self._fake_plan(),
            (self._fake_fact(),),
            rules=(rule,),
        )
        self.assertIn("pack.alpha/book-one", matching)
        missing = reading_evidence_bundle._eligible_rules(
            self._fake_plan(),
            (self._fake_fact("/facts/marker.other"),),
            rules=(rule,),
        )
        self.assertEqual(missing, {})

    def test_compatible_rule_systems_come_from_plan_data(self) -> None:
        rule = self._fake_rule(system="system.beta")
        rejected = reading_evidence_bundle._eligible_rules(
            self._fake_plan(),
            (self._fake_fact(),),
            rules=(rule,),
        )
        self.assertEqual(rejected, {})
        accepted = reading_evidence_bundle._eligible_rules(
            self._fake_plan(compatible_rule_systems=["system.beta"]),
            (self._fake_fact(),),
            rules=(rule,),
        )
        self.assertIn("pack.alpha/book-one", accepted)

    def test_allowed_evidence_roles_come_from_plan_data(self) -> None:
        rule = self._fake_rule(role="imagery_correspondence")
        rejected = reading_evidence_bundle._eligible_rules(
            self._fake_plan(allowed_evidence_roles=["timing_rule"]),
            (self._fake_fact(),),
            rules=(rule,),
        )
        self.assertEqual(rejected, {})
        accepted = reading_evidence_bundle._eligible_rules(
            self._fake_plan(
                allowed_evidence_roles=["imagery_correspondence"]
            ),
            (self._fake_fact(),),
            rules=(rule,),
        )
        self.assertIn("pack.alpha/book-one", accepted)

    def test_pack_chapter_filters_come_from_plan_data(self) -> None:
        in_chapter = self._fake_rule("pack.alpha#rule-1", chapter="chapter-one")
        off_chapter = self._fake_rule("pack.alpha#rule-2", chapter="chapter-two")
        plan = self._fake_plan(
            pack_chapter_filters={
                "pack.alpha/book-one": {
                    "applicable_chapter": "chapter-one",
                    "exempt_roles": ["methodology_rule"],
                }
            }
        )
        grouped = reading_evidence_bundle._eligible_rules(
            plan,
            (self._fake_fact(),),
            rules=(in_chapter, off_chapter),
        )
        selected_ids = [
            candidate[0].rule_id
            for candidate in grouped.get("pack.alpha/book-one", [])
        ]
        self.assertEqual(selected_ids, ["pack.alpha#rule-1"])

    def test_incompatible_scope_flag_yields_zero_rules_without_fallback(
        self,
    ) -> None:
        grouped = reading_evidence_bundle._eligible_rules(
            self._fake_plan(scope_compatible=False),
            (self._fake_fact(),),
            rules=(self._fake_rule(),),
        )
        self.assertEqual(grouped, {})

    def test_transaction_system_reads_plan_identity_not_branches(self) -> None:
        plan = self._fake_plan(registry_route="route.gamma")
        self.assertEqual(
            reading_evidence_bundle._transaction_system(plan),
            "route.gamma",
        )

    def test_conflicting_candidates_for_one_rule_id_are_rejected(self) -> None:
        first = self._fake_rule()
        conflicting = replace(first, quote="conflicting fixture quote")

        with self.assertRaisesRegex(ValueError, "conflicting evidence candidate"):
            reading_evidence_bundle._unique_candidates(
                [
                    (first, ("fact:/facts/marker.one",), ("first",)),
                    (conflicting, ("fact:/facts/marker.one",), ("first",)),
                ]
            )


if __name__ == "__main__":
    unittest.main()
