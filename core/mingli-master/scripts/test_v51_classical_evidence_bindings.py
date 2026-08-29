"""Task 7N independent classical-source and applicability binding contracts."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

import build_evidence_index
import generate_classical_evidence_bindings
from reading_engine.contracts import FactRef
from reading_engine.evidence_rules import load_evidence_rules, match_rule
from simplified_canonical import canonicalize


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "references/matrices/classical-evidence-bindings-v1.json"
INDEX = ROOT / "references/index/evidence-rules.jsonl"

QIONGTONG_RUNTIME_VERIFIED = {
    "QR-01-01",
    "QR-01-02",
    "QR-01-03",
    "QR-01-05",
    "QR-01-07",
    "QR-02-01",
    "QR-02-02",
    "QR-02-04",
    "QR-03-01",
    "QR-03-04",
    "QR-03-06",
    "QR-03-07",
    "QR-04-01",
    "QR-04-02",
    "QR-04-07",
    "QR-05-02",
    "QR-05-04",
    "QR-05-08",
}


class ClassicalEvidenceBindingTests(unittest.TestCase):
    def test_product_evidence_text_is_simplified_canonical(self) -> None:
        manifest = generate_classical_evidence_bindings.load_committed()
        records = build_evidence_index.compile_evidence_rules(
            root=ROOT,
            enforce_classical_bindings=False,
        )

        for record in records:
            for field in ("source_title", "chapter", "title", "quote"):
                self.assertEqual(record[field], canonicalize(record[field]))
            self.assertEqual(
                record["topics"],
                [canonicalize(topic) for topic in record["topics"]],
            )
        for binding in manifest["bindings"].values():
            for source in binding["classical_sources"]:
                self.assertEqual(
                    source["verbatim_quote"],
                    canonicalize(source["verbatim_quote"]),
                )

    def test_physiognomy_terminology_sources_use_substantive_text_not_headings(self) -> None:
        payload = generate_classical_evidence_bindings.load_committed()
        mayi_sources = payload["bindings"][
            "physiognomy/mayi-shenxiang#MR-02"
        ]["classical_sources"]
        shenxiang_sources = payload["bindings"][
            "physiognomy/shenxiang-quanbian#SR-02-04"
        ]["classical_sources"]

        self.assertEqual(
            {source["anchor"] for source in mayi_sources},
            {
                "fulltext.md#L55-L67",
                "fulltext.md#L116-L127",
                "fulltext.md#L258",
            },
        )
        self.assertEqual(
            [source["anchor"] for source in shenxiang_sources],
            ["fulltext.md#L1062-L1072"],
        )
        for source in (*mayi_sources, *shenxiang_sources):
            quote = source["verbatim_quote"].strip()
            self.assertTrue(quote)
            self.assertFalse(quote.startswith("#"), quote)
            self.assertNotIn("### 六府三才三停之圖", quote)

    def test_qiongtong_runtime_set_has_substantive_exact_sources_and_fails_closed_elsewhere(self) -> None:
        payload = generate_classical_evidence_bindings.load_committed()
        prefix = "bazi/qiongtong-baojian#"
        chapter_bindings = {
            rule_id.removeprefix(prefix): binding
            for rule_id, binding in payload["bindings"].items()
            if rule_id.startswith(prefix + "QR-")
            and rule_id.removeprefix(prefix) != "QR-00-01"
            and rule_id.removeprefix(prefix).split("-")[-1] != "00"
        }

        self.assertEqual(len(chapter_bindings), 40)
        for local_id, binding in chapter_bindings.items():
            with self.subTest(local_id=local_id):
                expected = (
                    "verified"
                    if local_id in QIONGTONG_RUNTIME_VERIFIED
                    else "inactive_unverified"
                )
                self.assertEqual(binding["verification_status"], expected)
                if expected == "verified":
                    self.assertEqual(
                        binding["mechanical_location_status"], "verified_exact"
                    )
                    self.assertTrue(binding["classical_sources"])
                    for source in binding["classical_sources"]:
                        quote = source["verbatim_quote"].strip()
                        self.assertTrue(quote)
                        self.assertFalse(quote.startswith("#"), quote)
                        self.assertNotIn("#### 三", quote)
                else:
                    self.assertEqual(binding["semantic_verification_status"], expected)

    def test_qiongtong_source_quotes_are_exact_at_the_pinned_lines(self) -> None:
        payload = generate_classical_evidence_bindings.load_committed()
        research_root = Path(
            os.environ.get(
                "MINGLI_RESEARCH_ROOT",
                ROOT / "__missing_external_research__",
            )
        ).resolve()
        for local_id in sorted(QIONGTONG_RUNTIME_VERIFIED):
            binding = payload["bindings"][
                f"bazi/qiongtong-baojian#{local_id}"
            ]
            for source in binding["classical_sources"]:
                with self.subTest(local_id=local_id, anchor=source["anchor"]):
                    path = research_root / source["path"]
                    self.assertEqual(
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                        source["sha256"],
                    )
                    line_number = int(source["anchor"].rsplit("L", 1)[1])
                    line = path.read_text(encoding="utf-8").splitlines()[
                        line_number - 1
                    ]
                    self.assertIn(source["verbatim_quote"], canonicalize(line))

    def test_qiongtong_runtime_summaries_preserve_month_specific_differences(self) -> None:
        records = {
            record["local_rule_id"]: record
            for record in build_evidence_index.compile_evidence_rules(
                root=ROOT, enforce_classical_bindings=False
            )
            if record["source_pack"] == "bazi/qiongtong-baojian"
        }

        self.assertIn("三月先取庚金、次用壬水", records["QR-01-01"]["quote"])
        self.assertNotIn("三月土厚，用甲疏土", records["QR-01-01"]["quote"])
        self.assertIn("六月先用丁火、次取甲木", records["QR-04-02"]["quote"])
        self.assertIn("十月癸水宜用庚辛", records["QR-05-08"]["quote"])
        self.assertIn("十一月专用丙火解冻", records["QR-05-08"]["quote"])
        self.assertIn("十二月宜丙火解冻", records["QR-05-08"]["quote"])

        expected_ranges = {
            "QR-01-01": "fulltext.md L41-L69",
            "QR-01-02": "fulltext.md L73-L101",
            "QR-01-03": "fulltext.md L105-L149",
            "QR-01-05": "fulltext.md L179-L207",
            "QR-01-07": "fulltext.md L247-L275",
            "QR-02-01": "fulltext.md L317-L382",
            "QR-02-02": "fulltext.md L386-L448",
            "QR-02-04": "fulltext.md L503-L557",
            "QR-03-01": "fulltext.md L769-L798",
            "QR-03-04": "fulltext.md L897-L929",
            "QR-03-06": "fulltext.md L981-L1002",
            "QR-03-07": "fulltext.md L1006-L1029",
            "QR-04-01": "fulltext.md L1072-L1133",
            "QR-04-02": "fulltext.md L1137-L1166",
            "QR-04-07": "fulltext.md L1348-L1405",
            "QR-05-02": "fulltext.md L1496-L1530",
            "QR-05-04": "fulltext.md L1587-L1625",
            "QR-05-08": "fulltext.md L1731-L1764",
        }
        self.assertEqual(
            {
                local_id: records[local_id]["source_anchor"]
                for local_id in expected_ranges
            },
            expected_ranges,
        )

    def test_conditional_observation_packs_bind_only_provider_activated_safe_rules(self) -> None:
        expected = {
            "fengshui/zangshu#R-02": "methodology_rule",
            "fengshui/xuexin-fu#XXF-R01": "methodology_rule",
            "fengshui/yangzhai-sanyao#YZS-R005": "methodology_rule",
            "fengshui/yangzhai-shishu#YZS-R014": "methodology_rule",
            "fengshui/hanlong-jing#R-01": "methodology_rule",
            "fengshui/huangdi-zhaijing#HDZJ-R006": "methodology_rule",
            "fengshui/yilong-jing#R-05": "methodology_rule",
            "physiognomy/liuzhuang-xiangfa#LZ-R01": "methodology_rule",
            "physiognomy/mayi-shenxiang#MR-02": "terminology_only",
            "physiognomy/shenxiang-quanbian#SR-02-04": "terminology_only",
        }
        records = {
            record["rule_id"]: record
            for record in build_evidence_index.compile_evidence_rules(
                root=ROOT, enforce_classical_bindings=False
            )
        }
        payload = generate_classical_evidence_bindings.load_committed()

        for rule_id, role in expected.items():
            with self.subTest(rule_id=rule_id):
                self.assertEqual(records[rule_id]["evidence_role"], role)
                self.assertIn(
                    {
                        "path_suffix": "/active_source_rule_ids",
                        "operator": "descendant_eq",
                        "value": rule_id,
                    },
                    records[rule_id]["required_fact_predicates"],
                )
                binding = payload["bindings"][rule_id]
                self.assertEqual(binding["verification_status"], "verified")
                self.assertEqual(binding["mechanical_location_status"], "verified_exact")
                self.assertTrue(binding["classical_sources"])

        mayi_sources = payload["bindings"][
            "physiognomy/mayi-shenxiang#MR-02"
        ]["classical_sources"]
        self.assertEqual(
            {source["anchor"] for source in mayi_sources},
            {
                "fulltext.md#L55-L67",
                "fulltext.md#L116-L127",
                "fulltext.md#L258",
            },
        )
        shenxiang_sources = payload["bindings"][
            "physiognomy/shenxiang-quanbian#SR-02-04"
        ]["classical_sources"]
        self.assertEqual(
            [source["anchor"] for source in shenxiang_sources],
            ["fulltext.md#L1062-L1072"],
        )
        for source in (*mayi_sources, *shenxiang_sources):
            quote = source["verbatim_quote"].strip()
            self.assertTrue(quote)
            self.assertFalse(quote.startswith("#"), quote)
            self.assertNotIn("### 六府三才三停之圖", quote)

    def test_group_b_mandatory_packs_have_exact_source_and_scope_bindings(self) -> None:
        def source(pack: str, sha256: str, line: int, quote: str) -> dict[str, str]:
            quote = canonicalize(quote)
            return {
                "path": f"references/fulltext/{pack}/fulltext.md",
                "sha256": sha256,
                "anchor": f"fulltext.md#L{line}",
                "verbatim_quote": quote,
                "verbatim_quote_sha256": hashlib.sha256(
                    quote.encode("utf-8")
                ).hexdigest(),
                "location": "research_tree",
            }

        nonempty = lambda path: {"path_suffix": path, "operator": "nonempty"}
        descendant = lambda path, value: {
            "path_suffix": path,
            "operator": "descendant_eq",
            "value": value,
        }
        expected = {
            "divination/zengshan-buyi#ZR-F01": {
                "role": "casting_rule",
                "predicates": [
                    {"path_suffix": "/output/primary_hexagram/name", "operator": "eq", "value": "兑为泽"},
                    {"path_suffix": "/output/changed_hexagram/name", "operator": "eq", "value": "天水讼"},
                    {"path_suffix": "/output/moving_lines/0", "operator": "eq", "value": 1},
                    {"path_suffix": "/output/moving_lines/1", "operator": "eq", "value": 6},
                ],
                "sources": [source("divination/zengshan-buyi", "40cb50a05cbcb03ce3d42f2cc3de5daf1db6cf78e8dbae4c4b9b1e42dd6f50e0", 266, "如亥月己丑日占將來有官否。得兌化訟卦")],
            },
            "divination/bushi-zhengzong#BSZZ-M01": {
                "role": "casting_rule",
                "predicates": [nonempty("/output/casting/tosses"), nonempty("/output/moving_lines")],
                "sources": [source("divination/bushi-zhengzong", "651efe70d1bce36d1a18e9bf680a912ae3f556f2e66b16c137cd6efbfc9cb491", 138, "自下装上，三掷内卦成")],
            },
            "divination/huangjin-ce#HJC-M001": {
                "role": "methodology_rule",
                "predicates": [nonempty("/output/moving_lines"), nonempty("/output/changed_hexagram")],
                "sources": [source("divination/huangjin-ce", "6a8569490397634b15c821116ebe21d9eff799c3b8c07c51179c4224a3362e77", 30, "動為始，變為終")],
            },
            "divination/huozhu-lin#HZL-M001": {
                "role": "methodology_rule",
                "predicates": [nonempty("/output/shi_ying")],
                "sources": [source("divination/huozhu-lin", "6239f9ef22be7deb5771b513dacfc9cc1e8eea8cc5e54164f971cd7de86e5293", 55, "先看世应，后审浅深。")],
            },
            "divination/meihua-yishu#MR-01-01": {
                "role": "methodology_rule",
                "predicates": [nonempty("/output/totals")],
                "sources": [source("divination/meihua-yishu", "6fa4f590c86623eda1d0109200100c25408d101e557e98f76fc9db35699b9b59", 63, "乾，一；兌，二；離，三；震，四；巽，五；坎，六；艮，七；坤，八。")],
            },
            "divination/zhouyi-zhezhong#ZZR-M001": {
                "role": "methodology_rule",
                "predicates": [nonempty("/output/primary_hexagram")],
                "sources": [source("divination/zhouyi-zhezhong", "3b3dd34ee83c8b021ba63372d3cb1a5ade4b50747fa6ac72a8b9b2b08ef28cea", 334, "故因其八卦而更重之卦有六爻遂重為六十四卦也")],
            },
            "divination/huangji-jingshi#HR-04-01": {
                "role": "methodology_rule",
                "predicates": [nonempty("/output/upper_trigram/name"), nonempty("/output/lower_trigram/name")],
                "sources": [source("divination/huangji-jingshi", "bdc5c42a08d2b9591f1b4ccd457f709c9e9c6e8376e02fa6499478a7686683bc", 36891, "順數之乾一兊二離三震四巽五坎六艮七坤八")],
            },
            "selection/xingli-kaoyuan#KR-05": {
                "role": "methodology_rule",
                "predicates": [nonempty(f"/calendar/ganzhi/{key}") for key in ("year", "month", "day", "hour")],
                "sources": [
                    source("selection/xingli-kaoyuan", "419ee9d7fe62e6e9bf597d1325ae7476a952c14bcefe967cc1d622bf5e04f9ff", 270, "甲巳之年丙作首乙庚之嵗戊為頭丙辛更向庚寅起丁壬壬位順行流戊癸年從何處起甲寅之上好推求"),
                    source("selection/xingli-kaoyuan", "419ee9d7fe62e6e9bf597d1325ae7476a952c14bcefe967cc1d622bf5e04f9ff", 275, "甲巳還加甲乙庚丙作初丙辛從戊起丁壬庚子居戊癸尋壬子時元定不虚"),
                ],
            },
            "ziwei/taiwei-fu#TR-01": {
                "role": "methodology_rule",
                "predicates": [descendant("/output/palaces", "命宫")],
                "sources": [source("ziwei/taiwei-fu", "2f77ec8c47122cf18308e9c3fc06274df65695861526e4d1896e4fc59ce262c9", 5, "斗數至玄至微，理旨難明，雖設問於百篇之中，猶有言而未盡，至如星之分野，各有所屬，壽夭賢愚，富貴貧賤，不可一概論議。")],
            },
            "ziwei/ziwei-doushu-quanshu#ZW-M01": {
                "role": "methodology_rule",
                "predicates": [descendant("/output/palaces", "命宫"), descendant("/output/palaces", "父母")],
                "sources": [source("ziwei/ziwei-doushu-quanshu", "75679206451ebfad7d7124168316ffaf72a516de9c149e4bef001dd3f3b7283d", 963, "一 命宫、二兄弟、三妻妾、四子女、五财帛、六疾厄、七迁移、八奴仆、九官禄、十田宅、十一福德、十二父母")],
            },
            "bazi/qiongtong-baojian#QTB-M01": {
                "role": "methodology_rule",
                "predicates": [nonempty("/day_master/stem"), nonempty("/month_command/branch")],
                "sources": [source("bazi/qiongtong-baojian", "fce5e9215be146435c533b15647849c03321577128e6fb7ac19258dc8b55cbaf", 9, "土无常性，视四时所乘，欲使相济得所，勿令太过弗及。")],
            },
        }
        records = {
            record["rule_id"]: record
            for record in build_evidence_index.compile_evidence_rules(
                root=ROOT, enforce_classical_bindings=False
            )
        }
        payload = generate_classical_evidence_bindings.load_committed()

        for rule_id, contract in expected.items():
            with self.subTest(rule_id=rule_id):
                self.assertIn(rule_id, records)
                self.assertEqual(records[rule_id]["evidence_role"], contract["role"])
                self.assertEqual(records[rule_id]["required_fact_predicates"], contract["predicates"])
                binding = payload["bindings"][rule_id]
                self.assertEqual(binding["verification_status"], "verified")
                self.assertEqual(binding["mechanical_location_status"], "verified_exact")
                self.assertEqual(binding["classical_sources"], contract["sources"])
        self.assertEqual(
            payload["bindings"]["bazi/qiongtong-baojian#QR-03-02"][
                "verification_status"
            ],
            "inactive_unverified",
        )

    def test_classical_rule_digest_binds_the_evidence_role(self) -> None:
        records = build_evidence_index.compile_evidence_rules(
            root=ROOT, enforce_classical_bindings=False
        )
        record = next(
            item
            for item in records
            if item["rule_id"] == "bazi/sanming-tonghui#R-01-02"
        )
        original_digest = build_evidence_index.canonical_rule_record_digest(record)
        record["evidence_role"] = (
            "methodology_rule"
            if record["evidence_role"] != "methodology_rule"
            else "issue_specific_judgment_rule"
        )
        self.assertNotEqual(
            original_digest,
            build_evidence_index.canonical_rule_record_digest(record),
        )
        with self.assertRaisesRegex(ValueError, "rule record digest mismatch"):
            build_evidence_index._apply_classical_evidence_bindings(
                records, root=ROOT
            )

    def test_group_a_mandatory_packs_have_exact_verified_methodology_bindings(self) -> None:
        expected = {
            "bazi/sanming-tonghui#R-01-02",
            "bazi/yuanhai-ziping#YR-M01",
            "bazi/ziping-zhenquan#ZPR-01",
            "bazi/ditiansui-chanwei#DR-01-01",
            "luming-nayin/luoluzi-sanming#LZ-01-01",
            "luming-nayin/wuxing-jingji#WX-01-01",
            "luming-nayin/lantai-miaoxuan#LT-M01",
            "xingming/xingming-suyuan#XR-M01",
            "xingming/xingxue-dacheng#XXDC-M01",
            "xingming/guotian-jing#GR-01-01",
        }
        records = {
            record["rule_id"]: record
            for record in build_evidence_index.compile_evidence_rules(
                root=ROOT,
                enforce_classical_bindings=False,
            )
        }
        payload = generate_classical_evidence_bindings.load_committed()
        exact_predicates = {
            "bazi/yuanhai-ziping#YR-M01": [
                {"path_suffix": "/calendar_normalization/ganzhi", "operator": "nonempty"},
                {"path_suffix": "/day_master/stem", "operator": "nonempty"},
                {"path_suffix": "/month_command/branch", "operator": "nonempty"},
            ],
            "bazi/sanming-tonghui#R-01-02": [
                {"path_suffix": "/output/day_master/element", "operator": "nonempty"},
            ],
            "bazi/ziping-zhenquan#ZPR-01": [
                {"path_suffix": "/output/day_master/stem", "operator": "nonempty"},
                {"path_suffix": "/output/month_command/branch", "operator": "nonempty"},
            ],
            "bazi/ditiansui-chanwei#DR-01-01": [
                {"path_suffix": "/four_pillars", "operator": "nonempty"},
                {"path_suffix": "/hidden_stems", "operator": "nonempty"},
            ],
            "luming-nayin/luoluzi-sanming#LZ-01-01": [
                {"path_suffix": "/output/pillars", "operator": "nonempty"},
                {"path_suffix": "/output/three_yuan_profiles/luoluzi", "operator": "nonempty"},
            ],
            "luming-nayin/wuxing-jingji#WX-01-01": [
                {"path_suffix": "/output/pillars", "operator": "nonempty"},
                {"path_suffix": "/output/nayin", "operator": "nonempty"},
            ],
            "luming-nayin/lantai-miaoxuan#LT-M01": [
                {"path_suffix": "/output/three_yuan_profiles", "operator": "nonempty"},
                {"path_suffix": "/output/pillars", "operator": "nonempty"},
            ],
            "xingming/xingming-suyuan#XR-M01": [
                {"path_suffix": "/output/ming_shen", "operator": "nonempty"},
            ],
            "xingming/xingxue-dacheng#XXDC-M01": [
                {"path_suffix": f"/output/houses/{index}/name", "operator": "eq", "value": name}
                for index, name in enumerate((
                    "命宫", "财帛", "兄弟", "田宅", "男女", "奴仆",
                    "妻妾", "疾厄", "迁移", "官禄", "福德", "相貌",
                ))
            ],
            "xingming/guotian-jing#GR-01-01": [
                {"path_suffix": f"/calendar_normalization/ganzhi/{key}", "operator": "nonempty"}
                for key in ("year", "month", "day", "hour")
            ],
        }

        self.assertEqual(expected - records.keys(), set())
        for rule_id in sorted(expected):
            with self.subTest(rule_id=rule_id):
                record = records[rule_id]
                binding = payload["bindings"][rule_id]
                self.assertEqual(record["evidence_role"], "methodology_rule")
                self.assertTrue(record["required_fact_predicates"])
                if rule_id in exact_predicates:
                    self.assertEqual(
                        record["required_fact_predicates"], exact_predicates[rule_id]
                    )
                self.assertEqual(binding["verification_status"], "verified")
                self.assertEqual(
                    binding["mechanical_location_status"], "verified_exact"
                )
                self.assertTrue(binding["classical_sources"])
        xr_source = payload["bindings"]["xingming/xingming-suyuan#XR-M01"][
            "classical_sources"
        ][0]
        self.assertEqual(xr_source["anchor"], "fulltext.md#L67")
        self.assertEqual(xr_source["verbatim_quote"], "次察身宫")

    def test_compiler_never_emits_duplicate_applicability_predicates(self) -> None:
        records = build_evidence_index.compile_evidence_rules(
            root=ROOT,
            enforce_classical_bindings=False,
        )
        for record in records:
            predicates = record["required_fact_predicates"]
            canonical = [
                json.dumps(item, ensure_ascii=False, sort_keys=True)
                for item in predicates
            ]
            self.assertEqual(
                len(canonical),
                len(set(canonical)),
                record["rule_id"],
            )

    def test_scope_binding_can_only_override_a_known_evidence_role(self) -> None:
        base = {
            "schema_version": "mingli-evidence-scope-bindings-v1",
            "bindings": {
                "ziwei/taiwei-fu#TR-01": {
                    "route": "ziwei",
                    "rationale": "古文只证明读盘方法，不授权具体结果判断。",
                    "evidence_role": "methodology_rule",
                    "predicates": [
                        {
                            "path_suffix": "/palaces",
                            "operator": "descendant_eq",
                            "value": "命宫",
                        }
                    ],
                }
            },
            "series": [],
        }

        normalized = build_evidence_index.validate_evidence_scope_bindings(base)
        self.assertEqual(
            normalized["ziwei/taiwei-fu#TR-01"]["evidence_role"],
            "methodology_rule",
        )
        invalid = copy.deepcopy(base)
        invalid["bindings"]["ziwei/taiwei-fu#TR-01"]["evidence_role"] = (
            "invented_authority"
        )
        with self.assertRaisesRegex(ValueError, "evidence role"):
            build_evidence_index.validate_evidence_scope_bindings(invalid)

    def test_manifest_is_pinned_and_covers_every_predicate_bound_record(self) -> None:
        payload = build_evidence_index.load_classical_evidence_bindings(root=ROOT)
        rows = [
            json.loads(line)
            for line in INDEX.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        bound = {row["rule_id"] for row in rows if row["required_fact_predicates"]}

        self.assertEqual(set(payload["bindings"]), bound)
        self.assertEqual(
            generate_classical_evidence_bindings.SEMANTICALLY_VERIFIED_RULE_IDS
            - bound,
            set(),
        )
        statuses = {
            rule_id: binding["semantic_verification_status"]
            for rule_id, binding in payload["bindings"].items()
        }
        # Exact location is not semantic authorization. Only independently
        # audited source, role, and applicability contracts become active.
        self.assertEqual(sum(value == "verified" for value in statuses.values()), 192)
        self.assertEqual(
            sum(value == "verified" for value in statuses.values())
            + sum(value == "inactive_unverified" for value in statuses.values()),
            586,
        )
        self.assertEqual(
            sum(
                binding["mechanical_location_status"] == "verified_exact"
                for binding in payload["bindings"].values()
            ),
            391,
        )

    def test_compiler_binds_predicates_and_rule_summary_separately_from_quote(self) -> None:
        records = build_evidence_index.compile_evidence_rules(root=ROOT)
        verified = next(record for record in records if record["runtime_active"])
        inactive = next(
            record
            for record in records
            if record["required_fact_predicates"] and not record["runtime_active"]
        )

        self.assertEqual(
            verified["applicability_signature"],
            build_evidence_index.canonical_predicate_signature(
                verified["required_fact_predicates"],
                verified["excluded_fact_predicates"],
            ),
        )
        self.assertEqual(
            verified["rule_record_digest"],
            build_evidence_index.canonical_rule_record_digest(verified),
        )
        self.assertEqual(verified["classical_binding_status"], "verified")
        self.assertTrue(verified["classical_sources"])
        self.assertEqual(inactive["classical_binding_status"], "inactive_unverified")
        self.assertFalse(inactive["runtime_active"])

    def test_runtime_never_matches_an_inactive_predicate_bearing_record(self) -> None:
        rule = next(
            rule
            for rule in load_evidence_rules(INDEX, root=ROOT)
            if rule.required_fact_predicates and not rule.runtime_active
        )
        predicate = rule.required_fact_predicates[0]
        value = predicate.value
        if predicate.operator == "in":
            value = predicate.values[0]
        fact = FactRef(
            fact_id="f" * 64,
            path=f"/test{predicate.path_suffix}",
            value=value,
            provider_id="test",
            provider_version="1",
            reading_id="r" * 32,
            version=1,
        )

        self.assertEqual(match_rule(rule, (fact,)), (False, (), ()))

    def _semantic_manifest_mutation(self, mutation, message: str) -> None:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        mutation(payload)
        rendered = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ) + "\n"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_text(rendered, encoding="utf-8")
            expected = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
            with self.assertRaisesRegex(ValueError, message):
                build_evidence_index.load_classical_evidence_bindings(
                    root=ROOT,
                    manifest_path=path,
                    expected_sha256=expected,
                )

    def test_manifest_pin_rejects_even_a_well_formed_rewrite(self) -> None:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        payload["audit_note"] = "rewritten"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest hash"):
                build_evidence_index.load_classical_evidence_bindings(
                    root=ROOT, manifest_path=path
                )

    def test_manifest_rejects_path_traversal_and_bad_hash_anchor_or_quote(self) -> None:
        def verified(payload):
            return next(
                binding
                for binding in payload["bindings"].values()
                if binding["verification_status"] == "verified"
            )

        cases = (
            (
                lambda p: verified(p)["classical_sources"][0].__setitem__(
                    "path", "../escape.md"
                ),
                "path",
            ),
            (
                lambda p: verified(p)["classical_sources"][0].__setitem__(
                    "sha256", "0" * 64
                ),
                "source hash",
            ),
            (
                lambda p: verified(p)["classical_sources"][0].__setitem__(
                    "anchor", "fulltext.md#L0"
                ),
                "anchor",
            ),
            (
                lambda p: verified(p)["classical_sources"][0].__setitem__(
                    "verbatim_quote", "invented"
                ),
                "quote",
            ),
        )
        for mutation, message in cases:
            with self.subTest(message=message):
                self._semantic_manifest_mutation(mutation, message)

    def test_manifest_rejects_cross_rule_binding_or_predicate_swap(self) -> None:
        def swap_sources(payload):
            verified = [
                item
                for item in payload["bindings"].values()
                if item["verification_status"] == "verified"
            ]
            verified[0]["classical_sources"], verified[1]["classical_sources"] = (
                verified[1]["classical_sources"], verified[0]["classical_sources"]
            )

        def swap_predicates(payload):
            verified = [
                item
                for item in payload["bindings"].values()
                if item["verification_status"] == "verified"
            ]
            verified[0]["applicability_signature"], verified[1]["applicability_signature"] = (
                verified[1]["applicability_signature"],
                verified[0]["applicability_signature"],
            )

        self._semantic_manifest_mutation(
            swap_sources,
            "binding digest|rule binding|source hash/pack",
        )
        self._semantic_manifest_mutation(swap_predicates, "binding digest|predicate")


if __name__ == "__main__":
    unittest.main()
