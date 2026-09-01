"""Task 7N regressions for evidence-derived provider completeness."""

from __future__ import annotations

import copy
import hashlib
import inspect
import os
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import yaml

import audit_provider_completeness as completeness
import build_evidence_index
import reading_evidence_bundle
import reading_source_plan
from reading_engine.contracts import (
    CalculationResult,
    FactExtensionResult,
    FactRef,
    ReadingRequest,
)
from reading_engine.evidence_rules import (
    EvidenceRule,
    FactPredicate,
    load_evidence_rules,
    match_rule,
)
from reading_engine.fact_index import build_fact_index
from reading_engine import providers as reading_providers
from reading_engine.providers import (
    BaziProvider,
    FortuneProvider,
    LiurenProvider,
    LiuyaoProvider,
    TaiyiProvider,
    _attach_extension,
)
from reading_engine.providers import PROVIDER_CAPABILITIES, missing_required_inputs


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "references" / "matrices" / "provider-completeness.yaml"
EXPECTED_SYSTEMS = {
    "bazi",
    "fortune",
    "ziwei",
    "luming-nayin",
    "xingming",
    "liuyao",
    "meihua",
    "liuren",
    "qimen",
    "taiyi",
    "selection",
    "fengshui",
    "physiognomy",
}
EXPECTED_PROVIDER_IDENTITIES = {
    "bazi": (
        "reading_engine.providers.BaziProvider",
        "mingli-master.bazi.v7",
        "mingli-bazi-pipeline-v1-interpreted",
    ),
    "fortune": (
        "reading_engine.providers.FortuneProvider",
        "mingli-master.fortune.v6",
        "fortune-public-v6-mechanism-stack",
    ),
    "ziwei": (
        "reading_engine.providers.ZiweiProvider",
        "mingli-master.ziwei.iztro",
        "1.2.0+iztro-2.5.8",
    ),
    "luming-nayin": (
        "reading_engine.providers.LumingProvider",
        "mingli-master.luming-nayin.v1",
        "1.2.0",
    ),
    "xingming": (
        "reading_engine.providers.XingmingProvider",
        "mingli-master.xingming.v1",
        "1.1.0",
    ),
    "liuyao": (
        "reading_engine.providers.LiuyaoProvider",
        "mingli-master.liuyao.v1",
        "1.4.0",
    ),
    "meihua": (
        "reading_engine.providers.MeihuaProvider",
        "mingli-master.meihua.v1",
        "1.1.0",
    ),
    "liuren": (
        "reading_engine.providers.LiurenProvider",
        "mingli-master.liuren.v8",
        "mingli-liuren-pipeline-v6-runtime-contract",
    ),
    "qimen": (
        "reading_engine.providers.QimenProvider",
        "mingli-master.qimen.v1",
        "5.2.0",
    ),
    "taiyi": (
        "reading_engine.providers.TaiyiProvider",
        "mingli-master.taiyi.v1",
        "5.2.0",
    ),
    "selection": (
        "reading_engine.providers.SelectionProvider",
        "mingli-master.selection.v1",
        "1.3.0",
    ),
    "fengshui": (
        "reading_engine.providers.FengshuiProvider",
        "mingli-master.fengshui.v1",
        "1.0.0",
    ),
    "physiognomy": (
        "reading_engine.providers.PhysiognomyProvider",
        "mingli-master.physiognomy.v1",
        "1.1.0",
    ),
}


class SourcePackReplayContractTests(unittest.TestCase):
    """Mandatory source readiness is proved pack-by-pack from real results."""

    @staticmethod
    def _rule(
        pack: str,
        local_id: str,
        *,
        value: str,
        role: str = "issue_specific_judgment_rule",
    ) -> EvidenceRule:
        rule_id = f"{pack}#{local_id}"
        return EvidenceRule(
            rule_id=rule_id,
            local_rule_id=local_id,
            system="probe",
            source_pack=pack,
            source_title=pack,
            source_layer="primary",
            chapter="probe",
            title=rule_id,
            quote="fixed classical quote",
            source_anchor="rules.md#L1",
            topics=("probe",),
            required_fact_predicates=(
                FactPredicate(path_suffix="/source_probe", operator="eq", value=value),
            ),
            excluded_fact_predicates=(),
            exception_rule_ids=(),
            conflict_rule_ids=(),
            depends_on_rule_ids=(),
            record_kind="substantive_rule",
            source_path="references/books/probe/rules.md",
            source_sha256="1" * 64,
            quote_hash="2" * 64,
            evidence_role=role,
            runtime_active=True,
            classical_binding_status="verified",
            applicability_signature="3" * 64,
            rule_record_digest="4" * 64,
            classical_binding_digest="5" * 64,
            classical_sources=(
                {
                    "path": "references/fulltext/probe/fulltext.md",
                    "sha256": "6" * 64,
                    "anchor": "fulltext.md#L1",
                    "verbatim_quote": "fixed classical quote",
                    "verbatim_quote_sha256": "7" * 64,
                },
            ),
        )

    @staticmethod
    def _result(value: str) -> CalculationResult:
        return CalculationResult.create(
            system="probe",
            provider_id="probe.provider",
            provider_version="1",
            input_payload={"request_semantics": {"case": value}},
            facts={"source_probe": value},
        )

    @staticmethod
    def _family(
        *,
        required: tuple[str, ...],
        comparison: tuple[str, ...] = (),
    ) -> dict[str, object]:
        return {
            "required_always": list(required),
            "required_when_active_subprofile": {},
            "comparison_only": list(comparison),
            "required_roles_by_pack": {
                pack: ["issue_specific_judgment_rule"] for pack in required
            },
        }

    @staticmethod
    def _replay(result: CalculationResult, **extra: object) -> dict[str, object]:
        return {
            "case_id": "fixture-1",
            "fixture_input_bound": True,
            "ready": True,
            "calculation": result,
            **extra,
        }

    def test_missing_positive_for_one_mandatory_pack_fails_the_route(self) -> None:
        report = completeness._audit_source_pack_replays(
            "probe",
            source_family=self._family(required=("probe/a", "probe/b")),
            rules=(
                self._rule("probe/a", "A-1", value="A"),
                self._rule("probe/b", "B-1", value="B"),
            ),
            fixture_replays=(self._replay(
                self._result("A"),
                runtime_enabled_rule_ids=["probe/a#A-1", "probe/b#B-1"],
            ),),
        )

        self.assertFalse(report["ready"], report)
        self.assertTrue(report["packs"]["probe/a"]["ready"])
        self.assertFalse(report["packs"]["probe/b"]["ready"])
        self.assertEqual(report["packs"]["probe/b"]["positive_replay_rule_ids"], [])

    def test_comparison_only_positive_cannot_replace_required_support(self) -> None:
        report = completeness._audit_source_pack_replays(
            "probe",
            source_family=self._family(
                required=("probe/required",),
                comparison=("probe/comparison",),
            ),
            rules=(
                self._rule("probe/required", "R-1", value="R"),
                self._rule("probe/comparison", "C-1", value="C"),
            ),
            fixture_replays=(self._replay(
                self._result("C"),
                runtime_enabled_rule_ids=[
                    "probe/required#R-1", "probe/comparison#C-1"
                ],
            ),),
        )

        self.assertFalse(report["ready"], report)
        self.assertFalse(report["packs"]["probe/required"]["ready"])
        self.assertFalse(report["packs"]["probe/comparison"]["mandatory"])

    def test_forged_route_aggregate_cannot_hide_an_unready_pack(self) -> None:
        report = completeness._audit_source_pack_replays(
            "probe",
            source_family=self._family(required=("probe/a", "probe/b")),
            rules=(
                self._rule("probe/a", "A-1", value="A"),
                self._rule("probe/b", "B-1", value="B"),
            ),
            fixture_replays=(self._replay(
                self._result("A"),
                runtime_enabled_rule_ids=["probe/a#A-1", "probe/b#B-1"],
            ),),
        )
        forged = copy.deepcopy(report)
        forged.update(
            {
                "ready": True,
                "matched_representative_rules": ["probe/a#A-1", "probe/b#B-1"],
                "runtime_enabled_bound_rules": 2,
            }
        )

        findings = completeness._source_pack_replay_findings("probe", forged)

        self.assertIn("probe/b", " ".join(findings))

    def test_replay_self_reported_match_ids_are_ignored(self) -> None:
        report = completeness._audit_source_pack_replays(
            "probe",
            source_family=self._family(required=("probe/a",)),
            rules=(self._rule("probe/a", "A-1", value="A"),),
            fixture_replays=(
                self._replay(
                    self._result("not-A"),
                    matched_rule_ids=["probe/a#A-1"],
                    runtime_enabled_rule_ids=["probe/a#A-1"],
                ),
            ),
        )

        self.assertFalse(report["ready"], report)
        self.assertEqual(report["packs"]["probe/a"]["positive_replay_rule_ids"], [])

    def test_declared_pack_role_cannot_shrink_to_the_roles_that_happen_to_bind(self) -> None:
        family = self._family(required=("probe/a",))
        report = completeness._audit_source_pack_replays(
            "probe",
            source_family=family,
            rules=(
                self._rule(
                    "probe/a",
                    "A-1",
                    value="A",
                    role="methodology_rule",
                ),
            ),
            fixture_replays=(
                self._replay(
                    self._result("A"),
                    runtime_enabled_rule_ids=["probe/a#A-1"],
                ),
            ),
        )

        self.assertFalse(report["ready"], report)
        self.assertEqual(
            report["packs"]["probe/a"]["required_roles"],
            ["issue_specific_judgment_rule"],
        )
        self.assertIn(
            "probe/a: required roles not covered: ['issue_specific_judgment_rule']",
            report["packs"]["probe/a"]["findings"],
        )

    def test_predicate_mutation_that_still_matches_fails_the_pack(self) -> None:
        with mock.patch.object(
            completeness,
            "match_rule",
            return_value=(True, ("self-reported-fact",), ("self-reported",)),
        ):
            report = completeness._audit_source_pack_replays(
                "probe",
                source_family=self._family(required=("probe/a",)),
                rules=(self._rule("probe/a", "A-1", value="A"),),
                fixture_replays=(self._replay(
                    self._result("A"),
                    runtime_enabled_rule_ids=["probe/a#A-1"],
                ),),
            )

        self.assertFalse(report["ready"], report)
        self.assertEqual(report["packs"]["probe/a"]["negative_mutation_rule_ids"], [])
        self.assertIn("predicate mutation", " ".join(report["findings"]))

    def test_fact_match_without_runtime_source_plan_eligibility_fails(self) -> None:
        report = completeness._audit_source_pack_replays(
            "probe",
            source_family=self._family(required=("probe/a",)),
            rules=(self._rule("probe/a", "A-1", value="A"),),
            fixture_replays=(self._replay(
                self._result("A"),
                runtime_enabled_rule_ids=[],
            ),),
        )

        self.assertFalse(report["ready"], report)
        self.assertEqual(report["packs"]["probe/a"]["positive_replay_rule_ids"], [])

    def test_same_record_predicate_replay_is_mutation_closed(self) -> None:
        rule = replace(
            self._rule("probe/a", "A-1", value="unused"),
            required_fact_predicates=(
                FactPredicate(
                    path_suffix="/source_rules",
                    operator="same_record_fields",
                    value={
                        "source_pack": "probe/a",
                        "status": "active",
                        "source_rule": "A-1",
                    },
                ),
            ),
        )
        result = CalculationResult.create(
            system="probe",
            provider_id="probe.provider",
            provider_version="1",
            input_payload={"request_semantics": {"case": "same-record"}},
            facts={
                "source_rules": [
                    {
                        "source_pack": "probe/a",
                        "status": "active",
                        "source_rule": "A-1",
                    },
                    # A decoy row scattering the required values across
                    # different records must not become the witness.
                    {
                        "source_pack": "probe/a",
                        "status": "inactive",
                        "source_rule": "A-9",
                    },
                ]
            },
        )

        report = completeness._audit_source_pack_replays(
            "probe",
            source_family=self._family(required=("probe/a",)),
            rules=(rule,),
            fixture_replays=(
                self._replay(result, runtime_enabled_rule_ids=["probe/a#A-1"]),
            ),
        )

        pack = report["packs"]["probe/a"]
        self.assertEqual(pack["positive_replay_rule_ids"], ["probe/a#A-1"])
        self.assertEqual(pack["negative_mutation_rule_ids"], ["probe/a#A-1"])
        self.assertTrue(pack["ready"], pack)
        self.assertTrue(report["ready"], report)


