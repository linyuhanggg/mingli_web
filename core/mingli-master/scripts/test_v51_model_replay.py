"""Task 10 model-independent replay evaluation contracts."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_model_replay


ROUTING_CASES = ROOT / "tests/replay/mingli-routing-cases.jsonl"
ANSWER_CASES = ROOT / "tests/replay/mingli-answer-cases.jsonl"
BLIND_PREDICTIONS = (
    ROOT / "tests/replay/mingli-answer-predictions.partial-pillars.jsonl"
)


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _review_for(prediction: dict, *, unsupported: bool = False) -> dict:
    return {
        "case_id": prediction["case_id"],
        "prediction_sha256": run_model_replay.canonical_row_sha256(prediction),
        "reviewer": {
            "reviewer_id": "reviewer-anonymous-1",
            "reviewer_kind": "independent_agent",
            "independent": True,
            "blinded_run_label": "blind-run-a",
        },
        "direct_answer": True,
        "evidence_relevant": True,
        "naturalness": 4,
        "main_point_clear": True,
        "plain_language": 4,
        "useful_specificity": 4,
        "certainty_calibrated": True,
        "ambient_context_clean": True,
        "template_smell": False,
        "main_answer_claims_complete": True,
        "claim_reviews": [
            {
                "claim_index": 0,
                "claim_text": prediction["prediction"]["main_answer"],
                "trace_indexes": [0],
                "unsupported": unsupported,
            }
        ],
    }


class ModelReplayTests(unittest.TestCase):
    def test_answer_fixture_catalog_and_self_hashes_match_the_exporter(self) -> None:
        from scripts import export_v51_answer_cases

        rows = _rows(ANSWER_CASES)
        self.assertEqual(
            {row["case_id"] for row in rows},
            set(export_v51_answer_cases.scenario_ids()),
        )
        for row in rows:
            self.assertEqual(
                row["brief_sha256"],
                run_model_replay.canonical_value_sha256(row["brief"]),
                row["case_id"],
            )
            self.assertNotIn("artifacts", row, row["case_id"])
            self.assertNotIn("fixed_artifacts", row, row["case_id"])
            self.assertNotIn("prompt", row, row["case_id"])

    def test_production_contract_does_not_bind_a_host_model(self) -> None:
        production_paths = [
            ROOT / "SKILL.md",
            ROOT / "scripts/reading_transaction.py",
            *sorted((ROOT / "scripts/reading_engine").glob("*.py")),
        ]
        forbidden = re.compile(
            r"\b(?:gpt|glm|qwen|terra|sol)\b|"
            r"selected_model|model_provider|reasoning_(?:level|effort)",
            re.IGNORECASE,
        )
        for path in production_paths:
            self.assertIsNone(forbidden.search(path.read_text(encoding="utf-8")), path)

    def test_routing_fixture_covers_all_routes_and_conversation_boundaries(self) -> None:
        rows = _rows(ROUTING_CASES)
        systems = {
            row["expected"]["system"]
            for row in rows
            if row["expected"].get("system")
        }
        self.assertEqual(
            systems,
            {
                "bazi", "fortune", "luming-nayin", "xingming", "ziwei",
                "liuren", "liuyao", "meihua", "qimen", "taiyi",
                "selection", "fengshui", "physiognomy",
            },
        )
        tags = {tag for row in rows for tag in row["coverage_tags"]}
        self.assertTrue(
            {
                "ordinary_negative", "paraphrase", "image", "missing_fact",
                "resume", "continue", "correct", "recast", "source_conflict",
                "cross_check_bazi_ziwei", "cross_check_liuren_liuyao",
            }
            <= tags
        )

    def test_answer_briefs_use_only_synthetic_public_inputs(self) -> None:
        rows = _rows(ANSWER_CASES)
        self.assertEqual(len(rows), 9)
        for row in rows:
            serialized = json.dumps(row["brief"], ensure_ascii=False)
            self.assertNotIn("/Users/", serialized)
            self.assertNotIn("credential", serialized.casefold())
            self.assertNotIn("state_token", serialized)
            self.assertNotIn("reading_id", serialized)
            self.assertNotIn("counter_evidence", serialized)

    def test_source_conflict_route_does_not_prejudge_compiled_evidence(self) -> None:
        row = next(
            item for item in _rows(ROUTING_CASES)
            if item["case_id"] == "route-source-conflict"
        )
        self.assertNotIn("source_relationship", row["input"]["facts"])
        self.assertNotIn("cross_check_purpose", row["expected"])

    def test_answer_fixture_covers_delivery_quality_situations(self) -> None:
        tags = {tag for row in _rows(ANSWER_CASES) for tag in row["coverage_tags"]}
        self.assertTrue(
            {
                "broad_overview", "one_sentence", "explain_plainly",
                "continuation", "correction", "zero_evidence",
                "ambient_context_noise", "cross_system",
                "exact_event_boundary", "horizon_boundary", "short_answer",
                "partial_luck_sequence", "salience_candidates",
            }
            <= tags,
        )

    def test_generation_packet_materializer_exposes_only_public_inputs(self) -> None:
        from scripts import export_v51_answer_cases

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill_a = root / "a.md"
            skill_b = root / "b.md"
            skill_a.write_text("arm a", encoding="utf-8")
            skill_b.write_text("arm b", encoding="utf-8")
            output = root / "packet-set"
            manifest = export_v51_answer_cases.materialize_generation_packets(
                rows=_rows(ANSWER_CASES),
                output_dir=output,
                skill_snapshots=(("run-a", skill_a), ("run-b", skill_b)),
            )

            self.assertEqual(manifest["case_count"], 9)
            self.assertEqual(
                {item["label"] for item in manifest["skill_snapshots"]},
                {"run-a", "run-b"},
            )
            for item in manifest["packets"]:
                packet = json.loads(
                    (output / item["path"]).read_text(encoding="utf-8")
                )
                self.assertEqual(
                    set(packet), {"case_id", "brief_sha256", "brief"}
                )
                self.assertNotIn(
                    "review_rubric", json.dumps(packet, ensure_ascii=False)
                )
                self.assertEqual(
                    run_model_replay.canonical_value_sha256(packet),
                    item["sha256"],
                )

    def test_partial_pillar_case_keeps_sequence_but_never_timing(self) -> None:
        row = next(
            item for item in _rows(ANSWER_CASES)
            if item["case_id"] == "answer-bazi-partial-pillars-overview"
        )
        brief = row["brief"]
        luck_fact = next(
            fact
            for fact in brief["facts"]
            if fact["ref"].endswith("/calculated/bazi/luck_cycles")
        )
        self.assertEqual(luck_fact["value"]["status"], "sequence_only")
        self.assertEqual(len(luck_fact["value"]["cycles"]), 10)
        for cycle in luck_fact["value"]["cycles"]:
            self.assertEqual(set(cycle), {"sequence", "pillar"})
        rendered = json.dumps(brief, ensure_ascii=False)
        for banned in (
            "start_age_years",
            "approximate_start_datetime",
            "boundary_term",
        ):
            self.assertNotIn(banned, rendered)
        candidates = next(
            finding
            for finding in brief["findings"]
            if finding["kind_id"] == "finding.interpretive_candidates"
        )
        signals = candidates["data"]["salience_signals"]
        self.assertTrue(signals)
        for item in signals:
            self.assertEqual(item["status"], "mechanical_candidate")
            self.assertIsNone(item["hard_verdict"])
        forbidden = row["review_rubric"]["forbidden"]
        for term in ("起运岁数", "当前大运", "百分比"):
            self.assertIn(term, forbidden)
        self.assertIn("broad_overview", row["coverage_tags"])
        timing_limit_kinds = {
            limit["kind_id"] for limit in brief["limits"]
        }
        self.assertIn("limit.partial_luck_timing", timing_limit_kinds)
        self.assertEqual(
            brief["request_view"]["dimension_ids"], ["overview"]
        )
        self.assertEqual(brief["request_view"]["horizon"]["kind_id"], "life")
        self.assertEqual(
            {scope["dimension_id"] for scope in brief["claim_scopes"]},
            {"overview"},
        )

    def test_ambient_context_cases_forbid_host_memory_in_the_answer(self) -> None:
        rows = [
            row for row in _rows(ANSWER_CASES)
            if "ambient_context_noise" in row["coverage_tags"]
        ]
        self.assertTrue(rows)
        for row in rows:
            noise = row["ambient_context"]
            self.assertTrue(isinstance(noise, list) and noise)
            forbidden = row["review_rubric"]["forbidden"]
            for item in noise:
                self.assertIn(item, forbidden)
            artifacts = json.dumps(row["brief"], ensure_ascii=False)
            for item in noise:
                self.assertNotIn(item, artifacts)

    def test_answer_fixture_pins_no_expected_public_prose(self) -> None:
        for row in _rows(ANSWER_CASES):
            for banned in (
                "expected_answer",
                "expected_main_answer",
                "expected_public_copy",
                "reference_answer",
                "gold_answer",
            ):
                self.assertNotIn(banned, row, row["case_id"])
            self.assertEqual(
                set(row["review_rubric"]) - {"required", "forbidden"},
                set(),
                row["case_id"],
            )

    def test_answer_case_ids_and_digests_are_unique(self) -> None:
        rows = _rows(ANSWER_CASES)
        ids = [row["case_id"] for row in rows]
        self.assertEqual(len(set(ids)), len(ids))
        digests = [row["brief_sha256"] for row in rows]
        self.assertEqual(len(set(digests)), len(digests))

    def test_scoring_rejects_brief_drift_and_reports_honest_review_coverage(self) -> None:
        case = _rows(ANSWER_CASES)[0]
        public_fact_refs = [item["ref"] for item in case["brief"]["facts"]]
        public_evidence_refs = [
            item["ref"] for item in case["brief"]["evidence"]
        ]
        good = {
            "case_id": case["case_id"],
            "brief_sha256": case["brief_sha256"],
            "prediction": {
                "main_answer": "主结论以固定事实与证据为边界。",
                "claim_traces": [
                    {
                        "fact_refs": public_fact_refs[:1],
                        "evidence_refs": public_evidence_refs[:1],
                        "counter_evidence_refs": [],
                    }
                ]
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 80,
                "latency_ms": 250,
                "reported_cost": 0.01,
            },
        }
        review = _review_for(good)
        report = run_model_replay.score_predictions(
            [case], [good], kind="answer", reviews=[review], run_label="blind-run-a"
        )
        self.assertEqual(report["brief_invariance_rate"], 1.0)
        self.assertEqual(report["reference_violation_rate"], 0.0)
        self.assertEqual(report["unsupported_claim_rate"], 0.0)
        self.assertEqual(report["direct_answer_rate"], 1.0)
        self.assertEqual(report["independent_review_coverage"], 1.0)
        self.assertEqual(report["main_answer_claim_review_coverage"], 1.0)
        self.assertEqual(report["usage"]["coverage"], 1.0)

        with self.assertRaises(ValueError):
            run_model_replay.score_predictions([case], [good], kind="answer")

        stale_review = _review_for(good)
        stale_review["prediction_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            run_model_replay.score_predictions(
                [case], [good], kind="answer", reviews=[stale_review],
                run_label="blind-run-a",
            )

        unsupported = json.loads(json.dumps(good))
        unsupported["prediction"]["claim_traces"][0]["fact_refs"] = ["fact:/not-admitted"]
        unsupported_report = run_model_replay.score_predictions(
            [case], [unsupported], kind="answer", reviews=[_review_for(unsupported)],
            run_label="blind-run-a",
        )
        self.assertEqual(unsupported_report["reference_violation_rate"], 1.0)

        leaked_counter = json.loads(json.dumps(good))
        leaked_counter["prediction"]["claim_traces"][0][
            "counter_evidence_refs"
        ] = ["private:counter-evidence"]
        leaked_counter_report = run_model_replay.score_predictions(
            [case], [leaked_counter], kind="answer",
            reviews=[_review_for(leaked_counter)], run_label="blind-run-a",
        )
        self.assertEqual(
            leaked_counter_report["reference_violation_rate"], 1.0
        )

        semantically_unsupported = json.loads(json.dumps(good))
        semantic_report = run_model_replay.score_predictions(
            [case], [semantically_unsupported], kind="answer",
            reviews=[_review_for(semantically_unsupported, unsupported=True)],
            run_label="blind-run-a",
        )
        self.assertEqual(semantic_report["unsupported_claim_rate"], 1.0)

        mixed_claims = json.loads(json.dumps(good))
        mixed_claims["prediction"]["claim_traces"].append(
            json.loads(json.dumps(mixed_claims["prediction"]["claim_traces"][0]))
        )
        mixed_review = _review_for(mixed_claims, unsupported=True)
        mixed_review["claim_reviews"].append(
            {
                "claim_index": 1,
                "claim_text": "第二条独立主张。",
                "trace_indexes": [1],
                "unsupported": False,
            }
        )
        mixed_report = run_model_replay.score_predictions(
            [case], [mixed_claims], kind="answer", reviews=[mixed_review],
            run_label="blind-run-a",
        )
        self.assertEqual(mixed_report["unsupported_claim_rate"], 0.5)

        untraced_claim = json.loads(json.dumps(good))
        untraced_claim["prediction"]["main_answer"] += " 并保证一定升职。"
        untraced_review = _review_for(untraced_claim)
        untraced_review["claim_reviews"].append(
            {
                "claim_index": 1,
                "claim_text": "保证一定升职。",
                "trace_indexes": [],
                "unsupported": True,
            }
        )
        untraced_report = run_model_replay.score_predictions(
            [case], [untraced_claim], kind="answer", reviews=[untraced_review],
            run_label="blind-run-a",
        )
        self.assertEqual(untraced_report["unsupported_claim_rate"], 0.5)
        self.assertEqual(untraced_report["untraced_claim_rate"], 0.5)

        incomplete_review = _review_for(good)
        incomplete_review["claim_reviews"] = []
        with self.assertRaises(ValueError):
            run_model_replay.score_predictions(
                [case], [good], kind="answer", reviews=[incomplete_review],
                run_label="blind-run-a",
            )

        invalid_review = _review_for(good)
        invalid_review["direct_answer"] = "false"
        with self.assertRaises(ValueError):
            run_model_replay.score_predictions(
                [case], [good], kind="answer", reviews=[invalid_review],
                run_label="blind-run-a",
            )

        invalid_usage = json.loads(json.dumps(good))
        invalid_usage["usage"]["latency_ms"] = -1
        with self.assertRaises(ValueError):
            run_model_replay.score_predictions(
                [case], [invalid_usage], kind="answer", reviews=[_review_for(invalid_usage)],
                run_label="blind-run-a",
            )

        non_finite_usage = json.loads(json.dumps(good))
        non_finite_usage["usage"]["reported_cost"] = float("nan")
        with self.assertRaises(ValueError):
            run_model_replay.score_predictions(
                [case], [non_finite_usage], kind="answer",
                reviews=[_review_for(good)], run_label="blind-run-a",
            )

        drifted = json.loads(json.dumps(good))
        drifted["brief_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            run_model_replay.score_predictions(
                [case], [drifted], kind="answer", reviews=[_review_for(drifted)],
                run_label="blind-run-a",
            )

        private_artifacts = json.loads(json.dumps(good))
        private_artifacts["artifact_identity"] = {"obsolete": True}
        with self.assertRaises(ValueError):
            run_model_replay.score_predictions(
                [case], [private_artifacts], kind="answer",
                reviews=[_review_for(private_artifacts)],
                run_label="blind-run-a",
            )

    def test_cli_compares_external_prediction_files_without_selecting_a_model(self) -> None:
        cases = _rows(ROUTING_CASES)
        predictions = [
            {
                "case_id": case["case_id"],
                "prediction": case["expected"],
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "latency_ms": 50,
                    "reported_cost": 0.001,
                },
            }
            for case in cases
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "predictions.jsonl"
            path.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in predictions),
                encoding="utf-8",
            )
            report = run_model_replay.evaluate_files(
                cases_path=ROUTING_CASES,
                prediction_paths=(path,),
                kind="routing",
            )

        self.assertEqual(report["runs"][0]["route_correctness"], 1.0)
        self.assertNotIn("selected_model", json.dumps(report).casefold())

    def test_scoring_rejects_partial_case_sets(self) -> None:
        cases = _rows(ROUTING_CASES)[:2]
        prediction = {
            "case_id": cases[0]["case_id"],
            "prediction": cases[0]["expected"],
        }
        with self.assertRaises(ValueError):
            run_model_replay.score_predictions(cases, [prediction], kind="routing")

    def test_scoring_reports_unavailable_usage_without_fabricating_zeroes(self) -> None:
        case = _rows(ROUTING_CASES)[0]
        prediction = {"case_id": case["case_id"], "prediction": case["expected"]}
        report = run_model_replay.score_predictions(
            [case], [prediction], kind="routing"
        )
        self.assertEqual(report["usage"]["coverage"], 0.0)
        self.assertIsNone(report["usage"]["input_tokens_mean"])


class AnswerDeliveryReviewTests(unittest.TestCase):
    """Delivery review fields are required, typed, bounded and reported."""

    def setUp(self) -> None:
        self.case = _rows(ANSWER_CASES)[0]
        self.prediction = {
            "case_id": self.case["case_id"],
            "brief_sha256": self.case["brief_sha256"],
            "prediction": {
                "main_answer": "主结论先说清，再用决定性材料解释。",
                "claim_traces": [
                    {
                        "fact_refs": [
                            item["ref"]
                            for item in self.case["brief"]["facts"][:1]
                        ],
                        "evidence_refs": [
                            item["ref"]
                            for item in self.case["brief"]["evidence"][:1]
                        ],
                        "counter_evidence_refs": [],
                    }
                ],
            },
            "usage": {
                "input_tokens": 120,
                "output_tokens": 90,
                "latency_ms": 300,
                "reported_cost": 0.02,
            },
        }

    def _score(self, review: dict) -> dict:
        return run_model_replay.score_predictions(
            [self.case],
            [self.prediction],
            kind="answer",
            reviews=[review],
            run_label="blind-run-a",
        )

    def test_valid_delivery_review_is_accepted_and_reported(self) -> None:
        report = self._score(_review_for(self.prediction))

        self.assertEqual(report["main_point_clear_rate"], 1.0)
        self.assertEqual(report["plain_language_mean"], 4.0)
        self.assertEqual(report["useful_specificity_mean"], 4.0)
        self.assertEqual(report["certainty_calibrated_rate"], 1.0)
        self.assertEqual(report["ambient_memory_contamination_rate"], 0.0)
        self.assertEqual(report["template_smell_rate"], 0.0)
        self.assertEqual(report["naturalness_mean"], 4.0)
        self.assertEqual(
            report["reviewer_kind_counts"],
            {"human": 0, "independent_agent": 1},
        )

    def test_reviewer_kind_is_explicit_and_bounded(self) -> None:
        for value in (None, "", "model", "self_review"):
            review = _review_for(self.prediction)
            review["reviewer"]["reviewer_kind"] = value
            with self.assertRaises(ValueError, msg=repr(value)):
                self._score(review)

    def test_delivery_metrics_average_across_reviews(self) -> None:
        second_case = _rows(ANSWER_CASES)[1]
        second_prediction = {
            "case_id": second_case["case_id"],
            "brief_sha256": second_case["brief_sha256"],
            "prediction": {
                "main_answer": "第二个案例的主结论。",
                "claim_traces": [
                    {
                        "fact_refs": [
                            item["ref"]
                            for item in second_case["brief"]["facts"][:1]
                        ],
                        "evidence_refs": [
                            item["ref"]
                            for item in second_case["brief"]["evidence"][:1]
                        ],
                        "counter_evidence_refs": [],
                    }
                ],
            },
            "usage": {
                "input_tokens": 80,
                "output_tokens": 60,
                "latency_ms": 200,
                "reported_cost": 0.01,
            },
        }
        strong = _review_for(self.prediction)
        weak = _review_for(second_prediction)
        weak["main_point_clear"] = False
        weak["plain_language"] = 2
        weak["useful_specificity"] = 3
        weak["certainty_calibrated"] = False
        weak["ambient_context_clean"] = False
        weak["template_smell"] = True

        report = run_model_replay.score_predictions(
            [self.case, second_case],
            [self.prediction, second_prediction],
            kind="answer",
            reviews=[strong, weak],
            run_label="blind-run-a",
        )

        # Two reviews, one strong and one weak: every metric is a real mean.
        self.assertEqual(report["main_point_clear_rate"], 0.5)
        self.assertEqual(report["plain_language_mean"], 3.0)
        self.assertEqual(report["useful_specificity_mean"], 3.5)
        self.assertEqual(report["certainty_calibrated_rate"], 0.5)
        self.assertEqual(report["ambient_memory_contamination_rate"], 0.5)
        self.assertEqual(report["template_smell_rate"], 0.5)

    def test_single_weak_review_reports_floor_values(self) -> None:
        weak = _review_for(self.prediction)
        weak["main_point_clear"] = False
        weak["plain_language"] = 2
        weak["useful_specificity"] = 3
        weak["certainty_calibrated"] = False
        weak["ambient_context_clean"] = False
        weak["template_smell"] = True
        report = self._score(weak)

        self.assertEqual(report["main_point_clear_rate"], 0.0)
        self.assertEqual(report["plain_language_mean"], 2.0)
        self.assertEqual(report["useful_specificity_mean"], 3.0)
        self.assertEqual(report["certainty_calibrated_rate"], 0.0)
        self.assertEqual(report["ambient_memory_contamination_rate"], 1.0)
        self.assertEqual(report["template_smell_rate"], 1.0)

    def test_empty_case_and_prediction_sets_are_rejected(self) -> None:
        for kind in ("answer", "routing"):
            with self.assertRaises(ValueError, msg=kind):
                run_model_replay.score_predictions([], [], kind=kind)

    def test_every_new_delivery_field_is_mandatory(self) -> None:
        for field in (
            "main_point_clear",
            "plain_language",
            "useful_specificity",
            "certainty_calibrated",
            "ambient_context_clean",
            "template_smell",
        ):
            review = _review_for(self.prediction)
            review.pop(field)
            with self.assertRaises(ValueError, msg=field):
                self._score(review)

    def test_delivery_boolean_fields_reject_strings(self) -> None:
        for field in (
            "main_point_clear",
            "certainty_calibrated",
            "ambient_context_clean",
            "template_smell",
        ):
            review = _review_for(self.prediction)
            review[field] = "true"
            with self.assertRaises(ValueError, msg=field):
                self._score(review)

    def test_delivery_scores_reject_out_of_range_values(self) -> None:
        for field in ("plain_language", "useful_specificity"):
            for value in (0, 0.9, 5.1, 6):
                review = _review_for(self.prediction)
                review[field] = value
                with self.assertRaises(ValueError, msg=f"{field}={value}"):
                    self._score(review)

    def test_delivery_scores_reject_booleans_and_non_numbers(self) -> None:
        for field in ("plain_language", "useful_specificity"):
            for value in (True, "4"):
                review = _review_for(self.prediction)
                review[field] = value
                with self.assertRaises(ValueError, msg=f"{field}={value!r}"):
                    self._score(review)

    def test_delivery_review_must_not_be_embedded_in_predictions(self) -> None:
        embedded = json.loads(json.dumps(self.prediction))
        embedded["review"] = _review_for(self.prediction)
        with self.assertRaises(ValueError):
            run_model_replay.score_predictions(
                [self.case],
                [embedded],
                kind="answer",
                reviews=[_review_for(embedded)],
                run_label="blind-run-a",
            )

    def test_report_schema_version_declares_delivery_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            predictions_path = root / "blind-run-a.jsonl"
            reviews_path = root / "blind-run-a-review.jsonl"
            predictions_path.write_text(
                json.dumps(self.prediction, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            review = _review_for(self.prediction)
            review["reviewer"]["blinded_run_label"] = "blind-run-a"
            reviews_path.write_text(
                json.dumps(review, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            cases_path = root / "cases.jsonl"
            cases_path.write_text(
                json.dumps(self.case, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            report = run_model_replay.evaluate_files(
                cases_path=cases_path,
                prediction_paths=(predictions_path,),
                review_paths=(reviews_path,),
                kind="answer",
            )

        self.assertEqual(report["schema_version"], "mingli-model-replay-report-v2")
        self.assertEqual(report["runs"][0]["main_point_clear_rate"], 1.0)


class AnswerBriefStructureTests(unittest.TestCase):
    """Every fixture carries the real drafting boundary production uses.

    A reviewer cannot judge `certainty_calibrated` without the frozen claim
    scope and certainty ceiling, so the fixture must expose the same
    `ReadingBrief` shape the core hands the host model.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = _rows(ANSWER_CASES)

    def test_every_case_round_trips_as_a_reading_brief(self) -> None:
        from reading_engine.interface_contracts import ReadingBrief

        for row in self.rows:
            brief = row.get("brief")
            self.assertIsInstance(brief, dict, row["case_id"])
            restored = ReadingBrief.from_dict(brief)
            self.assertEqual(restored.to_dict(), brief, row["case_id"])

    def test_every_case_publishes_claim_scopes_with_a_certainty_ceiling(self) -> None:
        for row in self.rows:
            scopes = row["brief"]["claim_scopes"]
            self.assertTrue(scopes, row["case_id"])
            for scope in scopes:
                self.assertTrue(
                    str(scope["certainty_ceiling_id"]).strip(), row["case_id"]
                )
                self.assertTrue(scope["allowed_kind_ids"], row["case_id"])

    def test_vocabulary_is_exactly_the_production_brief_projection(self) -> None:
        for row in self.rows:
            brief = row["brief"]
            expected_ids: set[str] = set()
            for scope in brief["claim_scopes"]:
                expected_ids.add(scope["dimension_id"])
                expected_ids.update(scope["allowed_kind_ids"])
                expected_ids.add(scope["certainty_ceiling_id"])
            expected_ids.update(fact["kind_id"] for fact in brief["facts"])
            expected_ids.update(limit["kind_id"] for limit in brief["limits"])
            expected_ids.update(finding["kind_id"] for finding in brief["findings"])
            vocabulary = {item["id"]: item for item in brief["vocabulary"]}
            self.assertEqual(set(vocabulary), expected_ids, row["case_id"])
            for term in vocabulary.values():
                self.assertTrue(term["label"].strip(), row["case_id"])

    def test_claim_scopes_cover_answerable_dimensions_or_declare_a_limit(self) -> None:
        for row in self.rows:
            brief = row["brief"]
            requested = set(brief["request_view"]["dimension_ids"])
            scoped = {scope["dimension_id"] for scope in brief["claim_scopes"]}
            self.assertTrue(scoped, row["case_id"])
            self.assertTrue(scoped <= requested, row["case_id"])
            declared = {
                ref
                for limit in brief["limits"]
                if limit["kind_id"] == "limit.unsupported_dimension"
                for ref in limit["detail_ids"]
            }
            self.assertEqual(requested - scoped - declared, set(), row["case_id"])

    def test_claim_scope_references_are_closed_inside_the_public_brief(self) -> None:
        for row in self.rows:
            brief = row["brief"]
            admitted_facts = {fact["ref"] for fact in brief["facts"]}
            admitted_evidence = {item["ref"] for item in brief["evidence"]}
            for scope in brief["claim_scopes"]:
                self.assertTrue(
                    set(scope["fact_refs"]) <= admitted_facts, row["case_id"]
                )
                self.assertTrue(
                    set(scope["evidence_refs"]) <= admitted_evidence, row["case_id"]
                )

    def test_public_facts_have_nonempty_display_text(self) -> None:
        for row in self.rows:
            for fact in row["brief"]["facts"]:
                self.assertTrue(fact["display_text"].strip(), row["case_id"])

    def test_source_gap_limit_matches_an_actual_source_gap(self) -> None:
        for row in self.rows:
            has_source_gap = any(
                limit["kind_id"] == "limit.source_gap"
                for limit in row["brief"]["limits"]
            )
            self.assertEqual(
                has_source_gap,
                not bool(row["brief"]["evidence"]),
                row["case_id"],
            )

    def test_zero_evidence_case_declares_a_source_gap(self) -> None:
        rows = [row for row in self.rows if "zero_evidence" in row["coverage_tags"]]
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row["brief"]["evidence"], [])
            kinds = {limit["kind_id"] for limit in row["brief"]["limits"]}
            self.assertIn("limit.source_gap", kinds, row["case_id"])

    def test_only_continuation_supplies_prior_answer(self) -> None:
        continuation = next(
            row for row in self.rows if "continuation" in row["coverage_tags"]
        )
        correction = next(
            row for row in self.rows if "correction" in row["coverage_tags"]
        )
        prior = continuation["brief"]["prior_answer"]
        self.assertIsInstance(prior, str, continuation["case_id"])
        self.assertTrue(prior.strip(), continuation["case_id"])
        self.assertIsNone(correction["brief"]["prior_answer"], correction["case_id"])

    def test_ambient_context_never_enters_the_brief(self) -> None:
        rows = [
            row for row in self.rows
            if "ambient_context_noise" in row["coverage_tags"]
        ]
        self.assertTrue(rows)
        for row in rows:
            serialized = json.dumps(row["brief"], ensure_ascii=False)
            for item in row["ambient_context"]:
                self.assertNotIn(item, serialized, row["case_id"])