class EvidenceScopeBindingTests(unittest.TestCase):
    @staticmethod
    def _fact(path: str, value: object) -> FactRef:
        return FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value=value,
            provider_id="test.scope",
            provider_version="1",
            reading_id="a" * 32,
            version=1,
        )

    def _minimal_matching_facts(self, rule: EvidenceRule) -> tuple[FactRef, ...]:
        facts: list[FactRef] = []
        for index, predicate in enumerate(rule.required_fact_predicates):
            base = f"/probe{predicate.path_suffix}"
            if predicate.operator in {"present", "nonempty"}:
                facts.append(self._fact(f"{base}/{index}", "present"))
            elif predicate.operator == "descendant_eq":
                facts.append(self._fact(f"{base}/{index}/value", predicate.value))
            elif predicate.operator == "same_record_fields":
                for field, value in predicate.value.items():
                    facts.append(self._fact(f"{base}/{index}/{field}", value))
            elif predicate.operator == "eq":
                facts.append(self._fact(base, predicate.value))
            elif predicate.operator == "in":
                facts.append(self._fact(base, predicate.values[0]))
            elif predicate.operator == "contains":
                facts.append(self._fact(base, [predicate.value]))
            else:  # pragma: no cover - validator owns the operator allow-list
                self.fail(f"unsupported fixture predicate: {predicate.operator}")
        return tuple(facts)

    def test_curated_scope_bindings_compile_into_exact_source_rules(self) -> None:
        bindings = build_evidence_index.load_evidence_scope_bindings(root=ROOT)
        records = {
            record["rule_id"]: record
            for record in build_evidence_index.compile_evidence_rules(root=ROOT)
        }

        self.assertEqual(
            {entry["route"] for entry in bindings.values()},
            {
                "bazi", "ziwei", "luming-nayin", "xingming", "liuyao",
                "meihua", "liuren", "selection", "fengshui", "physiognomy",
            },
        )
        build_evidence_index.validate_evidence_scope_binding_coverage(
            bindings,
            set(records),
        )
        for rule_id, entry in bindings.items():
            with self.subTest(rule_id=rule_id):
                expected = list(entry["predicates"])
                if entry["route"] in {"fengshui", "physiognomy"}:
                    expected = [
                        {
                            "path_suffix": "/fact_layer_status",
                            "operator": "eq",
                            "value": (
                                f"observation_driven_{entry['route']}_facts"
                            ),
                        },
                        {
                            "path_suffix": "/active_source_rule_ids",
                            "operator": "descendant_eq",
                            "value": rule_id,
                        },
                        *expected,
                    ]
                self.assertEqual(
                    records[rule_id]["required_fact_predicates"],
                    expected,
                )

    def test_scope_binding_cannot_use_fact_layer_status_as_sole_proof(self) -> None:
        payload = {
            "schema_version": "mingli-evidence-scope-bindings-v1",
            "bindings": {
                "ziwei/taiwei-fu#TR-01": {
                    "route": "ziwei",
                    "rationale": "mutation probe",
                    "predicates": [
                        {
                            "path_suffix": "/fact_layer_status",
                            "operator": "present",
                        }
                    ],
                }
            },
        }

        with self.assertRaisesRegex(ValueError, "fact_layer_status"):
            build_evidence_index.validate_evidence_scope_bindings(payload)

    def test_scope_binding_rejects_unknown_compiled_rule_id(self) -> None:
        bindings = build_evidence_index.load_evidence_scope_bindings(root=ROOT)
        mutated = copy.deepcopy(bindings)
        mutated["ziwei/not-a-real-pack#NO-00"] = copy.deepcopy(
            next(iter(bindings.values()))
        )

        with self.assertRaisesRegex(ValueError, "unknown evidence rule"):
            build_evidence_index.validate_evidence_scope_binding_coverage(
                mutated,
                {
                    record["rule_id"]
                    for record in build_evidence_index.compile_evidence_rules(root=ROOT)
                },
            )

    def test_luming_jiazi_scope_cannot_widen_beyond_year_pillar(self) -> None:
        payload = {
            "schema_version": "mingli-evidence-scope-bindings-v1",
            "bindings": {
                "luming-nayin/li-xuzhong-mingshu#LX-01-01": {
                    "route": "luming-nayin",
                    "rationale": "mutation probe",
                    "predicates": [
                        {
                            "path_suffix": "/four_pillars",
                            "operator": "descendant_eq",
                            "value": "甲子",
                        }
                    ],
                }
            },
        }

        with self.assertRaisesRegex(ValueError, "year pillar"):
            build_evidence_index.validate_evidence_scope_bindings(payload)


    def test_luming_jiazi_rule_id_and_value_must_match(self) -> None:
        payload = {
            "schema_version": "mingli-evidence-scope-bindings-v1",
            "bindings": {
                "luming-nayin/li-xuzhong-mingshu#LX-01-01": {
                    "route": "luming-nayin",
                    "rationale": "mutation probe",
                    "predicates": [
                        {
                            "path_suffix": "/four_pillars/year",
                            "operator": "eq",
                            "value": "乙丑",
                        }
                    ],
                }
            },
        }

        with self.assertRaisesRegex(ValueError, "Jiazi value"):
            build_evidence_index.validate_evidence_scope_bindings(payload)

    def test_nonempty_predicate_rejects_an_empty_container(self) -> None:
        template = next(
            rule
            for rule in load_evidence_rules(
                ROOT / "references/index/evidence-rules.jsonl",
                root=ROOT,
            )
            if rule.rule_id == "divination/bushi-zhengzong#BSZZ-M01"
        ).to_dict()
        template["required_fact_predicates"] = [
            {"path_suffix": "/moving_lines", "operator": "nonempty"}
        ]
        rule = EvidenceRule.from_dict(template)

        empty = (self._fact("/chart_facts/output/moving_lines", []),)
        nonempty = (self._fact("/chart_facts/output/moving_lines/0", 1),)
        empty_scalar = (self._fact("/chart_facts/output/moving_lines", ""),)
        nonempty_scalar = (self._fact("/chart_facts/output/moving_lines", "甲子"),)

        self.assertFalse(match_rule(rule, empty)[0])
        self.assertTrue(match_rule(rule, nonempty)[0])
        self.assertFalse(match_rule(rule, empty_scalar)[0])
        self.assertTrue(match_rule(rule, nonempty_scalar)[0])

    def test_selection_inactive_rules_require_a_nonempty_marker(self) -> None:
        payload = yaml.safe_load(
            (
                ROOT
                / "references"
                / "matrices"
                / "selection-source-tables-v1.yaml"
            ).read_text(encoding="utf-8")
        )
        predicates = payload["evidence_fact_bindings"]["contracts"][
            "not_calculated"
        ]

        self.assertEqual(predicates[0]["operator"], "nonempty")

    def test_container_backed_bindings_reject_an_empty_fact(self) -> None:
        rules = {
            rule.rule_id: rule
            for rule in load_evidence_rules(
                ROOT / "references/index/evidence-rules.jsonl",
                root=ROOT,
            )
        }
        probes = {
            "ziwei/ziwei-doushu-quanshu#ZW-06-01": "/major_limits",
            "xingming/guotian-jing#GR-01-02": "/houses",
            "divination/zengshan-buyi#ZR-02-01": "/najia",
            "divination/meihua-yishu#MR-02-03": "/mutual_hexagram",
        }
        for rule_id, path_suffix in probes.items():
            with self.subTest(rule_id=rule_id):
                empty = (self._fact(f"/chart_facts/output{path_suffix}", []),)
                self.assertFalse(match_rule(rules[rule_id], empty)[0])

    def test_liuyao_moving_rule_rejects_a_real_static_cast(self) -> None:
        rules = {
            rule.rule_id: rule
            for rule in load_evidence_rules(
                ROOT / "references/index/evidence-rules.jsonl",
                root=ROOT,
            )
        }
        provider = LiuyaoProvider(ROOT)
        requests = {
            "moving": ReadingRequest(
                query="动卦适用性",
                system="liuyao",
                event_datetime="2024-02-10T12:00:00",
                timezone="Asia/Shanghai",
                location="上海",
                chart_data={"tosses": [9, 7, 7, 7, 7, 6]},
            ),
            "static": ReadingRequest(
                query="静卦适用性",
                system="liuyao",
                event_datetime="2024-02-10T12:00:00",
                timezone="Asia/Shanghai",
                location="上海",
                chart_data={"tosses": [7, 7, 7, 7, 7, 7]},
            ),
        }
        indexes = {}
        for label, request in requests.items():
            calculation = provider.calculate(request)
            calculation = provider.extend(
                calculation,
                tuple(PROVIDER_CAPABILITIES["liuyao"].dimensions),
                {"kind": "instant"},
            )
            indexes[label] = build_fact_index(
                calculation,
                reading_id="b" * 32,
                version=1,
            )

        moving_rule = rules["divination/bushi-zhengzong#BSZZ-M01"]
        self.assertTrue(match_rule(moving_rule, indexes["moving"])[0])
        self.assertFalse(match_rule(moving_rule, indexes["static"])[0])
        self.assertEqual(
            rules[
                "divination/zengshan-buyi#ZR-08-02"
            ].required_fact_predicates,
            (),
        )

    def test_every_curated_binding_has_an_inapplicable_mutation(self) -> None:
        bindings = build_evidence_index.load_evidence_scope_bindings(root=ROOT)
        rules = {
            rule.rule_id: rule
            for rule in load_evidence_rules(
                ROOT / "references/index/evidence-rules.jsonl",
                root=ROOT,
            )
        }

        for rule_id in sorted(bindings):
            with self.subTest(rule_id=rule_id):
                rule = rules[rule_id]
                matching = self._minimal_matching_facts(rule)
                if not rule.runtime_active:
                    self.assertFalse(match_rule(rule, matching)[0])
                    continue
                self.assertTrue(match_rule(rule, matching)[0])
                mutated = matching[1:]
                self.assertFalse(match_rule(rule, mutated)[0])

    def test_checked_index_must_equal_the_current_compiler_byte_for_byte(self) -> None:
        current = build_evidence_index.audit_checked_evidence_index(root=ROOT)
        self.assertTrue(current["current"], current)

        with tempfile.TemporaryDirectory() as temporary:
            mutated = Path(temporary) / "evidence-rules.jsonl"
            mutated.write_text(
                (ROOT / "references/index/evidence-rules.jsonl").read_text(
                    encoding="utf-8"
                )
                + "\n",
                encoding="utf-8",
            )
            report = build_evidence_index.audit_checked_evidence_index(
                root=ROOT,
                checked_path=mutated,
            )

        self.assertFalse(report["current"])
        self.assertTrue(report["findings"])

    def test_compiler_fails_closed_on_a_detached_root_without_research_sources(self) -> None:
        # Compilation regenerates the classical bindings and must therefore
        # verify every research-tree source; a detached release copy without
        # the research tree cannot silently rebuild the evidence index.
        # Runtime loading stays research-tree independent and detached
        # compilation with the required sources is covered by
        # test_v51_evidence_source_integrity.
        with tempfile.TemporaryDirectory() as temporary:
            detached = Path(temporary) / "skill"
            shutil.copytree(ROOT / "references", detached / "references")

            with self.assertRaisesRegex(ValueError, "research source is missing"):
                build_evidence_index.compile_evidence_rules(
                    root=detached,
                    verify_research_sources=True,
                )

    def test_eligible_rules_use_the_injected_rule_set(self) -> None:
        eligible = reading_evidence_bundle._eligible_rules(
            {
                "system": "bazi",
                "sources": [{"pack": "bazi/qiongtong-baojian"}],
            },
            (),
            rules=(),
        )

        self.assertEqual(eligible, {})


class BoundaryProofContractTests(unittest.TestCase):
    @staticmethod
    def _provider_proof(category: str) -> dict[str, str]:
        return {
            "category": category,
            "proof_mode": "provider_replay",
            "proof_id": f"provider_replay:bazi:{category}",
        }

    @staticmethod
    def _runtime(category: str, *, ready: bool = True) -> dict[str, object]:
        return {
            "case_replay_ready": True,
            "provider_boundary_replay_ready": True,
            "provider_boundary_replays": [
                {
                    "case_id": "boundary-a",
                    "categories": [category],
                    "fixture_input_bound": True,
                    "ready": ready,
                }
            ],
        }

    def _summary(
        self,
        *,
        categories: list[str],
        proofs: list[dict[str, str]],
        runtime: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return completeness._boundary_proof_summary(
            "bazi",
            declared_categories=categories,
            proof_declarations=proofs,
            dedicated_runtime_replay=(runtime or self._runtime(categories[0])),
            algorithm={},
            transaction_lifecycle={},
        )

    def test_every_declared_boundary_category_requires_one_verified_proof(self) -> None:
        summary = self._summary(
            categories=["edge", "unproved"],
            proofs=[self._provider_proof("edge")],
            runtime=self._runtime("edge"),
        )

        self.assertFalse(summary["ready"], summary)
        self.assertEqual(summary["verified_categories"], ["edge"])
        self.assertTrue(
            any("unproved" in item for item in summary["findings"]),
            summary,
        )

    def test_boundary_proof_rejects_unknown_id_and_mode_mismatch(self) -> None:
        unknown = self._provider_proof("edge")
        unknown["proof_id"] = "self-reported-ready"
        summary = self._summary(categories=["edge"], proofs=[unknown])
        self.assertFalse(summary["ready"], summary)
        self.assertTrue(any("unknown proof_id" in item for item in summary["findings"]))

        mismatch = self._provider_proof("edge")
        mismatch["proof_mode"] = "algorithm_invariant"
        summary = self._summary(categories=["edge"], proofs=[mismatch])
        self.assertFalse(summary["ready"], summary)
        self.assertTrue(any("mode mismatch" in item for item in summary["findings"]))

    def test_boundary_proof_rejects_duplicate_category_or_proof_id(self) -> None:
        duplicate_category = [
            self._provider_proof("edge"),
            {
                "category": "edge",
                "proof_mode": "provider_replay",
                "proof_id": "provider_replay:bazi:other",
            },
        ]
        summary = self._summary(categories=["edge"], proofs=duplicate_category)
        self.assertFalse(summary["ready"], summary)
        self.assertTrue(any("duplicate category" in item for item in summary["findings"]))

        duplicate_id = [
            self._provider_proof("edge"),
            {
                "category": "other",
                "proof_mode": "provider_replay",
                "proof_id": "provider_replay:bazi:edge",
            },
        ]
        summary = self._summary(
            categories=["edge", "other"],
            proofs=duplicate_id,
            runtime={
                **self._runtime("edge"),
                "provider_boundary_replays": [
                    {
                        "case_id": "boundary-a",
                        "categories": ["edge", "other"],
                        "fixture_input_bound": True,
                        "ready": True,
                    }
                ],
            },
        )
        self.assertFalse(summary["ready"], summary)
        self.assertTrue(any("duplicate proof_id" in item for item in summary["findings"]))

    def test_provider_replay_proof_requires_a_ready_fixture_bound_case(self) -> None:
        missing = self._summary(
            categories=["edge"],
            proofs=[self._provider_proof("edge")],
            runtime={
                **self._runtime("other"),
                "provider_boundary_replays": [],
            },
        )
        self.assertFalse(missing["ready"], missing)
        self.assertTrue(any("no provider case" in item for item in missing["findings"]))

        not_ready = self._summary(
            categories=["edge"],
            proofs=[self._provider_proof("edge")],
            runtime=self._runtime("edge", ready=False),
        )
        self.assertFalse(not_ready["ready"], not_ready)
        self.assertTrue(
            any("provider case is not ready" in item for item in not_ready["findings"]),
            not_ready,
        )

    def test_central_declarations_select_the_registered_proof_mode(self) -> None:
        declarations = completeness._boundary_proof_declarations(
            "liuyao",
            ["moving_lines", "hexagram_catalog", "random_cast_lifecycle"],
        )

        self.assertEqual(
            declarations,
            [
                {
                    "category": "hexagram_catalog",
                    "proof_mode": "algorithm_invariant",
                    "proof_id": "liuyao.plate.hexagram-palace-shiying",
                },
                {
                    "category": "moving_lines",
                    "proof_mode": "provider_replay",
                    "proof_id": "provider_replay:liuyao:moving_lines",
                },
                {
                    "category": "random_cast_lifecycle",
                    "proof_mode": "transaction_lifecycle",
                    "proof_id": "liuyao.transaction.random-cast-lifecycle",
                },
            ],
        )

    def test_algorithm_boundary_proofs_require_exact_dedicated_counts(self) -> None:
        contracts = {
            ("liuyao", "hexagram_catalog"): ("hexagrams", 64),
            ("liuyao", "xunkong_cycle"): ("xunkong_boundaries", 6),
            ("liuyao", "six_spirit_day_stem"): ("day_stem_boundaries", 10),
            ("fengshui", "compass_boundary"): ("compass_boundary_checks", 48),
        }
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        for (system, category), (count_field, expected) in contracts.items():
            with self.subTest(system=system, category=category):
                entry = copy.deepcopy(payload["providers"][system])
                self.assertEqual(entry["dedicated_audit"]["counts"][count_field], expected)
                entry["dedicated_audit"]["counts"][count_field] = expected - 1

                summary = self._matrix_summary(system, category, entry=entry)

                self.assertFalse(summary["ready"], summary)
                self.assertTrue(any(count_field in item for item in summary["findings"]))

    def test_algorithm_boundary_proofs_reject_nonzero_mismatch_counts(self) -> None:
        contracts = {
            ("liuyao", "hexagram_catalog"): "provider_mismatches",
            ("liuyao", "xunkong_cycle"): "provider_mismatches",
            ("liuyao", "six_spirit_day_stem"): "provider_mismatches",
            ("fengshui", "compass_boundary"): "compass_boundary_mismatches",
        }
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        for (system, category), mismatch_field in contracts.items():
            with self.subTest(system=system, category=category):
                entry = copy.deepcopy(payload["providers"][system])
                entry["dedicated_audit"]["counts"][mismatch_field] = 1

                summary = self._matrix_summary(system, category, entry=entry)

                self.assertFalse(summary["ready"], summary)
                self.assertTrue(any(mismatch_field in item for item in summary["findings"]))

        fengshui = copy.deepcopy(payload["providers"]["fengshui"])
        fengshui["dedicated_audit"]["counts"]["compass_reference_mismatches"] = 1
        summary = self._matrix_summary(
            "fengshui",
            "compass_boundary",
            entry=fengshui,
        )
        self.assertFalse(summary["ready"], summary)
        self.assertTrue(
            any("compass_reference_mismatches" in item for item in summary["findings"])
        )

    def test_readiness_ignores_self_reported_category_without_a_provider_case(
        self,
    ) -> None:
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        entry = copy.deepcopy(payload["providers"]["bazi"])
        entry["fixtures"]["boundary_categories"].append("self_reported_only")
        entry["dedicated_runtime_replay"]["fixture_boundary_categories"].append(
            "self_reported_only"
        )
        entry["dedicated_runtime_replay"]["provider_boundary_categories"].append(
            "self_reported_only"
        )

        findings = completeness._entry_readiness_findings("bazi", entry)

        self.assertTrue(
            any("self_reported_only" in item and "no provider case" in item for item in findings),
            findings,
        )

    @staticmethod
    def _matrix_summary(
        system: str,
        category: str,
        *,
        entry: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if entry is None:
            payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
            entry = copy.deepcopy(payload["providers"][system])
        return completeness._boundary_proof_summary(
            system,
            declared_categories=[category],
            proof_declarations=completeness._boundary_proof_declarations(
                system,
                [category],
            ),
            dedicated_runtime_replay=entry["dedicated_runtime_replay"],
            dedicated_counts=entry["dedicated_audit"]["counts"],
            algorithm=entry["algorithm"],
            transaction_lifecycle=entry["transaction_lifecycle"],
        )

    def test_aggregate_boundary_proofs_bind_fixed_cases_and_counts(self) -> None:
        contracts = {
            "liuyao": {
                "calendar_witness": "complete_reference_cases",
                "moving_lines": "moving_boundaries",
            },
            "liuren": {"classical_source_plate": "complete_source_plates"},
            "qimen": {"external_reference": "external_reference_boards"},
            "taiyi": {"annual_external_reference": "external_reference_boards"},
            "meihua": {
                "calendar_witness": "calendar_boundaries",
                "seasonal_profile": "seasonal_profiles",
            },
            "fengshui": {
                "complete": "complete_observation_fixtures",
                "correction": "complete_observation_fixtures",
                "missing": "partial_fixtures",
            },
            "physiognomy": {
                "complete": "complete_fixtures",
                "conflict": "boundary_fixtures",
                "correction": "boundary_fixtures",
                "low_quality": "boundary_fixtures",
                "missing": "boundary_fixtures",
            },
        }
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        for system, categories in contracts.items():
            for category, count_field in categories.items():
                with self.subTest(system=system, category=category):
                    entry = copy.deepcopy(payload["providers"][system])
                    summary = self._matrix_summary(system, category, entry=entry)
                    self.assertTrue(summary["ready"], summary)

                    entry["dedicated_audit"]["counts"][count_field] = -1
                    mutated = self._matrix_summary(system, category, entry=entry)
                    self.assertFalse(mutated["ready"], mutated)
                    self.assertTrue(
                        any("count" in item for item in mutated["findings"]),
                        mutated,
                    )

    def test_observation_fixture_minimum_allows_additional_verified_cases(self) -> None:
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        entry = copy.deepcopy(payload["providers"]["fengshui"])
        template = next(
            row
            for row in entry["dedicated_runtime_replay"]["case_replays"]
            if str(row.get("case_id") or "").startswith("FS-O")
        )
        extra = copy.deepcopy(template)
        extra["case_id"] = "FS-O21"
        entry["dedicated_runtime_replay"]["case_replays"].append(extra)
        entry["dedicated_audit"]["counts"]["complete_observation_fixtures"] = 21

        summary = self._matrix_summary("fengshui", "complete", entry=entry)

        self.assertTrue(summary["ready"], summary)
        self.assertEqual(len(summary["proofs"][0]["case_ids"]), 21)

    def test_aggregate_boundary_proofs_reject_missing_or_not_ready_cases(self) -> None:
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        for system, category in (
            ("liuyao", "moving_lines"),
            ("liuren", "classical_source_plate"),
            ("qimen", "external_reference"),
            ("taiyi", "annual_external_reference"),
            ("meihua", "calendar_witness"),
            ("fengshui", "correction"),
            ("physiognomy", "conflict"),
        ):
            with self.subTest(system=system, category=category):
                entry = copy.deepcopy(payload["providers"][system])
                rows = entry["dedicated_runtime_replay"]["case_replays"]
                boundary_rows = entry["dedicated_runtime_replay"][
                    "provider_boundary_replays"
                ]
                target = (rows or boundary_rows)[0]
                if system == "liuyao":
                    target = next(row for row in rows if row["case_id"] == "stable-all-yang")
                elif system == "fengshui":
                    target = next(row for row in rows if row["case_id"] == "FS-O20")
                elif system in {"physiognomy", "meihua"}:
                    target = next(
                        row
                        for row in boundary_rows
                        if {
                            "conflict": "contradictory",
                            "calendar_witness": "solar_term_boundary",
                        }[category]
                        in row["categories"]
                    )
                target["ready"] = False
                summary = self._matrix_summary(system, category, entry=entry)
                self.assertFalse(summary["ready"], summary)
                self.assertTrue(any("not ready" in item for item in summary["findings"]))

                missing = copy.deepcopy(payload["providers"][system])
                for collection in ("case_replays", "provider_boundary_replays"):
                    missing["dedicated_runtime_replay"][collection] = [
                        row
                        for row in missing["dedicated_runtime_replay"][collection]
                        if row["case_id"] != target["case_id"]
                    ]
                missing_summary = self._matrix_summary(
                    system,
                    category,
                    entry=missing,
                )
                self.assertFalse(missing_summary["ready"], missing_summary)
                self.assertTrue(
                    any("case count" in item for item in missing_summary["findings"]),
                    missing_summary,
                )

    def test_horizon_boundary_proofs_require_the_exact_observed_kind_and_count(
        self,
    ) -> None:
        for system, categories, case_count in (
            ("liuren", ("day", "instant", "month"), 13),
            ("selection", ("day", "month", "year"), 10),
        ):
            for category in categories:
                with self.subTest(system=system, category=category):
                    rows = [
                        {
                            "case_id": f"{category}-{index}",
                            "ready": True,
                            "fixture_input_bound": True,
                            "extension_replay_ready": True,
                            "extension_horizon_kinds": [category],
                        }
                        for index in range(case_count)
                    ]
                    runtime = {
                        "case_replay_ready": True,
                        "provider_boundary_replay_ready": True,
                        "case_replays": rows,
                        "provider_boundary_replays": [],
                    }
                    summary = completeness._boundary_proof_summary(
                        system,
                        declared_categories=[category],
                        proof_declarations=completeness._boundary_proof_declarations(
                            system,
                            [category],
                        ),
                        dedicated_runtime_replay=runtime,
                        dedicated_counts={
                            "provider_extensions": 2 * case_count,
                            "route_owned_cases": 3 * case_count,
                        },
                        algorithm={},
                        transaction_lifecycle={},
                    )
                    self.assertTrue(summary["ready"], summary)

                    rows[0]["extension_horizon_kinds"] = ["wrong-kind"]
                    mutated = completeness._boundary_proof_summary(
                        system,
                        declared_categories=[category],
                        proof_declarations=completeness._boundary_proof_declarations(
                            system,
                            [category],
                        ),
                        dedicated_runtime_replay=runtime,
                        dedicated_counts={
                            "provider_extensions": 2 * case_count,
                            "route_owned_cases": 3 * case_count,
                        },
                        algorithm={},
                        transaction_lifecycle={},
                    )
                    self.assertFalse(mutated["ready"], mutated)
                    self.assertTrue(any("horizon kind" in item for item in mutated["findings"]))

    def test_selection_external_reference_binds_all_fixed_replays_and_oracles(
        self,
    ) -> None:
        entry = copy.deepcopy(
            yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))["providers"][
                "selection"
            ]
        )
        summary = self._matrix_summary(
            "selection",
            "external_reference",
            entry=entry,
        )
        self.assertTrue(summary["ready"], summary)

        entry["dedicated_audit"]["counts"]["external_unexplained_mismatches"] = 1
        mutated = self._matrix_summary(
            "selection",
            "external_reference",
            entry=entry,
        )
        self.assertFalse(mutated["ready"], mutated)
        self.assertTrue(any("mismatch" in item for item in mutated["findings"]))


class CanonicalMatrixSnapshotTests(unittest.TestCase):
    """The live matrix is built once per process and compared with the checked file."""

    @classmethod
    def _live_canonical(cls) -> dict[str, object]:
        cached = cls.__dict__.get("_live_canonical_cache")
        if cached is None:
            cached = completeness.build_matrix(root=ROOT)
            cls._live_canonical_cache = cached
        return cached

    def test_checked_matrix_is_the_canonical_live_snapshot(self) -> None:
        canonical = self._live_canonical()
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        report = completeness.audit_matrix(
            payload,
            root=ROOT,
            canonical=canonical,
        )

        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["findings"], [])
        self.assertEqual(set(payload["providers"]), EXPECTED_SYSTEMS)
        self.assertEqual(
            completeness.render_matrix(canonical),
            MATRIX_PATH.read_text(encoding="utf-8"),
        )

    def test_ready_cannot_be_asserted_by_mutating_the_checked_file(self) -> None:
        canonical = self._live_canonical()
        mutated = copy.deepcopy(canonical)
        mutated["providers"]["fortune"]["ready"] = True
        mutated["providers"]["fortune"]["fixtures"]["qualifying_cases"] = 29

        report = completeness.audit_matrix(
            mutated,
            root=ROOT,
            canonical=canonical,
        )

        self.assertFalse(report["provider_ready"])
        self.assertTrue(
            any("fortune" in finding and "fixture" in finding for finding in report["findings"]),
            report,
        )