class BlindPredictionMaterialTests(unittest.TestCase):
    """Fresh-context prediction material with mechanical gates only.

    The prediction is real natural prose drafted for the frozen brief; the
    independent blind review itself stays pending with the acceptor, so no
    review record is embedded anywhere.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = _rows(ANSWER_CASES)
        predictions = _rows(BLIND_PREDICTIONS)
        assert len(predictions) == 1
        cls.prediction = predictions[0]
        cls.case = next(
            row
            for row in cls.rows
            if row["case_id"] == cls.prediction["case_id"]
        )

    def test_prediction_is_bound_to_the_frozen_brief(self) -> None:
        self.assertEqual(
            self.prediction["brief_sha256"], self.case["brief_sha256"]
        )
        answer = self.prediction["prediction"]["main_answer"]
        self.assertIsInstance(answer, str)
        self.assertGreaterEqual(len(answer), 120)
        self.assertTrue(self.prediction["prediction"]["claim_traces"])

    def test_prediction_stays_inside_the_case_rubric(self) -> None:
        answer = self.prediction["prediction"]["main_answer"]
        forbidden_terms = [
            term
            for term in self.case["review_rubric"]["forbidden"].split("、")
            if term
        ]
        self.assertTrue(forbidden_terms)
        for term in forbidden_terms:
            self.assertNotIn(term, answer)
        for ambient in self.case["ambient_context"]:
            self.assertNotIn(ambient, answer)
        self.assertNotIn("%", answer)
        self.assertNotIn("置信", answer)

    def test_prediction_traces_close_against_the_public_brief(self) -> None:
        fact_refs = {fact["ref"] for fact in self.case["brief"]["facts"]}
        evidence_refs = {
            item["ref"] for item in self.case["brief"]["evidence"]
        }
        traced_fact_refs: set[str] = set()
        for trace in self.prediction["prediction"]["claim_traces"]:
            self.assertTrue(trace["fact_refs"])
            self.assertTrue(set(trace["fact_refs"]) <= fact_refs)
            self.assertTrue(set(trace["evidence_refs"]) <= evidence_refs)
            self.assertEqual(trace["counter_evidence_refs"], [])
            traced_fact_refs.update(trace["fact_refs"])
        self.assertIn(
            "fact:subject:synthetic/calculated/bazi/four_pillars",
            traced_fact_refs,
        )

    def test_prediction_carries_no_embedded_review(self) -> None:
        self.assertNotIn("review", self.prediction)
        cases = [self.case]
        predictions = [self.prediction]
        with self.assertRaises(ValueError):
            run_model_replay.score_predictions(
                cases, predictions, kind="answer"
            )

    def test_hand_written_prediction_does_not_claim_measured_usage(self) -> None:
        self.assertNotIn("usage", self.prediction)


if __name__ == "__main__":
    unittest.main()