class ProviderCompletenessMatrixTests(unittest.TestCase):
    def test_fixture_case_aliases_include_route_owned_audit_labels(self) -> None:
        self.assertEqual(
            completeness._fixture_case_id_aliases({"lx-01"}),
            {
                "lx-01",
                "source-example-lx-01",
                "taiyuan-lx-01",
                "calendar-lx-01",
            },
        )

    def test_release_contract_pins_all_thirteen_provider_identities(self) -> None:
        self.assertEqual(
            completeness.EXPECTED_PROVIDER_IDENTITIES,
            EXPECTED_PROVIDER_IDENTITIES,
        )
        for system, expected in EXPECTED_PROVIDER_IDENTITIES.items():
            with self.subTest(system=system):
                runtime = completeness._provider_runtime(system)
                self.assertEqual(
                    (
                        runtime["expected_class"],
                        runtime["expected_provider_id"],
                        runtime["expected_provider_version"],
                    ),
                    expected,
                )
                self.assertTrue(runtime["identity_matches"], runtime)

    def test_provider_id_and_version_mutations_fail_the_release_contract(self) -> None:
        for system, provider_class in completeness.PROVIDER_CLASSES.items():
            for field, drifted in (
                ("provider_id", "mingli-master.drifted.v0"),
                ("provider_version", "drifted-version"),
            ):
                with self.subTest(system=system, field=field), mock.patch.object(
                    provider_class,
                    field,
                    drifted,
                ):
                    runtime = completeness._provider_runtime(system)
                    self.assertFalse(runtime["identity_matches"], runtime)

    def test_entry_readiness_compares_runtime_and_dedicated_identity_to_release_contract(
        self,
    ) -> None:
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        entry = copy.deepcopy(payload["providers"]["taiyi"])
        entry["runtime"]["identity_matches"] = False
        entry["dedicated_audit"].setdefault("provider", {})["provider_id"] = (
            "mingli-master.qimen.v1"
        )

        findings = completeness._entry_readiness_findings("taiyi", entry)

        self.assertTrue(
            any("release provider identity" in item for item in findings),
            findings,
        )
        self.assertTrue(
            any("dedicated provider identity" in item for item in findings),
            findings,
        )

    def test_liuren_readiness_requires_runtime_calendar_identity_match(self) -> None:
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        entry = copy.deepcopy(payload["providers"]["liuren"])
        entry["algorithm"]["runtime_identity_matches"] = False
        entry["dedicated_audit"]["calendar_month_general_closure_ready"] = False

        findings = completeness._entry_readiness_findings("liuren", entry)

        self.assertTrue(
            any("runtime algorithm identity" in item for item in findings),
            findings,
        )
        self.assertTrue(
            any("calendar/month-general closure" in item for item in findings),
            findings,
        )

    def test_dedicated_audit_projection_preserves_liuren_closure_evidence(self) -> None:
        report = {
            "schema_version": "liuren-audit-v1",
            "system": "liuren",
            "status": "pass",
            "provider_ready": True,
            "provider": {"provider_id": "liuren"},
            "counts": {"cases": 1},
            "findings": [],
            "calendar_month_general_closure_ready": True,
        }

        projected = completeness._dedicated_audit_projection(report)

        self.assertIs(
            projected["calendar_month_general_closure_ready"],
            True,
        )

    def test_readiness_counts_distinct_effective_inputs_not_query_labels(self) -> None:
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        entry = copy.deepcopy(payload["providers"]["bazi"])
        entry["dedicated_runtime_replay"]["distinct_effective_case_digests"] = 1
        entry["dedicated_runtime_replay"]["effective_cases_are_distinct"] = False

        findings = completeness._entry_readiness_findings("bazi", entry)

        self.assertTrue(
            any("distinct_effective_inputs" in item for item in findings),
            findings,
        )

    def test_audit_reuses_explicit_canonical_without_rebuilding(self) -> None:
        canonical = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(canonical)
        mutated["providers"]["fortune"]["fixtures"]["qualifying_cases"] = 0

        with mock.patch.object(
            completeness,
            "build_matrix",
            side_effect=AssertionError("canonical must not be rebuilt"),
        ):
            report = completeness.audit_matrix(
                mutated,
                root=ROOT,
                canonical=canonical,
            )

        self.assertFalse(report["provider_ready"], report)
        self.assertTrue(
            any("fortune" in finding for finding in report["findings"]),
            report,
        )

    def test_canonical_matrix_ignores_and_restores_external_research_root(
        self,
    ) -> None:
        observed_roots: list[str | None] = []

        def fake_build(root_text: str, fingerprint: str) -> dict[str, object]:
            self.assertTrue(root_text)
            self.assertEqual(fingerprint, "fixed-fingerprint")
            observed_roots.append(os.environ.get("MINGLI_RESEARCH_ROOT"))
            return {"portable": True}

        configured_root = "/private/external-research"
        with mock.patch.dict(
            os.environ,
            {
                "MINGLI_RESEARCH_ROOT": configured_root,
                "MINGLI_MATRIX_JOBS": "1",
            },
        ), mock.patch.object(
            completeness,
            "_matrix_input_fingerprint",
            return_value="fixed-fingerprint",
        ), mock.patch.object(
            completeness,
            "_build_matrix_uncached",
            side_effect=fake_build,
        ):
            payload = completeness.build_matrix(root=ROOT)
            restored = os.environ.get("MINGLI_RESEARCH_ROOT")

        self.assertEqual(payload, {"portable": True})
        self.assertEqual(observed_roots, [None])
        self.assertEqual(restored, configured_root)

    def test_matrix_build_disables_and_restores_bytecode_writes(self) -> None:
        observed_guards: list[str | None] = []

        def fake_build(root_text: str, fingerprint: str) -> dict[str, object]:
            self.assertTrue(root_text)
            self.assertEqual(fingerprint, "fixed-fingerprint")
            observed_guards.append(os.environ.get("PYTHONDONTWRITEBYTECODE"))
            return {"guarded": True}

        previous_guard = os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
        try:
            with mock.patch.dict(
                os.environ,
                {"MINGLI_MATRIX_JOBS": "1"},
            ), mock.patch.object(
                completeness,
                "_matrix_input_fingerprint",
                return_value="fixed-fingerprint",
            ), mock.patch.object(
                completeness,
                "_build_matrix_uncached",
                side_effect=fake_build,
            ):
                payload = completeness.build_matrix(root=ROOT)
                restored = os.environ.get("PYTHONDONTWRITEBYTECODE")
        finally:
            if previous_guard is not None:
                os.environ["PYTHONDONTWRITEBYTECODE"] = previous_guard

        self.assertEqual(payload, {"guarded": True})
        self.assertEqual(observed_guards, ["1"])
        self.assertIsNone(restored)

    def test_matrix_fingerprint_ignores_tests_but_tracks_runtime_scripts(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir()
            runtime = scripts / "runtime_probe.py"
            runtime.write_text("VALUE = 1\n", encoding="utf-8")
            before = completeness._matrix_input_fingerprint(root)

            (scripts / "test_runtime_probe.py").write_text(
                "assert True\n",
                encoding="utf-8",
            )
            after_test = completeness._matrix_input_fingerprint(root)
            (scripts / "run_test_suite.py").write_text(
                "# scheduling-only infrastructure\n",
                encoding="utf-8",
            )
            after_runner = completeness._matrix_input_fingerprint(root)
            runtime.write_text("VALUE = 2\n", encoding="utf-8")
            after_runtime = completeness._matrix_input_fingerprint(root)

        self.assertEqual(after_test, before)
        self.assertEqual(after_runner, before)
        self.assertNotEqual(after_runtime, before)

    def test_provider_partition_merge_is_ordered_and_complete(self) -> None:
        systems = ("first", "second")
        partitions = {
            "second": {"providers": {"second": {"ready": True}}},
            "first": {"providers": {"first": {"ready": True}}},
        }

        merged = completeness._merge_provider_partitions(systems, partitions)

        self.assertEqual(list(merged["providers"]), list(systems))
        with self.assertRaisesRegex(ValueError, "missing provider partition"):
            completeness._merge_provider_partitions(
                systems,
                {"first": partitions["first"]},
            )

    def test_matrix_jobs_are_bounded_and_reject_invalid_configuration(self) -> None:
        with mock.patch.dict(os.environ, {"MINGLI_MATRIX_JOBS": "99"}):
            self.assertEqual(completeness._matrix_jobs(13), 13)
        with mock.patch.dict(os.environ, {"MINGLI_MATRIX_JOBS": "0"}):
            with self.assertRaisesRegex(ValueError, "MINGLI_MATRIX_JOBS"):
                completeness._matrix_jobs(13)

    def test_readiness_requires_explicit_fixture_identity_and_route_replay(self) -> None:
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        entry = copy.deepcopy(payload["providers"]["liuyao"])
        entry["fixtures"]["dedicated_reported_sha256"] = None
        entry["fixtures"]["dedicated_hash_matches"] = True
        entry["fixtures"]["route_owned_cases"] = 0
        entry["dedicated_audit"]["system"] = "not-liuyao"
        entry["dedicated_audit"]["provider"] = {
            "provider_id": "invented",
            "provider_version": "invented",
        }

        findings = completeness._entry_readiness_findings("liuyao", entry)

        self.assertTrue(any("fixture sha256" in item for item in findings), findings)
        self.assertTrue(any("route-owned" in item for item in findings), findings)
        self.assertTrue(any("dedicated audit system" in item for item in findings), findings)
        self.assertTrue(any("dedicated provider identity" in item for item in findings), findings)

    def test_matrix_cache_key_changes_when_any_input_artifact_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "references").mkdir()
            probe = root / "references" / "probe.yaml"
            probe.write_text("value: one\n", encoding="utf-8")
            first = completeness._matrix_input_fingerprint(root)
            probe.write_text("value: two\n", encoding="utf-8")
            second = completeness._matrix_input_fingerprint(root)

        self.assertNotEqual(first, second)

    def test_matrix_build_rejects_inputs_that_drift_during_generation(self) -> None:
        with mock.patch.object(
            completeness,
            "EXPECTED_SYSTEMS",
            (),
        ), mock.patch.object(
            completeness.audit_algorithm_sources,
            "audit_matrix",
            return_value={"ok": True, "systems": {}},
        ), mock.patch.object(
            completeness,
            "_matrix_input_fingerprint",
            side_effect=("start-fingerprint", "end-fingerprint"),
        ):
            with self.assertRaisesRegex(ValueError, "changed during generation"):
                completeness._build_matrix_uncached(
                    str(ROOT),
                    "start-fingerprint",
                )

    def test_matrix_binds_the_release_runtime_integrity_artifacts(self) -> None:
        with mock.patch.object(
            completeness,
            "EXPECTED_SYSTEMS",
            (),
        ), mock.patch.object(
            completeness.audit_algorithm_sources,
            "audit_matrix",
            return_value={"ok": True, "systems": {}},
        ):
            payload = completeness.build_matrix(root=ROOT)
        artifacts = payload["inputs"]["runtime_integrity_artifacts"]
        expected_paths = {
            "requirements-runtime.lock",
            "requirements-runtime-build.lock",
            "scripts/runtime_python.py",
            "scripts/runtime_launcher.py",
            "scripts/provision_runtime.py",
            "scripts/run_reading_transaction.sh",
        }

        self.assertEqual(set(artifacts), expected_paths)
        for relative, digest in artifacts.items():
            self.assertEqual(
                digest,
                hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
            )
        self.assertTrue(payload["policy"]["runtime_preimport_integrity_required"])
        self.assertTrue(payload["policy"]["hash_locked_runtime_required"])

    def test_write_mode_never_publishes_a_failed_matrix(self) -> None:
        generated = {
            "inputs": {"generator_input_fingerprint": "a" * 64},
            "providers": {},
        }
        failed_report = {
            "schema_version": "mingli-provider-completeness-audit-v1",
            "provider_ready": False,
            "provider_count": 0,
            "findings": ["mutation probe"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            matrix_path = Path(temporary) / "provider-completeness.yaml"
            with mock.patch.object(
                completeness,
                "build_matrix",
                return_value=generated,
            ), mock.patch.object(
                completeness,
                "render_matrix",
                return_value="failed: true\n",
            ), mock.patch.object(
                completeness,
                "audit_matrix",
                return_value=failed_report,
            ):
                return_code = completeness.main(
                    ["--write", "--matrix", str(matrix_path)]
                )

            self.assertEqual(return_code, 1)
            self.assertFalse(matrix_path.exists())

    def test_main_audits_the_generated_matrix_without_rebuilding(self) -> None:
        generated = {
            "inputs": {"generator_input_fingerprint": "a" * 64},
            "providers": {},
        }
        ready_report = {
            "schema_version": "mingli-provider-completeness-audit-v1",
            "provider_ready": True,
            "provider_count": 0,
            "findings": [],
        }
        observed: dict[str, object] = {}

        def fake_audit(payload, *, root, canonical=None):
            observed["payload"] = payload
            observed["canonical"] = canonical
            return ready_report

        with tempfile.TemporaryDirectory() as temporary:
            matrix_path = Path(temporary) / "provider-completeness.yaml"
            matrix_path.write_text("rendered: true\n", encoding="utf-8")
            with mock.patch.object(
                completeness,
                "build_matrix",
                return_value=generated,
            ) as build_mock, mock.patch.object(
                completeness,
                "render_matrix",
                return_value="rendered: true\n",
            ), mock.patch.object(
                completeness,
                "audit_matrix",
                side_effect=fake_audit,
            ):
                return_code = completeness.main(
                    ["--check", "--matrix", str(matrix_path)]
                )

        self.assertEqual(return_code, 0)
        self.assertEqual(build_mock.call_count, 1)
        self.assertIs(observed["payload"], generated)
        self.assertIs(observed["canonical"], generated)

    def test_liuyao_readiness_replays_the_private_random_cast_lifecycle(self) -> None:
        report = completeness.audit_liuyao_transaction_lifecycle(root=ROOT)

        self.assertTrue(report["ready"], report)
        self.assertTrue(report["fresh_casts_are_distinct"], report)
        self.assertTrue(report["restart_replay_matches"], report)
        self.assertTrue(report["continue_preserves_cast"], report)
        self.assertTrue(report["continue_preserves_chart_facts"], report)
        self.assertTrue(report["continue_skips_recalculation"], report)
        self.assertTrue(report["correct_preserves_cast"], report)
        self.assertTrue(report["cast_correction_requires_recast"], report)
        self.assertTrue(report["public_seed_redacted"], report)
        self.assertTrue(report["seed_values_match_csprng_calls"], report)
        self.assertTrue(report["all_public_contracts_seed_redacted"], report)
        self.assertTrue(report["recast_restart_replay_matches"], report)
        self.assertTrue(report["public_casting_schema_exact"], report)
        self.assertTrue(report["supplied_to_digital_requires_recast"], report)
        self.assertTrue(report["supplied_toss_change_requires_recast"], report)
        self.assertTrue(report["digital_toss_injection_requires_recast"], report)
        self.assertTrue(report["same_cast_correction_preserves_cast"], report)
        self.assertEqual(report["random_seed_calls"], 2)

    def test_liuyao_entry_cannot_be_ready_without_transaction_lifecycle(self) -> None:
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        entry = copy.deepcopy(payload["providers"]["liuyao"])
        entry["transaction_lifecycle"] = {
            "ready": False,
            "findings": ["mutation probe"],
        }

        findings = completeness._entry_readiness_findings("liuyao", entry)

        self.assertTrue(
            any("transaction lifecycle" in item for item in findings),
            findings,
        )

    def test_liuyao_entry_requires_the_complete_random_cast_contract(self) -> None:
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        entry = copy.deepcopy(payload["providers"]["liuyao"])
        proof_names = (
            "new_seed_format_valid",
            "new_seed_not_reading_id_derived",
            "public_contract_seed_redacted",
            "stored_request_seed_redacted",
            "private_calculation_seed_persisted",
            "restart_replay_exact",
            "continuation_seed_reused",
            "correction_seed_reused",
            "recast_created_new_reading",
            "recast_seed_distinct",
            "seed_commitment_verified",
            "public_report_seed_redacted",
        )
        valid_contract = {
            "schema_version": "mingli-liuyao-random-cast-contract-v1",
            "ready": True,
            "new_cast_count": 2,
            "token_hex_call_count": 2,
            "token_hex_32_byte_requests": 2,
            **{name: True for name in proof_names},
        }
        entry["dedicated_audit"]["random_cast_contract"] = valid_contract
        valid_findings = completeness._entry_readiness_findings("liuyao", entry)
        self.assertFalse(
            any("random cast contract" in item for item in valid_findings),
            valid_findings,
        )

        for field in (*proof_names, "ready"):
            with self.subTest(field=field):
                mutated = copy.deepcopy(entry)
                mutated["dedicated_audit"]["random_cast_contract"][field] = False
                findings = completeness._entry_readiness_findings("liuyao", mutated)
                self.assertTrue(
                    any("random cast contract" in item for item in findings),
                    findings,
                )

        missing = copy.deepcopy(entry)
        missing["dedicated_audit"].pop("random_cast_contract")
        findings = completeness._entry_readiness_findings("liuyao", missing)
        self.assertTrue(
            any("random cast contract" in item for item in findings),
            findings,
        )

    def test_dedicated_self_report_without_observed_provider_calls_is_not_ready(self) -> None:
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        entry = copy.deepcopy(payload["providers"]["bazi"])
        entry["dedicated_runtime_replay"] = {
            "calculation_runs": 0,
            "distinct_input_hashes": 0,
            "deterministic_input_replays": 0,
            "provider_identity_matches": False,
            "findings": ["no observed calls"],
        }

        findings = completeness._entry_readiness_findings("bazi", entry)

        self.assertTrue(
            any("observed dedicated provider replay" in item for item in findings),
            findings,
        )

    def test_dedicated_fail_status_and_malformed_sections_fail_closed(self) -> None:
        payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        entry = copy.deepcopy(payload["providers"]["bazi"])
        entry["dedicated_audit"]["status"] = "fail"
        findings = completeness._entry_readiness_findings("bazi", entry)
        self.assertTrue(any("status is not pass" in item for item in findings))

        for section in ("fixtures", "dedicated_audit", "source_applicability"):
            malformed = copy.deepcopy(entry)
            malformed[section] = ["not", "an", "object"]
            with self.subTest(section=section):
                findings = completeness._entry_readiness_findings("bazi", malformed)
                self.assertTrue(
                    any(f"{section} must be an object" in item for item in findings),
                    findings,
                )

    def test_dedicated_runtime_observer_preserves_the_original_provider_class(self) -> None:
        class FakeProvider:
            provider_id = "mingli-master.fake.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                if request.query == "fixture-reject":
                    raise ValueError("deterministic rejection")
                return CalculationResult.create(
                    system="fake",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"request": str(request)},
                    facts={"value": "stable"},
                )

        module = SimpleNamespace(__name__="audit_fake", FakeProvider=FakeProvider)

        def audit_fake(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            identity_preserved = module.FakeProvider is FakeProvider
            provider = module.FakeProvider()
            label = "fixture-case-1"
            case_id = label
            provider.calculate(
                ReadingRequest(
                    query=f"one {label}",
                    system="fake",
                    chart_data={"case": 1},
                )
            )
            provider.calculate(
                ReadingRequest(
                    query=f"one {label}",
                    system="fake",
                    chart_data={"case": 1},
                )
            )
            for _ in range(2):
                try:
                    provider.calculate(
                        ReadingRequest(
                            query="fixture-reject",
                            system="fake",
                            chart_data={"case": 2},
                        )
                    )
                except ValueError:
                    pass
            return {
                "schema_version": "fake-audit-v1",
                "provider_ready": identity_preserved,
                "status": "pass" if identity_preserved else "fail",
                "route_owned_case_ids": [label],
                "counts": {},
                "findings": [] if identity_preserved else ["provider class replaced"],
            }

        module.audit_fake = audit_fake
        expected_identity = (
            f"{FakeProvider.__module__}.{FakeProvider.__qualname__}",
            FakeProvider.provider_id,
            FakeProvider.provider_version,
        )
        report, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=FakeProvider,
            fixture_path=Path("unused"),
            expected_system="fake",
            expected_identity=expected_identity,
            known_case_ids={"fixture-case-1", "fixture-reject"},
            case_categories={
                "fixture-case-1": {"edge"},
                "fixture-reject": {"invalid_edge"},
            },
        )

        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(telemetry["calculation_runs"], 4)
        self.assertEqual(telemetry["deterministic_input_replays"], 1)
        self.assertTrue(telemetry["provider_identity_matches"], telemetry)
        self.assertTrue(telemetry["case_ids_fixture_bound"], telemetry)
        self.assertTrue(telemetry["case_replay_ready"], telemetry)
        self.assertEqual(telemetry["provider_boundary_case_count"], 1)
        self.assertEqual(telemetry["provider_boundary_rejection_case_count"], 1)
        self.assertEqual(
            telemetry["provider_boundary_categories"],
            ["edge", "invalid_edge"],
        )
        self.assertTrue(telemetry["provider_boundary_replay_ready"])

        _, unbound_telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=FakeProvider,
            fixture_path=Path("unused"),
            expected_system="fake",
            expected_identity=expected_identity,
            known_case_ids=set(),
            case_categories={},
        )
        self.assertFalse(unbound_telemetry["case_ids_fixture_bound"])
        self.assertTrue(
            any("fixture-bound" in item for item in unbound_telemetry["findings"]),
            unbound_telemetry,
        )

        with mock.patch.object(
            FakeProvider,
            "provider_id",
            "mingli-master.drifted.v0",
        ):
            _, drifted_telemetry = completeness._run_dedicated_provider_audit(
                module=module,
                provider_class=FakeProvider,
                fixture_path=Path("unused"),
                expected_system="fake",
                expected_identity=expected_identity,
                known_case_ids={"fixture-case-1", "fixture-reject"},
                case_categories={
                    "fixture-case-1": {"edge"},
                    "fixture-reject": {"invalid_edge"},
                },
            )
        self.assertFalse(
            drifted_telemetry["provider_identity_matches"],
            drifted_telemetry,
        )

        original_calculate = FakeProvider.calculate

        def drifted_system_calculate(
            self: FakeProvider,
            request: ReadingRequest,
        ) -> CalculationResult:
            return replace(
                original_calculate(self, request),
                system="drifted-system",
            )

        with mock.patch.object(
            FakeProvider,
            "calculate",
            drifted_system_calculate,
        ):
            _, drifted_system_telemetry = (
                completeness._run_dedicated_provider_audit(
                    module=module,
                    provider_class=FakeProvider,
                    fixture_path=Path("unused"),
                    expected_system="fake",
                    expected_identity=expected_identity,
                    known_case_ids={"fixture-case-1", "fixture-reject"},
                    case_categories={
                        "fixture-case-1": {"edge"},
                        "fixture-reject": {"invalid_edge"},
                    },
                )
            )
        self.assertFalse(
            drifted_system_telemetry["provider_identity_matches"],
            drifted_system_telemetry,
        )

    def test_rejected_observation_boundaries_bind_without_a_result_payload(self) -> None:
        for system in ("fengshui", "physiognomy"):
            with self.subTest(system=system):
                module = completeness.DEDICATED_AUDIT_MODULES[system]
                fixture_path = Path(module.FIXTURE)
                fixture = completeness._load_yaml(fixture_path)
                bindings = completeness._fixture_case_bindings(
                    fixture,
                    system=system,
                )
                for case_id, binding in completeness._module_fixture_case_bindings(
                    module,
                    root=ROOT,
                    system=system,
                ).items():
                    bindings[case_id] = binding
                case_ids = completeness._fixture_case_ids(fixture)
                case_ids.update(
                    completeness._module_fixture_case_ids(module, root=ROOT)
                )
                case_ids = completeness._fixture_case_id_aliases(case_ids)
                categories = completeness._fixture_case_categories(fixture)
                for case_id, names in completeness._module_fixture_case_categories(
                    module,
                    root=ROOT,
                ).items():
                    categories.setdefault(case_id, set()).update(names)
                categories = completeness._fixture_case_category_aliases(categories)

                _, telemetry = completeness._run_dedicated_provider_audit(
                    module=module,
                    provider_class=completeness.PROVIDER_CLASSES[system],
                    fixture_path=fixture_path,
                    expected_system=system,
                    expected_identity=completeness.EXPECTED_PROVIDER_IDENTITIES[system],
                    known_case_ids=case_ids,
                    case_categories=categories,
                    fixture_case_bindings=bindings,
                )

                rejected = [
                    row
                    for row in telemetry["provider_boundary_replays"]
                    if row["outcome"] == "rejection"
                ]
                self.assertTrue(rejected, telemetry)
                self.assertTrue(all(row["fixture_input_bound"] for row in rejected))
                self.assertTrue(telemetry["provider_boundary_replay_ready"], telemetry)

    def test_ziwei_effective_case_identity_includes_extension_dimensions(self) -> None:
        system = "ziwei"
        module = completeness.DEDICATED_AUDIT_MODULES[system]
        fixture_path = Path(module.FIXTURE)
        fixture = completeness._load_yaml(fixture_path)
        bindings = completeness._fixture_case_bindings(fixture, system=system)
        for case_id, binding in completeness._module_fixture_case_bindings(
            module,
            root=ROOT,
            system=system,
        ).items():
            bindings[case_id] = binding
        case_ids = completeness._fixture_case_ids(fixture)
        case_ids.update(completeness._module_fixture_case_ids(module, root=ROOT))
        case_ids = completeness._fixture_case_id_aliases(case_ids)
        categories = completeness._fixture_case_categories(fixture)
        for case_id, names in completeness._module_fixture_case_categories(
            module,
            root=ROOT,
        ).items():
            categories.setdefault(case_id, set()).update(names)
        categories = completeness._fixture_case_category_aliases(categories)

        report, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=completeness.PROVIDER_CLASSES[system],
            fixture_path=fixture_path,
            expected_system=system,
            expected_identity=completeness.EXPECTED_PROVIDER_IDENTITIES[system],
            known_case_ids=case_ids,
            case_categories=categories,
            fixture_case_bindings=bindings,
        )

        route_count = len(report["route_owned_case_ids"])
        self.assertEqual(telemetry["distinct_effective_case_digests"], route_count)
        self.assertTrue(telemetry["case_replay_ready"], telemetry)
        self.assertTrue(telemetry["provider_boundary_replay_ready"], telemetry)

    def test_case_replay_rejects_reused_requests_under_distinct_fixture_ids(self) -> None:
        class ReusedRequestProvider:
            provider_id = "mingli-master.reused.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="reused",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload=request.to_dict(),
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_reused",
            ReusedRequestProvider=ReusedRequestProvider,
        )

        def audit_reused(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = ReusedRequestProvider()
            for case_id in ("case-a", "case-b"):
                for _ in range(2):
                    provider.calculate(
                        ReadingRequest(query="same request", system="reused")
                    )
            return {
                "schema_version": "reused-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        module.audit_reused = audit_reused
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=ReusedRequestProvider,
            fixture_path=Path("unused"),
            expected_system="reused",
            expected_identity=(
                f"{ReusedRequestProvider.__module__}."
                f"{ReusedRequestProvider.__qualname__}",
                ReusedRequestProvider.provider_id,
                ReusedRequestProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
        )

        self.assertEqual(telemetry["distinct_route_request_digests"], 0)
        self.assertFalse(telemetry["case_replay_ready"], telemetry)

    def test_case_replay_rejects_query_only_nonces_with_identical_calculation_inputs(self) -> None:
        class QueryNonceProvider:
            provider_id = "mingli-master.query-nonce.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="query-nonce",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload=request.to_dict(),
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_query_nonce",
            QueryNonceProvider=QueryNonceProvider,
        )

        def audit_query_nonce(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = QueryNonceProvider()
            for case_id in ("case-a", "case-b"):
                for _ in range(2):
                    provider.calculate(
                        ReadingRequest(
                            query=f"nonce {case_id}",
                            system="query-nonce",
                        )
                    )
            return {
                "schema_version": "query-nonce-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        module.audit_query_nonce = audit_query_nonce
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=QueryNonceProvider,
            fixture_path=Path("unused"),
            expected_system="query-nonce",
            expected_identity=(
                f"{QueryNonceProvider.__module__}."
                f"{QueryNonceProvider.__qualname__}",
                QueryNonceProvider.provider_id,
                QueryNonceProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
        )

        self.assertEqual(telemetry["distinct_route_request_digests"], 2)
        self.assertEqual(telemetry["distinct_calculation_request_digests"], 1)
        self.assertFalse(
            telemetry["calculation_request_cases_are_distinct"], telemetry
        )
        self.assertEqual(telemetry["distinct_effective_case_digests"], 1)
        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertFalse(telemetry["provider_boundary_replay_ready"], telemetry)

    def test_extension_replay_rejects_successful_horizon_nonces(self) -> None:
        class SuccessfulNonceProvider:
            provider_id = "mingli-master.successful-nonce.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"semantic": request.chart_data["semantic_case"]},
                    facts={"stable": True},
                )

            def extend(
                self,
                calculation: CalculationResult,
                requested_dimensions: tuple[str, ...],
                horizon: dict[str, object],
            ) -> CalculationResult:
                extension = FactExtensionResult.create(
                    system=calculation.system,
                    base_calculation_digest=calculation.base().result_hash,
                    requested_dimensions=requested_dimensions,
                    horizon=horizon,
                    status="complete",
                    facts={"stable": True},
                )
                return calculation.base().with_fact_extension(extension)

        module = SimpleNamespace(
            __name__="audit_successful_nonce",
            SuccessfulNonceProvider=SuccessfulNonceProvider,
        )

        def audit_successful_nonce(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = SuccessfulNonceProvider()
            for case_id in ("case-a", "case-b"):
                for _ in range(2):
                    calculation = provider.calculate(
                        ReadingRequest(
                            query=f"fixture {case_id}",
                            system="bazi",
                            chart_data={"semantic_case": "same"},
                        )
                    )
                    provider.extend(
                        calculation,
                        ("life",),
                        {"kind": "life", "audit_nonce": case_id},
                    )
            return {
                "schema_version": "successful-nonce-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        module.audit_successful_nonce = audit_successful_nonce
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=SuccessfulNonceProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{SuccessfulNonceProvider.__module__}."
                f"{SuccessfulNonceProvider.__qualname__}",
                SuccessfulNonceProvider.provider_id,
                SuccessfulNonceProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
        )

        self.assertEqual(telemetry["distinct_effective_case_digests"], 0)
        self.assertFalse(telemetry["case_replay_ready"], telemetry)

    def test_extension_fixture_cannot_pass_without_extension_calls(self) -> None:
        class MissingExtensionProvider:
            provider_id = "mingli-master.missing-extension.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="missing-extension",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"base": "stable"},
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_missing_extension",
            MissingExtensionProvider=MissingExtensionProvider,
        )

        def audit_missing_extension(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = MissingExtensionProvider()
            for _ in range(2):
                provider.calculate(
                    ReadingRequest(query="case-a", system="missing-extension")
                )
            return {
                "schema_version": "missing-extension-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a"],
                "counts": {},
                "findings": [],
            }

        module.audit_missing_extension = audit_missing_extension
        fixture = {
            "cases": [
                {
                    "id": "case-a",
                    "input": {"kind": "year", "start": 2024, "end": 2024},
                }
            ]
        }
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=MissingExtensionProvider,
            fixture_path=Path("unused"),
            expected_system="missing-extension",
            expected_identity=(
                f"{MissingExtensionProvider.__module__}."
                f"{MissingExtensionProvider.__qualname__}",
                MissingExtensionProvider.provider_id,
                MissingExtensionProvider.provider_version,
            ),
            known_case_ids={"case-a"},
            case_categories={"case-a": {"edge"}},
            fixture_case_bindings=completeness._fixture_case_bindings(fixture),
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertEqual(telemetry["distinct_effective_case_digests"], 0)

    def test_partial_extension_is_only_ready_for_observation_routes(self) -> None:
        extension = FactExtensionResult.create(
            system="fengshui",
            base_calculation_digest="base",
            requested_dimensions=("state", "direction"),
            horizon={"kind": "instant"},
            status="partial",
            facts={"observed": True},
            unsupported_dimensions=("state",),
        )

        self.assertTrue(
            completeness._extension_status_is_ready(
                extension,
                capability=completeness.PROVIDER_CAPABILITIES["fengshui"],
                requested_dimensions=("state", "direction"),
            )
        )
        self.assertFalse(
            completeness._extension_status_is_ready(
                extension,
                capability=completeness.PROVIDER_CAPABILITIES["bazi"],
                requested_dimensions=("state", "direction"),
            )
        )

    def test_complete_extension_requires_calculated_facts(self) -> None:
        extension = FactExtensionResult.create(
            system="bazi",
            base_calculation_digest="base",
            requested_dimensions=("timing",),
            horizon={"kind": "life"},
            status="complete",
            facts={},
        )

        self.assertFalse(
            completeness._extension_status_is_ready(
                extension,
                capability=completeness.PROVIDER_CAPABILITIES["bazi"],
                requested_dimensions=("timing",),
            )
        )

    def test_fixture_leaf_identity_preserves_paths_order_and_types(self) -> None:
        original = {"pillars": ["甲子", "乙丑"], "count": 1}

        self.assertNotEqual(
            completeness._semantic_input_leaves(original),
            completeness._semantic_input_leaves(
                {"wrong": ["甲子", "乙丑"], "count": 1}
            ),
        )
        self.assertNotEqual(
            completeness._semantic_input_leaves(original),
            completeness._semantic_input_leaves(
                {"pillars": ["乙丑", "甲子"], "count": 1}
            ),
        )
        self.assertNotEqual(
            completeness._semantic_input_leaves(original),
            completeness._semantic_input_leaves(
                {"pillars": ["甲子", "乙丑"], "count": "1"}
            ),
        )

    def test_structured_projection_rejects_wrong_paths_and_array_order(self) -> None:
        expected = {"chart_data": {"pillars": ["甲子", "乙丑"]}}

        self.assertTrue(
            completeness._payload_contains_projection(
                {"chart_data": {"pillars": ["甲子", "乙丑"], "extra": True}},
                expected,
            )
        )
        self.assertFalse(
            completeness._payload_contains_projection(
                {"chart_data": {"wrong": ["甲子", "乙丑"]}},
                expected,
            )
        )
        self.assertFalse(
            completeness._payload_contains_projection(
                {"chart_data": {"pillars": ["乙丑", "甲子"]}},
                expected,
            )
        )
        self.assertFalse(
            completeness._payload_contains_projection(
                {"liqi": {"unexpected": True}},
                {"liqi": {}},
            )
        )

    def test_real_fixture_projections_match_explicit_request_surfaces(self) -> None:
        bazi = completeness._fixture_case_bindings(
            completeness._load_yaml(completeness.audit_bazi_provider.FIXTURE),
            system="bazi",
        )
        self.assertEqual(
            bazi["luck-male-cycle-1-at"]["calculation_projection"][
                "reference_datetime"
            ],
            "2007-07-09T18:28:52.600800+08:00",
        )
        self.assertNotEqual(
            bazi["luck-male-cycle-1-before"]["identity_digest"],
            bazi["luck-male-cycle-1-at"]["identity_digest"],
        )
        for case_id in (
            "horizon-ten-years",
            "horizon-sixty-one-years",
            "horizon-upper-year-boundary",
        ):
            with self.subTest(case_id=case_id):
                self.assertEqual(bazi[case_id]["unconsumed_semantic_leaves"], ())
                self.assertIsInstance(
                    bazi[case_id]["input_projection"]["start"], str
                )
                self.assertIsInstance(
                    bazi[case_id]["input_projection"]["end"], str
                )
                self.assertEqual(
                    bazi[case_id]["input_projection"],
                    bazi[case_id]["extension_projection"],
                )

        fortune = completeness._fixture_case_bindings(
            completeness._load_yaml(completeness.audit_fortune_provider.FIXTURE),
            system="fortune",
        )["fortune-hko-2024-01-01"]
        self.assertEqual(
            fortune["calculation_projection"]["birth_data"]["birth_datetime"],
            "2000-10-18T06:45:00",
        )
        self.assertEqual(
            fortune["extension_projection"],
            {"kind": "day", "start": "2024-01-01", "end": "2024-01-01"},
        )

        liuyao = completeness._fixture_case_bindings(
            completeness._load_yaml(completeness.audit_liuyao_provider.FIXTURE),
            system="liuyao",
        )["stable-all-yang"]
        self.assertEqual(
            liuyao["calculation_projection"]["chart_data"]["tosses"],
            [7, 7, 7, 7, 7, 7],
        )

        selection = completeness._fixture_case_bindings(
            completeness._load_yaml(completeness.audit_selection_provider.FIXTURE),
            system="selection",
        )["lunar-python-01"]
        self.assertEqual(
            selection["calculation_projection"]["chart_data"][
                "selection_spec"
            ]["date_range"],
            {"start": "2024-01-01", "end": "2024-01-01"},
        )
        selection_spec = selection["calculation_projection"]["chart_data"][
            "selection_spec"
        ]
        self.assertEqual(selection_spec["event_profile"], "construction_renovation")
        self.assertEqual(selection_spec["requested_actions"], ["立向"])
        self.assertEqual(selection_spec["requested_scopes"], ["directional_judgment"])
        self.assertEqual(selection_spec["directional_context"], {"site_mountain": "乙"})
        self.assertEqual(selection["unconsumed_semantic_leaves"], ())

    def test_horizon_validation_is_typed_bounded_and_calendar_valid(self) -> None:
        target_horizon = {
            "kind": "month",
            "start": "2025-01",
            "end": "2025-02",
            "target_date": "2025-02-01",
        }
        self.assertTrue(
            completeness._horizon_is_valid(target_horizon, system="ziwei")
        )
        self.assertFalse(
            completeness._horizon_is_valid(target_horizon, system="selection")
        )
        self.assertFalse(
            completeness._horizon_is_valid(
                {
                    "kind": "year",
                    "start": "2025",
                    "end": "2025",
                    "target_date": "2025-02-01",
                },
                system="ziwei",
            )
        )
        for horizon in (
            {"kind": "day", "start": "zzz", "end": "zzz"},
            {"kind": "month", "start": "2025-13", "end": "2025-13"},
            {"kind": "year", "start": 2025, "end": 2026},
            {"kind": "life", "target_date": "2025-01-01"},
            {
                "kind": "month",
                "start": "2025-02",
                "end": "2025-02",
                "target_date": "2025-03-01",
            },
        ):
            self.assertFalse(completeness._horizon_is_valid(horizon), horizon)

    def test_provider_request_semantics_excludes_unconsumed_envelope_fields(
        self,
    ) -> None:
        request = ReadingRequest(
            query="label only",
            action="new",
            system="selection",
            system_hint="legacy-only",
            timezone="Asia/Shanghai",
            location="上海",
            chart_data={"selection_spec": {"date_range": {}}},
            metadata={
                "longitude": 121.47,
                "unused_nonce": "must-not-bind",
            },
        )

        payload = reading_providers._bind_request_semantics(
            {"stable": True}, request
        )

        self.assertNotIn("query", payload["request_semantics"])
        self.assertNotIn("action", payload["request_semantics"])
        self.assertNotIn("system_hint", payload["request_semantics"])
        self.assertEqual(
            payload["request_semantics"]["metadata"],
            {"longitude": 121.47},
        )

    def test_partial_extension_cannot_claim_unrequested_unsupported_dimensions(
        self,
    ) -> None:
        extension = FactExtensionResult.create(
            system="fengshui",
            base_calculation_digest="base",
            requested_dimensions=("state",),
            horizon={"kind": "instant"},
            status="partial",
            facts={"observed": True},
            unsupported_dimensions=("direction",),
        )

        self.assertFalse(
            completeness._extension_status_is_ready(
                extension,
                capability=completeness.PROVIDER_CAPABILITIES["fengshui"],
                requested_dimensions=("state",),
            )
        )

    def test_case_replay_rejects_unconsumed_metadata_nonces(self) -> None:
        class MetadataNonceProvider:
            provider_id = "mingli-master.metadata-nonce.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                del request
                return CalculationResult.create(
                    system="metadata-nonce",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"provider_consumed_input": "same"},
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_metadata_nonce",
            MetadataNonceProvider=MetadataNonceProvider,
        )

        def audit_metadata_nonce(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = MetadataNonceProvider()
            for case_id in ("case-a", "case-b"):
                for _ in range(2):
                    provider.calculate(
                        ReadingRequest(
                            query=f"fixture {case_id}",
                            system="metadata-nonce",
                            metadata={"audit_nonce": case_id},
                        )
                    )
            return {
                "schema_version": "metadata-nonce-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        module.audit_metadata_nonce = audit_metadata_nonce
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=MetadataNonceProvider,
            fixture_path=Path("unused"),
            expected_system="metadata-nonce",
            expected_identity=(
                f"{MetadataNonceProvider.__module__}."
                f"{MetadataNonceProvider.__qualname__}",
                MetadataNonceProvider.provider_id,
                MetadataNonceProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
        )

        self.assertEqual(telemetry["distinct_route_request_digests"], 2)
        self.assertEqual(telemetry["distinct_calculation_request_digests"], 1)
        self.assertEqual(telemetry["distinct_effective_case_digests"], 1)
        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertFalse(telemetry["provider_boundary_replay_ready"], telemetry)

    def test_audit_labels_are_removed_recursively_from_semantic_payloads(self) -> None:
        self.assertEqual(
            completeness._semantic_audit_payload(
                {
                    "kind": "life",
                    "nested": {"audit_nonce": "case-a", "years": 10},
                    "case_id": "case-a",
                }
            ),
            {"kind": "life", "nested": {"years": 10}},
        )

    def test_provider_input_observer_rejects_reused_object_identity(self) -> None:
        class ReusedIdentityProvider:
            provider_id = "mingli-master.reused-identity.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                captured = CalculationResult.create(
                    system="reused-identity-child",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={
                        "audit_nonce": request.metadata["audit_nonce"],
                    },
                    facts={"temporary": True},
                )
                return CalculationResult(
                    system="reused-identity",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_hash=captured.input_hash,
                    result_hash="b" * 64,
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_reused_identity",
            ReusedIdentityProvider=ReusedIdentityProvider,
        )

        def audit_reused_identity(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = ReusedIdentityProvider()
            for case_id in ("case-a", "case-b"):
                for _ in range(2):
                    provider.calculate(
                        ReadingRequest(
                            query=f"fixture {case_id}",
                            system="reused-identity",
                            metadata={"audit_nonce": case_id},
                        )
                    )
            return {
                "schema_version": "reused-identity-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        module.audit_reused_identity = audit_reused_identity
        with mock.patch.object(completeness, "id", return_value=1, create=True):
            _, telemetry = completeness._run_dedicated_provider_audit(
                module=module,
                provider_class=ReusedIdentityProvider,
                fixture_path=Path("unused"),
                expected_system="reused-identity",
                expected_identity=(
                    f"{ReusedIdentityProvider.__module__}."
                    f"{ReusedIdentityProvider.__qualname__}",
                    ReusedIdentityProvider.provider_id,
                    ReusedIdentityProvider.provider_version,
                ),
                known_case_ids={"case-a", "case-b"},
                case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
            )

        self.assertIn(
            "provider returned a different result than its captured input result",
            telemetry["findings"],
        )
        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertFalse(telemetry["provider_boundary_replay_ready"], telemetry)

    def test_provider_input_observer_rejects_opaque_self_reported_digest(self) -> None:
        class OpaqueDigestProvider:
            provider_id = "mingli-master.opaque-digest.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={
                        "input_digest": completeness.canonical_digest(request.query)
                    },
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_opaque_digest",
            OpaqueDigestProvider=OpaqueDigestProvider,
        )

        def audit_opaque_digest(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = OpaqueDigestProvider()
            for case_id in ("case-a", "case-b"):
                for _ in range(2):
                    provider.calculate(
                        ReadingRequest(query=case_id, system="bazi")
                    )
            return {
                "schema_version": "opaque-digest-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        module.audit_opaque_digest = audit_opaque_digest
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=OpaqueDigestProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{OpaqueDigestProvider.__module__}.{OpaqueDigestProvider.__qualname__}",
                OpaqueDigestProvider.provider_id,
                OpaqueDigestProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertTrue(
            any("preimage" in item for item in telemetry["findings"]),
            telemetry,
        )

    def test_fixture_binding_rejects_renamed_digest_wrapped_nonce(self) -> None:
        class RenamedNonceProvider:
            provider_id = "mingli-master.renamed-nonce.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                proof = {"marker": request.chart_data["scenario_token"]}
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={
                        "semantic": "same",
                        "proof": proof,
                        "input_digest": completeness.canonical_digest(proof),
                    },
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_renamed_nonce",
            RenamedNonceProvider=RenamedNonceProvider,
        )

        def audit_renamed_nonce(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = RenamedNonceProvider()
            for case_id in ("case-a", "case-b"):
                for _ in range(2):
                    provider.calculate(
                        ReadingRequest(
                            query=case_id,
                            system="bazi",
                            timezone="Asia/Shanghai",
                            chart_data={"scenario_token": case_id},
                        )
                    )
            return {
                "schema_version": "renamed-nonce-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        fixture = {
            "cases": [
                {
                    "id": "case-a",
                    "input": {
                        "timezone": "Asia/Shanghai",
                        "real_input": "alpha",
                    },
                },
                {
                    "id": "case-b",
                    "input": {
                        "timezone": "Asia/Shanghai",
                        "real_input": "beta",
                    },
                },
            ]
        }
        module.audit_renamed_nonce = audit_renamed_nonce
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=RenamedNonceProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{RenamedNonceProvider.__module__}.{RenamedNonceProvider.__qualname__}",
                RenamedNonceProvider.provider_id,
                RenamedNonceProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
            fixture_case_bindings=completeness._fixture_case_bindings(fixture),
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertTrue(
            any("fixture semantic input" in item for item in telemetry["findings"]),
            telemetry,
        )

    def test_fixture_binding_rejects_provider_input_that_ignores_semantics(self) -> None:
        class IgnoredSemanticProvider:
            provider_id = "mingli-master.ignored-semantic.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={
                        "request_semantics": {
                            "chart_data": {
                                "wrong_input": request.chart_data["real_input"]
                            }
                        },
                        "scenario_token": request.chart_data["scenario_token"],
                    },
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_ignored_semantic",
            IgnoredSemanticProvider=IgnoredSemanticProvider,
        )

        def audit_ignored_semantic(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = IgnoredSemanticProvider()
            for case_id, real_input in (("case-a", "alpha"), ("case-b", "beta")):
                for _ in range(2):
                    provider.calculate(
                        ReadingRequest(
                            query=case_id,
                            system="bazi",
                            chart_data={
                                "real_input": real_input,
                                "scenario_token": case_id,
                            },
                        )
                    )
            return {
                "schema_version": "ignored-semantic-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        fixture = {
            "cases": [
                {
                    "id": "case-a",
                    "input": {"chart_data": {"real_input": "alpha"}},
                },
                {
                    "id": "case-b",
                    "input": {"chart_data": {"real_input": "beta"}},
                },
            ]
        }
        module.audit_ignored_semantic = audit_ignored_semantic
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=IgnoredSemanticProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{IgnoredSemanticProvider.__module__}."
                f"{IgnoredSemanticProvider.__qualname__}",
                IgnoredSemanticProvider.provider_id,
                IgnoredSemanticProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
            fixture_case_bindings=completeness._fixture_case_bindings(fixture),
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertTrue(
            any("provider input" in item for item in telemetry["findings"]),
            telemetry,
        )

    def test_fixture_binding_rejects_swapped_inputs_with_unchanged_case_ids(self) -> None:
        class SwappedInputProvider:
            provider_id = "mingli-master.swapped-input.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={
                        "request_semantics": {
                            "chart_data": {
                                "real_input": request.chart_data["real_input"]
                            }
                        }
                    },
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_swapped_input",
            SwappedInputProvider=SwappedInputProvider,
        )

        def audit_swapped_input(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = SwappedInputProvider()
            for case_id, wrong_input in (("case-a", "beta"), ("case-b", "alpha")):
                for _ in range(2):
                    provider.calculate(
                        ReadingRequest(
                            query=case_id,
                            system="bazi",
                            chart_data={"real_input": wrong_input},
                        )
                    )
            return {
                "schema_version": "swapped-input-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        fixture = {
            "cases": [
                {"id": "case-a", "input": {"chart_data": {"real_input": "alpha"}}},
                {"id": "case-b", "input": {"chart_data": {"real_input": "beta"}}},
            ]
        }
        module.audit_swapped_input = audit_swapped_input
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=SwappedInputProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{SwappedInputProvider.__module__}.{SwappedInputProvider.__qualname__}",
                SwappedInputProvider.provider_id,
                SwappedInputProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
            fixture_case_bindings=completeness._fixture_case_bindings(fixture),
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertTrue(
            all(not row["fixture_input_bound"] for row in telemetry["case_replays"]),
            telemetry,
        )

    def test_fixture_binding_rejects_semantic_field_drift(self) -> None:
        original_fixture = {
            "cases": [
                {"id": "case-a", "input": {"chart_data": {"real_input": "alpha"}}}
            ]
        }
        drifted_fixture = copy.deepcopy(original_fixture)
        drifted_fixture["cases"][0]["input"]["chart_data"]["real_input"] = "beta"
        self.assertNotEqual(
            completeness._fixture_case_bindings(original_fixture)["case-a"][
                "identity_digest"
            ],
            completeness._fixture_case_bindings(drifted_fixture)["case-a"][
                "identity_digest"
            ],
        )

        class FixtureDriftProvider:
            provider_id = "mingli-master.fixture-drift.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={
                        "request_semantics": {
                            "chart_data": copy.deepcopy(request.chart_data)
                        }
                    },
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_fixture_drift",
            FixtureDriftProvider=FixtureDriftProvider,
        )

        def audit_fixture_drift(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = FixtureDriftProvider()
            for _ in range(2):
                provider.calculate(
                    ReadingRequest(
                        query="case-a",
                        system="bazi",
                        chart_data={"real_input": "alpha"},
                    )
                )
            return {
                "schema_version": "fixture-drift-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a"],
                "counts": {},
                "findings": [],
            }

        module.audit_fixture_drift = audit_fixture_drift
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=FixtureDriftProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{FixtureDriftProvider.__module__}.{FixtureDriftProvider.__qualname__}",
                FixtureDriftProvider.provider_id,
                FixtureDriftProvider.provider_version,
            ),
            known_case_ids={"case-a"},
            case_categories={"case-a": {"edge"}},
            fixture_case_bindings=completeness._fixture_case_bindings(
                drifted_fixture
            ),
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertFalse(telemetry["case_replays"][0]["fixture_input_bound"])

    def test_effective_case_identity_ignores_extra_request_nonces(self) -> None:
        class ExtraNonceProvider:
            provider_id = "mingli-master.extra-nonce.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="extra-nonce",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={
                        "request_semantics": {
                            "chart_data": request.chart_data,
                        }
                    },
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_extra_nonce",
            ExtraNonceProvider=ExtraNonceProvider,
        )

        def audit_extra_nonce(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = ExtraNonceProvider()
            for case_id in ("case-a", "case-b"):
                for _ in range(2):
                    provider.calculate(
                        ReadingRequest(
                            query=case_id,
                            system="extra-nonce",
                            chart_data={
                                "real_input": "same",
                                "scenario_token": case_id,
                            },
                        )
                    )
            return {
                "schema_version": "extra-nonce-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        fixture = {
            "cases": [
                {
                    "id": "case-a",
                    "input": {"chart_data": {"real_input": "same"}},
                },
                {
                    "id": "case-b",
                    "input": {"chart_data": {"real_input": "same"}},
                },
            ]
        }
        module.audit_extra_nonce = audit_extra_nonce
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=ExtraNonceProvider,
            fixture_path=Path("unused"),
            expected_system="extra-nonce",
            expected_identity=(
                f"{ExtraNonceProvider.__module__}.{ExtraNonceProvider.__qualname__}",
                ExtraNonceProvider.provider_id,
                ExtraNonceProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
            fixture_case_bindings=completeness._fixture_case_bindings(fixture),
        )

        self.assertEqual(telemetry["distinct_effective_case_digests"], 1)
        self.assertFalse(telemetry["case_replay_ready"], telemetry)

    def test_case_replay_rejects_copied_request_envelope_nonces(self) -> None:
        class CopiedEnvelopeProvider:
            provider_id = "mingli-master.copied-envelope.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="copied-envelope",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload=request.to_dict(),
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_copied_envelope",
            CopiedEnvelopeProvider=CopiedEnvelopeProvider,
        )

        def audit_copied_envelope(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = CopiedEnvelopeProvider()
            for case_id in ("case-a", "case-b"):
                for _ in range(2):
                    provider.calculate(
                        ReadingRequest(
                            query=f"fixture {case_id}",
                            system="copied-envelope",
                            intent={"audit_nonce": case_id},
                            goal={"audit_nonce": case_id},
                            metadata={"audit_nonce": case_id},
                        )
                    )
            return {
                "schema_version": "copied-envelope-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        module.audit_copied_envelope = audit_copied_envelope
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=CopiedEnvelopeProvider,
            fixture_path=Path("unused"),
            expected_system="copied-envelope",
            expected_identity=(
                f"{CopiedEnvelopeProvider.__module__}."
                f"{CopiedEnvelopeProvider.__qualname__}",
                CopiedEnvelopeProvider.provider_id,
                CopiedEnvelopeProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
        )

        self.assertEqual(telemetry["distinct_route_request_digests"], 2)
        self.assertEqual(telemetry["distinct_effective_case_digests"], 1)
        self.assertFalse(telemetry["case_replay_ready"], telemetry)

    def test_boundary_categories_cannot_merge_duplicate_effective_cases(self) -> None:
        class DuplicateBoundaryProvider:
            provider_id = "mingli-master.duplicate-boundary.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                del request
                return CalculationResult.create(
                    system="duplicate-boundary",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"semantic": "same"},
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_duplicate_boundary",
            DuplicateBoundaryProvider=DuplicateBoundaryProvider,
        )

        def audit_duplicate_boundary(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = DuplicateBoundaryProvider()
            for case_id in ("route-case", "extra-a", "extra-b"):
                for _ in range(2):
                    provider.calculate(
                        ReadingRequest(
                            query=case_id,
                            system="duplicate-boundary",
                        )
                    )
            return {
                "schema_version": "duplicate-boundary-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["route-case"],
                "counts": {},
                "findings": [],
            }

        module.audit_duplicate_boundary = audit_duplicate_boundary
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=DuplicateBoundaryProvider,
            fixture_path=Path("unused"),
            expected_system="duplicate-boundary",
            expected_identity=(
                f"{DuplicateBoundaryProvider.__module__}."
                f"{DuplicateBoundaryProvider.__qualname__}",
                DuplicateBoundaryProvider.provider_id,
                DuplicateBoundaryProvider.provider_version,
            ),
            known_case_ids={"route-case", "extra-a", "extra-b"},
            case_categories={
                "route-case": {"ordinary"},
                "extra-a": {"edge-a"},
                "extra-b": {"edge-b"},
            },
        )

        self.assertFalse(telemetry["provider_boundary_replay_ready"], telemetry)
        self.assertEqual(telemetry["provider_boundary_case_count"], 3)
        self.assertEqual(telemetry["distinct_boundary_effective_case_digests"], 1)

    def test_nondeterministic_rejection_replay_blocks_boundary_readiness(self) -> None:
        class RejectionProvider:
            provider_id = "mingli-master.rejection-replay.v1"
            provider_version = "1.0.0"

            def __init__(self) -> None:
                self.rejections = 0

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                if request.query == "fixture-reject":
                    self.rejections += 1
                    raise ValueError(f"rejection-{self.rejections}")
                return CalculationResult.create(
                    system="rejection-replay",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"semantic": request.chart_data["case"]},
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_rejection_replay",
            RejectionProvider=RejectionProvider,
        )

        def audit_rejection_replay(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = RejectionProvider()
            for _ in range(2):
                provider.calculate(
                    ReadingRequest(
                        query="fixture-case",
                        system="rejection-replay",
                        chart_data={"case": "stable"},
                    )
                )
            for _ in range(2):
                try:
                    provider.calculate(
                        ReadingRequest(
                            query="fixture-reject",
                            system="rejection-replay",
                            chart_data={"case": "invalid"},
                        )
                    )
                except ValueError:
                    pass
            return {
                "schema_version": "rejection-replay-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["fixture-case"],
                "counts": {},
                "findings": [],
            }

        module.audit_rejection_replay = audit_rejection_replay
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=RejectionProvider,
            fixture_path=Path("unused"),
            expected_system="rejection-replay",
            expected_identity=(
                f"{RejectionProvider.__module__}.{RejectionProvider.__qualname__}",
                RejectionProvider.provider_id,
                RejectionProvider.provider_version,
            ),
            known_case_ids={"fixture-case", "fixture-reject"},
            case_categories={
                "fixture-case": {"edge"},
                "fixture-reject": {"invalid_edge"},
            },
        )

        self.assertFalse(telemetry["provider_boundary_replay_ready"], telemetry)
        self.assertTrue(
            any("boundary replay" in item for item in telemetry["findings"]),
            telemetry,
        )

    def test_duplicate_rejection_semantics_block_boundary_readiness(self) -> None:
        class DuplicateRejectionProvider:
            provider_id = "mingli-master.duplicate-rejection.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                if request.query.startswith("reject-"):
                    raise ValueError("same rejection")
                return CalculationResult.create(
                    system="duplicate-rejection",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"semantic": request.chart_data["case"]},
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_duplicate_rejection",
            DuplicateRejectionProvider=DuplicateRejectionProvider,
        )

        def audit_duplicate_rejection(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = DuplicateRejectionProvider()
            for _ in range(2):
                provider.calculate(
                    ReadingRequest(
                        query="route-case",
                        system="duplicate-rejection",
                        chart_data={"case": "valid"},
                    )
                )
            for case_id in ("reject-a", "reject-b"):
                for _ in range(2):
                    try:
                        provider.calculate(
                            ReadingRequest(
                                query=case_id,
                                system="duplicate-rejection",
                                chart_data={"case": "same-invalid"},
                                metadata={"audit_nonce": case_id},
                            )
                        )
                    except ValueError:
                        pass
            return {
                "schema_version": "duplicate-rejection-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["route-case"],
                "counts": {},
                "findings": [],
            }

        module.audit_duplicate_rejection = audit_duplicate_rejection
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=DuplicateRejectionProvider,
            fixture_path=Path("unused"),
            expected_system="duplicate-rejection",
            expected_identity=(
                f"{DuplicateRejectionProvider.__module__}."
                f"{DuplicateRejectionProvider.__qualname__}",
                DuplicateRejectionProvider.provider_id,
                DuplicateRejectionProvider.provider_version,
            ),
            known_case_ids={"route-case", "reject-a", "reject-b"},
            case_categories={
                "route-case": {"edge"},
                "reject-a": {"invalid-a"},
                "reject-b": {"invalid-b"},
            },
        )

        self.assertFalse(telemetry["provider_boundary_replay_ready"], telemetry)
        self.assertEqual(telemetry["provider_boundary_rejection_case_count"], 0)

    def test_case_replay_fails_closed_on_multiple_result_creations(self) -> None:
        class MultipleCreateProvider:
            provider_id = "mingli-master.multiple-create.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                CalculationResult.create(
                    system="multiple-create",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"decoy": request.query},
                    facts={"decoy": True},
                )
                return CalculationResult.create(
                    system="multiple-create",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"semantic": request.query},
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_multiple_create",
            MultipleCreateProvider=MultipleCreateProvider,
        )

        def audit_multiple_create(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = MultipleCreateProvider()
            for _ in range(2):
                provider.calculate(
                    ReadingRequest(query="case-a", system="multiple-create")
                )
            return {
                "schema_version": "multiple-create-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a"],
                "counts": {},
                "findings": [],
            }

        module.audit_multiple_create = audit_multiple_create
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=MultipleCreateProvider,
            fixture_path=Path("unused"),
            expected_system="multiple-create",
            expected_identity=(
                f"{MultipleCreateProvider.__module__}."
                f"{MultipleCreateProvider.__qualname__}",
                MultipleCreateProvider.provider_id,
                MultipleCreateProvider.provider_version,
            ),
            known_case_ids={"case-a"},
            case_categories={"case-a": {"edge"}},
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertTrue(
            any("exactly one" in item for item in telemetry["findings"]),
            telemetry,
        )

    def test_case_replay_fails_closed_on_returned_input_hash_drift(self) -> None:
        class DriftedInputHashProvider:
            provider_id = "mingli-master.drifted-input-hash.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                result = CalculationResult.create(
                    system="drifted-input-hash",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"semantic": request.query},
                    facts={"stable": True},
                )
                return replace(result, input_hash="0" * 64)

        module = SimpleNamespace(
            __name__="audit_drifted_input_hash",
            DriftedInputHashProvider=DriftedInputHashProvider,
        )

        def audit_drifted_input_hash(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = DriftedInputHashProvider()
            for _ in range(2):
                provider.calculate(
                    ReadingRequest(query="case-a", system="drifted-input-hash")
                )
            return {
                "schema_version": "drifted-input-hash-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a"],
                "counts": {},
                "findings": [],
            }

        module.audit_drifted_input_hash = audit_drifted_input_hash
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=DriftedInputHashProvider,
            fixture_path=Path("unused"),
            expected_system="drifted-input-hash",
            expected_identity=(
                f"{DriftedInputHashProvider.__module__}."
                f"{DriftedInputHashProvider.__qualname__}",
                DriftedInputHashProvider.provider_id,
                DriftedInputHashProvider.provider_version,
            ),
            known_case_ids={"case-a"},
            case_categories={"case-a": {"edge"}},
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertTrue(
            any("input hash" in item for item in telemetry["findings"]),
            telemetry,
        )

    def test_extension_replay_rejects_query_only_nonces(self) -> None:
        class ExtensionQueryNonceProvider:
            provider_id = "mingli-master.extension-query-nonce.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="extension-query-nonce",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload=request.to_dict(),
                    facts={"stable": True},
                )

            def extend(
                self,
                calculation: CalculationResult,
                requested_dimensions: tuple[str, ...],
                horizon: dict[str, object],
            ) -> dict[str, object]:
                del calculation, requested_dimensions, horizon
                return {"stable": True}

        module = SimpleNamespace(
            __name__="audit_extension_query_nonce",
            ExtensionQueryNonceProvider=ExtensionQueryNonceProvider,
        )

        def audit_extension_query_nonce(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = ExtensionQueryNonceProvider()
            for case_id in ("case-a", "case-b"):
                for _ in range(2):
                    calculation = provider.calculate(
                        ReadingRequest(
                            query=f"nonce {case_id}",
                            system="extension-query-nonce",
                        )
                    )
                    provider.extend(
                        calculation,
                        ("timing",),
                        {"kind": "bounded", "days": 7},
                    )
            return {
                "schema_version": "extension-query-nonce-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        module.audit_extension_query_nonce = audit_extension_query_nonce
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=ExtensionQueryNonceProvider,
            fixture_path=Path("unused"),
            expected_system="extension-query-nonce",
            expected_identity=(
                f"{ExtensionQueryNonceProvider.__module__}."
                f"{ExtensionQueryNonceProvider.__qualname__}",
                ExtensionQueryNonceProvider.provider_id,
                ExtensionQueryNonceProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
        )

        self.assertEqual(telemetry["distinct_route_request_digests"], 2)
        self.assertEqual(telemetry["distinct_calculation_request_digests"], 1)
        self.assertEqual(telemetry["distinct_effective_case_digests"], 0)
        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertFalse(telemetry["provider_boundary_replay_ready"], telemetry)

    def test_extension_replay_cannot_use_failed_nonce_requests(self) -> None:
        class FailedExtensionProvider:
            provider_id = "mingli-master.failed-extension.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="failed-extension",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={
                        "semantic": request.chart_data["semantic_case"],
                    },
                    facts={"stable": True},
                )

            def extend(
                self,
                calculation: CalculationResult,
                requested_dimensions: tuple[str, ...],
                horizon: dict[str, object],
            ) -> CalculationResult:
                del calculation, requested_dimensions, horizon
                raise ValueError("deterministic failed extension")

        module = SimpleNamespace(
            __name__="audit_failed_extension",
            FailedExtensionProvider=FailedExtensionProvider,
        )

        def audit_failed_extension(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = FailedExtensionProvider()
            for case_id in ("case-a", "case-b"):
                for _ in range(2):
                    calculation = provider.calculate(
                        ReadingRequest(
                            query=f"fixture {case_id}",
                            system="failed-extension",
                            chart_data={"semantic_case": case_id},
                        )
                    )
                    try:
                        provider.extend(
                            calculation,
                            ("timing",),
                            {"kind": "instant", "audit_nonce": case_id},
                        )
                    except ValueError:
                        pass
            return {
                "schema_version": "failed-extension-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a", "case-b"],
                "counts": {},
                "findings": [],
            }

        module.audit_failed_extension = audit_failed_extension
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=FailedExtensionProvider,
            fixture_path=Path("unused"),
            expected_system="failed-extension",
            expected_identity=(
                f"{FailedExtensionProvider.__module__}."
                f"{FailedExtensionProvider.__qualname__}",
                FailedExtensionProvider.provider_id,
                FailedExtensionProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
        )

        self.assertEqual(telemetry["distinct_effective_case_digests"], 0)
        self.assertFalse(telemetry["case_replay_ready"], telemetry)

    def test_extension_replay_requires_two_matching_executions(self) -> None:
        class SingleExtensionProvider:
            provider_id = "mingli-master.single-extension.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"semantic": request.chart_data["semantic_case"]},
                    facts={"stable": True},
                )

            def extend(
                self,
                calculation: CalculationResult,
                requested_dimensions: tuple[str, ...],
                horizon: dict[str, object],
            ) -> CalculationResult:
                return _attach_extension(
                    calculation,
                    requested_dimensions,
                    horizon,
                    status="complete",
                    facts={"stable_extension": True},
                )

        module = SimpleNamespace(
            __name__="audit_single_extension",
            SingleExtensionProvider=SingleExtensionProvider,
        )

        def audit_single_extension(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = SingleExtensionProvider()
            for replay in range(2):
                calculation = provider.calculate(
                    ReadingRequest(
                        query="case-a",
                        system="bazi",
                        chart_data={"semantic_case": "case-a"},
                    )
                )
                if replay == 0:
                    provider.extend(calculation, ("timing",), {"kind": "life"})
            return {
                "schema_version": "single-extension-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a"],
                "counts": {},
                "findings": [],
            }

        module.audit_single_extension = audit_single_extension
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=SingleExtensionProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{SingleExtensionProvider.__module__}.{SingleExtensionProvider.__qualname__}",
                SingleExtensionProvider.provider_id,
                SingleExtensionProvider.provider_version,
            ),
            known_case_ids={"case-a"},
            case_categories={"case-a": {"edge"}},
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertFalse(telemetry["case_replays"][0]["extension_replay_ready"])

    def test_extension_replay_rejects_non_calculation_results(self) -> None:
        class NonCalculationExtensionProvider:
            provider_id = "mingli-master.non-calculation-extension.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"semantic": request.chart_data["semantic_case"]},
                    facts={"stable": True},
                )

            def extend(
                self,
                calculation: CalculationResult,
                requested_dimensions: tuple[str, ...],
                horizon: dict[str, object],
            ) -> dict[str, object]:
                del calculation, requested_dimensions, horizon
                return {"fact_extension": "forged"}

        module = SimpleNamespace(
            __name__="audit_non_calculation_extension",
            NonCalculationExtensionProvider=NonCalculationExtensionProvider,
        )

        def audit_non_calculation_extension(
            *, fixture_path: Path
        ) -> dict[str, object]:
            del fixture_path
            provider = NonCalculationExtensionProvider()
            for _ in range(2):
                calculation = provider.calculate(
                    ReadingRequest(
                        query="case-a",
                        system="bazi",
                        chart_data={"semantic_case": "case-a"},
                    )
                )
                provider.extend(calculation, ("timing",), {"kind": "life"})
            return {
                "schema_version": "non-calculation-extension-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a"],
                "counts": {},
                "findings": [],
            }

        module.audit_non_calculation_extension = audit_non_calculation_extension
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=NonCalculationExtensionProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{NonCalculationExtensionProvider.__module__}."
                f"{NonCalculationExtensionProvider.__qualname__}",
                NonCalculationExtensionProvider.provider_id,
                NonCalculationExtensionProvider.provider_version,
            ),
            known_case_ids={"case-a"},
            case_categories={"case-a": {"edge"}},
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertFalse(telemetry["case_replays"][0]["extension_replay_ready"])

    def test_extension_replay_rejects_nondeterministic_results(self) -> None:
        class NondeterministicExtensionProvider:
            provider_id = "mingli-master.nondeterministic-extension.v1"
            provider_version = "1.0.0"

            def __init__(self) -> None:
                self.counter = 0

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={"semantic": request.chart_data["semantic_case"]},
                    facts={"stable": True},
                )

            def extend(
                self,
                calculation: CalculationResult,
                requested_dimensions: tuple[str, ...],
                horizon: dict[str, object],
            ) -> CalculationResult:
                self.counter += 1
                return _attach_extension(
                    calculation,
                    requested_dimensions,
                    horizon,
                    status="complete",
                    facts={"counter": self.counter},
                )

        module = SimpleNamespace(
            __name__="audit_nondeterministic_extension",
            NondeterministicExtensionProvider=NondeterministicExtensionProvider,
        )

        def audit_nondeterministic_extension(
            *, fixture_path: Path
        ) -> dict[str, object]:
            del fixture_path
            provider = NondeterministicExtensionProvider()
            for _ in range(2):
                calculation = provider.calculate(
                    ReadingRequest(
                        query="case-a",
                        system="bazi",
                        chart_data={"semantic_case": "case-a"},
                    )
                )
                provider.extend(
                    calculation,
                    ("timing",),
                    {"kind": "life"},
                )
            return {
                "schema_version": "nondeterministic-extension-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a"],
                "counts": {},
                "findings": [],
            }

        module.audit_nondeterministic_extension = audit_nondeterministic_extension
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=NondeterministicExtensionProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{NondeterministicExtensionProvider.__module__}."
                f"{NondeterministicExtensionProvider.__qualname__}",
                NondeterministicExtensionProvider.provider_id,
                NondeterministicExtensionProvider.provider_version,
            ),
            known_case_ids={"case-a"},
            case_categories={"case-a": {"edge"}},
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertFalse(telemetry["provider_boundary_replay_ready"], telemetry)

    def _scheduled_extension_telemetry(
        self,
        schedule: tuple[tuple[int, dict[str, object]], ...],
    ) -> dict[str, object]:
        class ScheduledExtensionProvider:
            provider_id = "mingli-master.scheduled-extension.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={
                        "request_semantics": {
                            "chart_data": copy.deepcopy(request.chart_data)
                        }
                    },
                    facts={"stable": True},
                )

            def extend(
                self,
                calculation: CalculationResult,
                requested_dimensions: tuple[str, ...],
                horizon: dict[str, object],
            ) -> CalculationResult:
                return _attach_extension(
                    calculation,
                    requested_dimensions,
                    horizon,
                    status="complete",
                    facts={"stable_extension": True},
                )

        module = SimpleNamespace(
            __name__="audit_scheduled_extension",
            ScheduledExtensionProvider=ScheduledExtensionProvider,
        )

        def audit_scheduled_extension(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = ScheduledExtensionProvider()
            calculations = [
                provider.calculate(
                    ReadingRequest(
                        query="case-a",
                        system="bazi",
                        chart_data={"semantic_case": "case-a"},
                    )
                )
                for _ in range(2)
            ]
            for calculation_index, horizon in schedule:
                provider.extend(
                    calculations[calculation_index],
                    ("timing",),
                    copy.deepcopy(horizon),
                )
            return {
                "schema_version": "scheduled-extension-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a"],
                "counts": {},
                "findings": [],
            }

        module.audit_scheduled_extension = audit_scheduled_extension
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=ScheduledExtensionProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{ScheduledExtensionProvider.__module__}."
                f"{ScheduledExtensionProvider.__qualname__}",
                ScheduledExtensionProvider.provider_id,
                ScheduledExtensionProvider.provider_version,
            ),
            known_case_ids={"case-a"},
            case_categories={"case-a": {"edge"}},
        )
        return telemetry

    def test_extension_replay_requires_each_base_calculation_to_be_extended(
        self,
    ) -> None:
        telemetry = self._scheduled_extension_telemetry(
            (
                (0, {"kind": "life"}),
                (0, {"kind": "life"}),
            )
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertFalse(telemetry["case_replays"][0]["extension_replay_ready"])

    def test_extension_replay_rejects_two_individually_repeated_requests(
        self,
    ) -> None:
        telemetry = self._scheduled_extension_telemetry(
            (
                (0, {"kind": "life"}),
                (0, {"kind": "life"}),
                (1, {"kind": "year", "start": "2025", "end": "2025"}),
                (1, {"kind": "year", "start": "2025", "end": "2025"}),
            )
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertFalse(telemetry["case_replays"][0]["extension_replay_ready"])

    def test_fixture_binding_rejects_unconsumed_semantic_leaf(self) -> None:
        class SemanticLeafProvider:
            provider_id = "mingli-master.semantic-leaf.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={
                        "request_semantics": {
                            "chart_data": {
                                "pillars": copy.deepcopy(
                                    request.chart_data["pillars"]
                                )
                            }
                        }
                    },
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_semantic_leaf",
            SemanticLeafProvider=SemanticLeafProvider,
        )

        def audit_semantic_leaf(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = SemanticLeafProvider()
            for _ in range(2):
                provider.calculate(
                    ReadingRequest(
                        query="case-a",
                        system="bazi",
                        chart_data={"pillars": ["甲子", "乙丑", "丙寅", "丁卯"]},
                    )
                )
            return {
                "schema_version": "semantic-leaf-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a"],
                "counts": {},
                "findings": [],
            }

        fixture = {
            "cases": [
                {
                    "id": "case-a",
                    "category": "strong_weak_dispute",
                    "input": {
                        "pillars": ["甲子", "乙丑", "丙寅", "丁卯"],
                        "school_variant": "explicit-school-a",
                    },
                }
            ]
        }
        module.audit_semantic_leaf = audit_semantic_leaf
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=SemanticLeafProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{SemanticLeafProvider.__module__}.{SemanticLeafProvider.__qualname__}",
                SemanticLeafProvider.provider_id,
                SemanticLeafProvider.provider_version,
            ),
            known_case_ids={"case-a"},
            case_categories={"case-a": {"edge"}},
            fixture_case_bindings=completeness._fixture_case_bindings(
                fixture,
                system="bazi",
            ),
        )

        self.assertFalse(telemetry["case_replay_ready"], telemetry)
        self.assertFalse(telemetry["case_replays"][0]["fixture_input_bound"])

    def test_input_digest_requires_canonical_request_semantics(self) -> None:
        request_semantics = {
            "chart_data": {"pillars": ["甲子", "乙丑", "丙寅", "丁卯"]}
        }
        unrelated_witness = {"marker": "not-the-request"}
        payload = {
            "request_semantics": request_semantics,
            "input_digest": completeness.canonical_digest(unrelated_witness),
            "witness": unrelated_witness,
        }

        self.assertFalse(
            completeness._declared_input_digests_have_preimages(payload)
        )

    def test_route_owned_case_ids_must_equal_explicit_qualifying_ids(self) -> None:
        parameters = inspect.signature(
            completeness._run_dedicated_provider_audit
        ).parameters
        self.assertIn("qualifying_case_ids", parameters)

        class QualifyingCoverageProvider:
            provider_id = "mingli-master.qualifying-coverage.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="bazi",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload={
                        "request_semantics": {
                            "chart_data": copy.deepcopy(request.chart_data)
                        }
                    },
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_qualifying_coverage",
            QualifyingCoverageProvider=QualifyingCoverageProvider,
        )

        def audit_qualifying_coverage(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = QualifyingCoverageProvider()
            for _ in range(2):
                provider.calculate(
                    ReadingRequest(
                        query="case-a",
                        system="bazi",
                        chart_data={"semantic_case": "case-a"},
                    )
                )
            return {
                "schema_version": "qualifying-coverage-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a"],
                "counts": {},
                "findings": [],
            }

        module.audit_qualifying_coverage = audit_qualifying_coverage
        _, telemetry = completeness._run_dedicated_provider_audit(
            module=module,
            provider_class=QualifyingCoverageProvider,
            fixture_path=Path("unused"),
            expected_system="bazi",
            expected_identity=(
                f"{QualifyingCoverageProvider.__module__}."
                f"{QualifyingCoverageProvider.__qualname__}",
                QualifyingCoverageProvider.provider_id,
                QualifyingCoverageProvider.provider_version,
            ),
            known_case_ids={"case-a", "case-b"},
            qualifying_case_ids={"case-a", "case-b"},
            case_categories={"case-a": {"edge"}, "case-b": {"edge"}},
        )

        self.assertFalse(telemetry["case_ids_fixture_bound"], telemetry)
        self.assertFalse(telemetry["case_replay_ready"], telemetry)

    def test_direct_audit_observation_does_not_publish_to_the_session(self) -> None:
        class QuietProvider:
            provider_id = "mingli-master.quiet.v1"
            provider_version = "1.0.0"

            def calculate(self, request: ReadingRequest) -> CalculationResult:
                return CalculationResult.create(
                    system="quiet",
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    input_payload=request.to_dict(),
                    facts={"stable": True},
                )

        module = SimpleNamespace(
            __name__="audit_quiet",
            QuietProvider=QuietProvider,
        )

        def audit_quiet(*, fixture_path: Path) -> dict[str, object]:
            del fixture_path
            provider = QuietProvider()
            for _ in range(2):
                provider.calculate(
                    ReadingRequest(query="case-a", system="quiet")
                )
            return {
                "schema_version": "quiet-audit-v1",
                "provider_ready": True,
                "status": "pass",
                "route_owned_case_ids": ["case-a"],
                "counts": {},
                "findings": [],
            }

        module.audit_quiet = audit_quiet
        with tempfile.TemporaryDirectory() as session:
            with mock.patch.dict(
                os.environ,
                {"MINGLI_TEST_SESSION_DIR": session},
            ):
                completeness._run_dedicated_provider_audit(
                    module=module,
                    provider_class=QuietProvider,
                    fixture_path=Path("unused"),
                    expected_system="quiet",
                    expected_identity=(
                        f"{QuietProvider.__module__}."
                        f"{QuietProvider.__qualname__}",
                        QuietProvider.provider_id,
                        QuietProvider.provider_version,
                    ),
                    known_case_ids={"case-a"},
                    case_categories={"case-a": {"edge"}},
                )
            self.assertEqual(os.listdir(session), [])

    def test_same_process_matrix_build_rejects_a_detached_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            detached = Path(temporary) / "skill"
            detached.mkdir()
            with self.assertRaisesRegex(ValueError, "isolated subprocess"):
                completeness.build_matrix(root=detached)

        with self.assertRaisesRegex(ValueError, "fingerprint is stale"):
            completeness._build_matrix_uncached(str(ROOT), "0" * 64)


class LiveProviderDeclarationTests(unittest.TestCase):
    def test_selection_probe_horizons_use_declared_granularity(self) -> None:
        expected = {
            "day": {
                "kind": "day",
                "start": "2026-07-24",
                "end": "2026-07-28",
            },
            "month": {"kind": "month", "start": "2026-07", "end": "2026-07"},
            "year": {"kind": "year", "start": "2026", "end": "2026"},
        }
        for kind, horizon in expected.items():
            with self.subTest(kind=kind):
                self.assertEqual(
                    completeness._probe_horizon("selection", kind),
                    horizon,
                )
                self.assertTrue(
                    completeness._horizon_is_valid(horizon, system="selection")
                )

    def test_rfc6901_binding_resolver_is_strict_and_supports_escaped_tokens(self) -> None:
        payload = {"a/b": {"~key": ["value"]}}

        self.assertEqual(
            completeness.resolve_json_pointer(payload, "/a~1b/~0key/0"),
            "value",
        )
        with self.assertRaises((KeyError, IndexError, TypeError, ValueError)):
            completeness.resolve_json_pointer(payload, "/a~1b/missing")

    def test_every_live_provider_runs_twice_and_resolves_all_declared_outputs(self) -> None:
        for system in sorted(EXPECTED_SYSTEMS):
            with self.subTest(system=system):
                report = completeness.audit_live_provider_contract(
                    system,
                    root=ROOT,
                )
                capability = PROVIDER_CAPABILITIES[system]
                self.assertTrue(report["deterministic"], report)
                self.assertEqual(report["findings"], [], report)
                self.assertEqual(
                    set(report["resolved_output_bindings"]),
                    set(capability.outputs),
                )
                self.assertEqual(
                    set(report["resolved_extension_bindings"]),
                    set(capability.extension_outputs),
                )
                self.assertEqual(report["runs"], 2)

    def test_source_applicability_requires_captured_fixture_provider_replays(self) -> None:
        report = completeness.audit_source_applicability("bazi", root=ROOT)

        self.assertFalse(report["ready"], report)
        self.assertEqual(report["accepted_fixture_replay_count"], 0)
        self.assertTrue(
            any("captured fixture" in item for item in report["findings"]),
            report,
        )

    def test_runtime_registry_separates_required_and_comparison_packs(self) -> None:
        registry = reading_source_plan.load_runtime_source_registry()

        self.assertEqual(
            registry["routes"]["selection"]["required_always"],
            ["selection/xieji-bianfang-shu", "selection/xingli-kaoyuan"],
        )
        self.assertEqual(
            registry["routes"]["selection"]["comparison_only"],
            ["selection/yuqia-ji", "selection/donggong-zeri"],
        )
        self.assertEqual(
            registry["routes"]["physiognomy"]["comparison_only"],
            ["physiognomy/bingjian"],
        )

    def test_source_audit_never_reads_the_global_production_rule_cache(self) -> None:
        with mock.patch.object(
            reading_evidence_bundle,
            "production_evidence_rules",
            side_effect=AssertionError("global evidence cache must not be read"),
        ):
            report = completeness.audit_source_applicability("liuyao", root=ROOT)

        self.assertFalse(report["ready"], report)
        self.assertTrue(report["findings"])

    def test_every_runtime_route_has_a_real_dedicated_provider_identity(self) -> None:
        self.assertEqual(set(completeness.PROVIDER_CLASSES), EXPECTED_SYSTEMS)
        for system, provider_class in completeness.PROVIDER_CLASSES.items():
            with self.subTest(system=system):
                self.assertNotEqual(provider_class.__name__, "StructuredChartProvider")
                self.assertTrue(provider_class.provider_id.startswith("mingli-master."))
                self.assertNotIn("structured", provider_class.provider_id)
                self.assertTrue(str(provider_class.provider_version).strip())

    def test_capability_fields_are_nonempty_unique_and_executable_names(self) -> None:
        expected_extension_outputs = {
            "bazi": {
                "year_layers",
                "month_layers",
                "day_layers",
                "dimension_fact_scope",
                "life_kline",
            },
            "fortune": {
                "target_period",
                "available_periods",
                "period_markers",
            },
            "ziwei": {
                "active_major_limit",
                "annual_layers",
                "monthly_layers",
                "dimension_fact_scope",
            },
            "luming-nayin": {"dimension_fact_scope"},
        }
        for system in EXPECTED_SYSTEMS:
            capability = PROVIDER_CAPABILITIES[system]
            with self.subTest(system=system):
                self.assertIn(capability.mode, {"calculation", "observation_driven_ready"})
                for field in (
                    capability.objects,
                    capability.horizons,
                    capability.dimensions,
                    capability.outputs,
                    capability.extension_outputs,
                ):
                    self.assertTrue(field)
                    self.assertEqual(len(field), len(set(field)))
                    self.assertTrue(all(str(item).strip() for item in field))
                if system in expected_extension_outputs:
                    self.assertEqual(
                        set(capability.extension_outputs),
                        expected_extension_outputs[system],
                    )
                self.assertEqual(
                    {binding.name for binding in capability.output_bindings},
                    set(capability.outputs),
                )
                self.assertEqual(
                    {
                        binding.name
                        for binding in capability.extension_output_bindings
                    },
                    set(capability.extension_outputs),
                )
                for binding in (
                    *capability.output_bindings,
                    *capability.extension_output_bindings,
                ):
                    self.assertTrue(binding.json_pointers)
                    self.assertTrue(
                        all(pointer.startswith("/") for pointer in binding.json_pointers)
                    )

    def test_fortune_declares_its_executable_day_and_week_horizons(self) -> None:
        self.assertEqual(
            set(PROVIDER_CAPABILITIES["fortune"].horizons),
            {"day", "week"},
        )
        self.assertIn(
            "reference_datetime",
            PROVIDER_CAPABILITIES["fortune"].required_inputs,
        )

    def test_completed_extension_cannot_escape_declared_dimensions_or_horizons(self) -> None:
        for system in EXPECTED_SYSTEMS:
            capability = PROVIDER_CAPABILITIES[system]
            base = CalculationResult.create(
                system=system,
                provider_id=completeness.PROVIDER_CLASSES[system].provider_id,
                provider_version=str(
                    completeness.PROVIDER_CLASSES[system].provider_version
                ),
                input_payload={"probe": system},
                facts={"probe": system},
            )
            unknown_dimension = _attach_extension(
                base,
                ("not_declared",),
                {"kind": capability.horizons[0]},
                status="complete",
                facts={"probe": True},
            )
            unknown_horizon = _attach_extension(
                base,
                (capability.dimensions[0],),
                {"kind": "not_declared"},
                status="complete",
                facts={"probe": True},
            )
            with self.subTest(system=system, field="dimension"):
                self.assertEqual(unknown_dimension.fact_extension.status, "unsupported")
            with self.subTest(system=system, field="horizon"):
                self.assertEqual(unknown_horizon.fact_extension.status, "unsupported")

    def test_empty_applicability_rules_are_never_runtime_eligible(self) -> None:
        template = next(
            iter(
                load_evidence_rules(
                    ROOT / "references" / "index" / "evidence-rules.jsonl"
                )
            )
        )
        unbound = replace(template, required_fact_predicates=())
        self.assertFalse(match_rule(unbound, ())[0])

        eligible = reading_evidence_bundle._eligible_rules(
            {
                "system": "bazi",
                "sources": [{"pack": "bazi/ditiansui-chanwei"}],
            },
            (),
        )

        self.assertEqual(eligible, {})

    def test_taiyi_year_extension_is_bound_to_the_calculated_annual_board(self) -> None:
        provider = TaiyiProvider(ROOT)
        calculation = provider.calculate(
            ReadingRequest(
                query="核对 2024 年局",
                action="new",
                system="taiyi",
                reference_datetime="2024-06-21T12:00:00",
                timezone="Asia/Shanghai",
                location="上海",
            )
        )

        extended = provider.extend(
            calculation,
            ("state",),
            {"kind": "year", "start": "2035", "end": "2035"},
        )

        self.assertEqual(extended.fact_extension.status, "unsupported")

        ziwei = CalculationResult.create(
            system="ziwei",
            provider_id=completeness.PROVIDER_CLASSES["ziwei"].provider_id,
            provider_version=str(
                completeness.PROVIDER_CLASSES["ziwei"].provider_version
            ),
            input_payload={"probe": "ziwei"},
            facts={"probe": "ziwei"},
        )
        for horizon in (
            {
                "kind": "year",
                "start": "2025",
                "end": "2025",
                "target_date": "2025-02-01",
            },
            {"kind": "life", "target_date": "2025-02-01"},
        ):
            with self.subTest(horizon=horizon):
                result = _attach_extension(
                    ziwei,
                    (PROVIDER_CAPABILITIES["ziwei"].dimensions[0],),
                    horizon,
                    status="complete",
                    facts={"probe": True},
                )
                self.assertEqual(result.fact_extension.status, "unsupported")

    def test_instant_routes_reject_bounded_date_ranges(self) -> None:
        for system in ("liuyao", "meihua", "qimen", "fengshui", "physiognomy"):
            base = CalculationResult.create(
                system=system,
                provider_id=completeness.PROVIDER_CLASSES[system].provider_id,
                provider_version=str(
                    completeness.PROVIDER_CLASSES[system].provider_version
                ),
                input_payload={"probe": system},
                facts={"probe": system},
            )
            extended = _attach_extension(
                base,
                (PROVIDER_CAPABILITIES[system].dimensions[0],),
                {"kind": "instant", "start": "2099-01-01", "end": "2099-01-02"},
                status="complete",
                facts={"probe": True},
            )
            with self.subTest(system=system):
                self.assertEqual(extended.fact_extension.status, "unsupported")

    def test_bazi_never_binds_an_implicit_wall_clock_to_identical_input(self) -> None:
        request = ReadingRequest(
            query="核对本命盘",
            action="new",
            system="bazi",
            timezone="Asia/Shanghai",
            location="上海",
            chart_data={"pillars": ["甲子", "丙寅", "壬辰", "辛酉"]},
        )
        provider = BaziProvider(ROOT)
        with mock.patch(
            "reading_engine.providers.bazi_calc._resolve_as_of",
            side_effect=("2026-07-24T23:00:00+08:00", "2026-07-24T23:00:01+08:00"),
        ):
            first = provider.calculate(request)
            second = provider.calculate(request)

        self.assertEqual(first.input_hash, second.input_hash)
        self.assertEqual(first.result_hash, second.result_hash)

    def test_fortune_and_liuren_reject_missing_reference_time(self) -> None:
        fortune_request = ReadingRequest(
            query="看目标日",
            action="new",
            system="fortune",
            birth_data={
                "birth_datetime": "2000-10-18T06:45:00",
                "timezone": "Asia/Shanghai",
                "location": "上海",
                "gender": "male",
            },
        )
        liuren_request = ReadingRequest(
            query="看此事",
            action="new",
            system="liuren",
            timezone="Asia/Shanghai",
            location="上海",
        )

        with self.assertRaisesRegex(ValueError, "reference_datetime"):
            FortuneProvider(ROOT).calculate(fortune_request)
        with self.assertRaisesRegex(ValueError, "event_datetime|reference_datetime"):
            LiurenProvider(ROOT).calculate(liuren_request)

    def test_liuren_direct_provider_rejects_undeclared_defaults(self) -> None:
        for changes, missing in (({"timezone": None}, "timezone"),):
            payload = {
                "query": "看此事",
                "action": "new",
                "system": "liuren",
                "reference_datetime": "2026-07-24T12:00:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海",
                **changes,
            }
            request = ReadingRequest(**payload)
            with self.subTest(missing=missing):
                self.assertIn(
                    missing,
                    missing_required_inputs("liuren", request),
                )
                with self.assertRaisesRegex(ValueError, missing):
                    LiurenProvider(ROOT).calculate(request)

    def test_luming_birth_mode_does_not_request_unused_gender(self) -> None:
        request = ReadingRequest(
            query="核对禄命事实",
            action="new",
            system="luming-nayin",
            birth_data={
                "birth_datetime": "2000-10-18T06:45:00",
                "timezone": "Asia/Shanghai",
                "location": "上海",
            },
        )

        self.assertEqual(missing_required_inputs("luming-nayin", request), ())

    def test_extension_horizon_rejects_silently_ignored_keys(self) -> None:
        base = CalculationResult.create(
            system="qimen",
            provider_id=completeness.PROVIDER_CLASSES["qimen"].provider_id,
            provider_version=str(
                completeness.PROVIDER_CLASSES["qimen"].provider_version
            ),
            input_payload={"probe": "qimen"},
            facts={"probe": "qimen"},
        )

        extended = _attach_extension(
            base,
            (PROVIDER_CAPABILITIES["qimen"].dimensions[0],),
            {"kind": "instant", "ignored": "2099-01-01"},
            status="complete",
            facts={"probe": True},
        )

        self.assertEqual(extended.fact_extension.status, "unsupported")


if __name__ == "__main__":
    unittest.main()
