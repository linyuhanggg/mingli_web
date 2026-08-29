#!/usr/bin/env python3
"""Generate only deterministic, exact classical evidence bindings.

This intentionally has no similarity/fuzzy fallback.  A predicate-bearing
record that does not satisfy one of the source-audited rules below is emitted
as ``inactive_unverified`` instead of being guessed into the runtime corpus.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

import build_evidence_index as compiler
from simplified_canonical import canonicalize


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = Path(
    os.environ.get("MINGLI_RESEARCH_ROOT", ROOT / "__missing_external_research__")
).resolve()
OUTPUT = ROOT / "references/matrices/classical-evidence-bindings-v1.json"
LINE_RE = re.compile(r"L([1-9][0-9]*)(?:-L?([1-9][0-9]*))?")
QUOTE_ID_RE = re.compile(r"\b(?:DLQ-[0-9]{3}|(?:LZ|LM)-Q[0-9]{3})\b")
QIONGTONG_RUNTIME_VERIFIED_LOCAL_IDS = {
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
SEMANTICALLY_VERIFIED_RULE_IDS = {
    "bazi/sanming-tonghui#R-01-02",
    "bazi/sanming-tonghui#R-02-04",
    "bazi/yuanhai-ziping#YR-M01",
    "bazi/ziping-zhenquan#ZPR-01",
    "bazi/ditiansui-chanwei#DR-01-01",
    "luming-nayin/luoluzi-sanming#LZ-01-01",
    "luming-nayin/wuxing-jingji#WX-01-01",
    "luming-nayin/lantai-miaoxuan#LT-M01",
    "xingming/xingming-suyuan#XR-M01",
    "xingming/xingxue-dacheng#XXDC-M01",
    "xingming/guotian-jing#GR-01-01",
    "divination/zengshan-buyi#ZR-F01",
    "divination/bushi-zhengzong#BSZZ-M01",
    "divination/huangjin-ce#HJC-M001",
    "divination/huangjin-ce#HJC-R009",
    "divination/huozhu-lin#HZL-M001",
    "divination/meihua-yishu#MR-01-01",
    "divination/meihua-yishu#MR-04-01",
    "divination/meihua-yishu#MR-04-02",
    "divination/meihua-yishu#MR-04-04",
    "divination/zhouyi-zhezhong#ZZR-M001",
    "divination/huangji-jingshi#HR-04-01",
    "divination/zengshan-buyi#ZR-04-04",
    "divination/zengshan-buyi#ZR-05-05",
    "selection/xingli-kaoyuan#KR-05",
    "ziwei/taiwei-fu#TR-01",
    "ziwei/ziwei-doushu-quanshu#ZW-M01",
    "bazi/qiongtong-baojian#QTB-M01",
    *{
        f"bazi/qiongtong-baojian#{local_id}"
        for local_id in QIONGTONG_RUNTIME_VERIFIED_LOCAL_IDS
    },
    "fengshui/zangshu#R-02",
    "fengshui/xuexin-fu#XXF-R01",
    "fengshui/yangzhai-sanyao#YZS-R005",
    "fengshui/yangzhai-shishu#YZS-R003",
    "fengshui/yangzhai-shishu#YZS-R014",
    "fengshui/hanlong-jing#R-01",
    "fengshui/huangdi-zhaijing#HDZJ-R006",
    "fengshui/yilong-jing#R-05",
    "physiognomy/liuzhuang-xiangfa#LZ-R01",
    "physiognomy/mayi-shenxiang#MR-02",
    "physiognomy/shenxiang-quanbian#SR-02-04",
    *{
        f"luming-nayin/li-xuzhong-mingshu#LX-01-{number:02d}"
        for number in range(1, 61)
        if number not in {1, 11, 36, 56}
    },
    *{
        f"san-shi/daliuren-daquan#DLR-{number:02d}"
        for number in (*range(2, 11), 17)
    },
    "san-shi/liuren-miben#LM-R01",
    "san-shi/liuren-miben#LM-R20",
    "san-shi/liuren-miben#LM-R21",
    *{
        f"san-shi/liuren-zhiyin#LR-{number:02d}"
        for number in (*range(2, 9), 17, 18, 19)
    },
    *{
        f"san-shi/qimen-dunjia-tongzhi#QM-P{number:02d}"
        for number in range(1, 41)
        if number not in {26, 36}
    },
    "san-shi/qimen-faqiao#QM-P26",
    "san-shi/qimen-faqiao#QM-P36",
    *{
        f"san-shi/taiyi-shenshu#TR-{number:02d}"
        for number in (1, 3, 4, 5, 10)
    },
    *{
        f"san-shi/taiyi-shenshu#TY-P{number:02d}"
        for number in range(1, 11)
    },
    "selection/xieji-bianfang-shu#XR-18",
}

QIONGTONG_FULLTEXT = "references/fulltext/bazi/qiongtong-baojian/fulltext.md"
QIONGTONG_FULLTEXT_SHA256 = (
    "fce5e9215be146435c533b15647849c03321577128e6fb7ac19258dc8b55cbaf"
)


def load_committed() -> dict[str, Any]:
    """Load the portable, hash-bound binding snapshot without research files."""

    return compiler.load_classical_evidence_bindings(root=ROOT)


def _qiongtong_sources(*items: tuple[int, str]) -> tuple[tuple[str, str, int, str], ...]:
    return tuple(
        (QIONGTONG_FULLTEXT, QIONGTONG_FULLTEXT_SHA256, line, quote)
        for line, quote in items
    )


AUDITED_QIONGTONG_CHAPTER_SOURCES = {
    "bazi/qiongtong-baojian#QR-01-01": _qiongtong_sources(
        (43, "正月甲木，初春尚有余寒，得丙癸逢"),
        (55, "二月甲木，庚金得所"),
        (57, "三月甲木，木气相竭。先取庚金，次用壬水"),
    ),
    "bazi/qiongtong-baojian#QR-01-02": _qiongtong_sources(
        (73, "四月甲木退气，丙火司权，先癸后丁"),
        (81, "五月先癸后丁庚金次之。六月三伏生寒，丁火退气。先丁后庚，无癸亦可"),
    ),
    "bazi/qiongtong-baojian#QR-01-03": _qiongtong_sources(
        (115, "七月甲木，丁火为尊，庚金次之"),
        (117, "八月甲木，木囚金旺。丁火为先，次用丙火，庚金再次"),
        (131, "九月甲木，木星凋零，独爱丁火，壬癸滋扶"),
    ),
    "bazi/qiongtong-baojian#QR-01-05": _qiongtong_sources(
        (181, "正月乙木，必须用丙，因天气尤有余寒，非丙不暖，虽有癸水，恐凝寒气，故以丙火为先，癸水次之"),
        (187, "二月乙木，阳气渐升，木不寒矣，以丙为君，癸为臣"),
        (197, "三月乙木，阳气愈炽，先癸后丙"),
    ),
    "bazi/qiongtong-baojian#QR-01-07": _qiongtong_sources(
        (247, "三秋乙木，金神司令，先丙后癸，惟九月耑用癸水"),
    ),
    "bazi/qiongtong-baojian#QR-02-01": _qiongtong_sources(
        (319, "正月用壬，庚辛为助。二月耑用壬水。三月土重晦光，取甲佐之为妙"),
    ),
    "bazi/qiongtong-baojian#QR-02-02": _qiongtong_sources(
        (388, "四月耑用壬水，金为佐。五月亦耑用壬。四五月壬透者富贵。丁多、兼看癸水。六月用壬，但借庚金为佐"),
    ),
    "bazi/qiongtong-baojian#QR-02-04": _qiongtong_sources(
        (507, "十月丙火，木旺宜庚，水旺宜戊，火旺用壬，随宜酌用可也"),
        (518, "十一月丙火，冬至一阳生，弱中复强，壬水为最，戊土佐之"),
        (537, "十二月丙火，气进二阳，侮雪欺霜，喜壬为用。己土司令，土多又不可少甲"),
    ),
    "bazi/qiongtong-baojian#QR-03-01": _qiongtong_sources(
        (769, "正二月先丙后甲，癸又次之。三月先甲后丙，癸又次之"),
    ),
    "bazi/qiongtong-baojian#QR-03-04": _qiongtong_sources(
        (897, "十月戊土，时值小阳，阳气略出，先用甲木，次取丙火"),
        (912, "十一二月严寒冰冻，丙火为专，甲木为佐"),
    ),
    "bazi/qiongtong-baojian#QR-03-06": _qiongtong_sources(
        (981, "三夏己土，杂气才官，禾稼在田，最喜甘沛，取癸为要，次用丙火"),
    ),
    "bazi/qiongtong-baojian#QR-03-07": _qiongtong_sources(
        (1006, "三秋己土，万物收藏之际，外虚内实，寒气渐升，须丙火温之，癸水润之"),
        (1018, "九月土盛，宜甲木疏之"),
    ),
    "bazi/qiongtong-baojian#QR-04-01": _qiongtong_sources(
        (1084, "正月庚金，丙甲为上，丁火次之"),
        (1093, "二月庚金，专用丁火，借甲引丁，借庚噼甲"),
        (1116, "三月庚金，戊土司令，无生金之理，有埋金之忧，故先甲后丁"),
    ),
    "bazi/qiongtong-baojian#QR-04-02": _qiongtong_sources(
        (1143, "四月庚金，须用壬丙戊"),
        (1147, "五月庚金，丁火旺烈，庚金败地，专用壬水，癸又次之"),
        (1153, "六月庚金，三伏生寒，顽钝极矣，先用丁火，次取甲木"),
    ),
    "bazi/qiongtong-baojian#QR-04-07": _qiongtong_sources(
        (1352, "七月辛金，壬不在多，故书云：水浅金多，号曰体全之象，壬水为尊，甲戊酌用可也"),
        (1359, "八月辛金，当权得令，旺之极矣，专用壬水淘洗火"),
        (1384, "九月辛金，戊土司令，母旺子相，须甲疏土，壬洩旺金，先壬后甲"),
    ),
    "bazi/qiongtong-baojian#QR-05-02": _qiongtong_sources(
        (1496, "四月壬水，丙火司权，水弱极矣，专取壬水比肩为助，次取辛金发源，且暗合丙火，庚金为佐"),
        (1515, "五月壬水，丁旺壬弱，取癸为用，取庚为佐"),
        (1528, "六月壬水，先辛后甲，次取癸水"),
    ),
    "bazi/qiongtong-baojian#QR-05-04": _qiongtong_sources(
        (1591, "十月壬水、专用戊丙，次取庚金"),
        (1600, "十一月壬水，阳刃帮身，较前更旺，先取戊土，次用丙火"),
        (1617, "十二月壬水，旺极复衰，何也？上半月癸辛主事，故旺，专用丙火。下半月己土主事，故衰。亦用丙火，甲木佐之"),
    ),
    "bazi/qiongtong-baojian#QR-05-08": _qiongtong_sources(
        (1731, "十月癸水，旺中有弱，何也？因亥摇木，洩散元神，宜用庚辛为妙"),
        (1744, "十一月癸水，值冰冻之时，金水无交欢之象，专用丙火解冻，庶不致成冰，又要辛金滋扶"),
        (1754, "十二月癸水，寒极成冰，万物不能舒泰，宜丙火解冻"),
    ),
}

AUDITED_METHODOLOGY_SOURCES = {
    "bazi/sanming-tonghui#R-01-02": (
        "references/fulltext/bazi/sanming-tonghui/fulltext.md",
        "0f78de8e47b7cd1dc199d6488c5fdf40d01819e589b0f50e78273541e8c14ed7",
        34,
        "故五者流行而更轉順則相生逆則相尅",
    ),
    "bazi/yuanhai-ziping#YR-M01": (
        "references/fulltext/bazi/yuanhai-ziping/fulltext.md",
        "a09dc8706d654ddfcb8b88843dde9fc01e792487b066c3faa9232c5df3e4918a",
        109,
        "以日为主，年为本，月为提纲，时为辅佐。",
    ),
    "bazi/ziping-zhenquan#ZPR-01": (
        "references/fulltext/bazi/ziping-zhenquan/fulltext.md",
        "a00b705357cca35178e6062eced8eb0622274751ff4fc4aaa424a655bfffe4d7",
        179,
        "八字用神，專求月令，以日干配月令地支，而生尅不同，格局分焉。",
    ),
    "bazi/ditiansui-chanwei#DR-01-01": (
        "references/fulltext/bazi/ditiansui-chanwei/fulltext.md",
        "8e27b47b0155cbe4a4ce4e7d250435e786f203f2caf81f95440526eecf0d17db",
        11,
        "干为天元，支为地元，支中所藏为人元。",
    ),
    "luming-nayin/luoluzi-sanming#LZ-01-01": (
        "references/fulltext/luming-nayin/luoluzi-sanming/fulltext.md",
        "05d42aa624f9287dd131e9202da40d3db3f0ed9200f1a089c711e97be4d96c28",
        9,
        "以四柱論之，本命生月生日生時四柱也。每一宮有三元，有天元、人元、支元。",
    ),
    "luming-nayin/wuxing-jingji#WX-01-01": (
        "references/fulltext/luming-nayin/wuxing-jingji/fulltext.md",
        "32e0581bcba3b1b6df2b8e0c48db135a4a6f27e7dca2f010e0a818ab6ba9e08b",
        251,
        "天氣始於甲，地氣始於子，子甲相合，命曰歲，以十乾配十二支，周而復始，則六甲成矣。",
    ),
    "luming-nayin/lantai-miaoxuan#LT-M01": (
        "references/fulltext/luming-nayin/lantai-miaoxuan/fulltext.md",
        "ae30d81ed02dc99dd227f2ca7b0e6daf34bea9776c8a531f042b8e59bd80346e",
        18,
        "（天元、地元、人元謂之三命。）",
    ),
    "xingming/xingming-suyuan#XR-M01": (
        "references/fulltext/xingming/xingming-suyuan/fulltext.md",
        "93581f38e1ffa36f9b33e695d4ec3441da57cad4a3f20e6b1c29b77207394f5a",
        67,
        "次察身宫",
    ),
    "xingming/xingxue-dacheng#XXDC-M01": (
        "references/fulltext/xingming/xingxue-dacheng/fulltext.md",
        "099ddc76d4143ad5e41601337c0ecb777b77adaf67737067339b9814784cb980",
        921,
        "以宫分言則一命宫二財帛三兄弟四田宅五男女六奴僕七妻妾八疾厄九遷移十官禄十一福徳十二相貌",
    ),
    "divination/zengshan-buyi#ZR-F01": (
        "references/fulltext/divination/zengshan-buyi/fulltext.md",
        "40cb50a05cbcb03ce3d42f2cc3de5daf1db6cf78e8dbae4c4b9b1e42dd6f50e0",
        266,
        "如亥月己丑日占將來有官否。得兌化訟卦",
    ),
    "divination/bushi-zhengzong#BSZZ-M01": (
        "references/fulltext/divination/bushi-zhengzong/fulltext.md",
        "651efe70d1bce36d1a18e9bf680a912ae3f556f2e66b16c137cd6efbfc9cb491",
        138,
        "自下装上，三掷内卦成",
    ),
    "divination/huangjin-ce#HJC-M001": (
        "references/fulltext/divination/huangjin-ce/fulltext.md",
        "6a8569490397634b15c821116ebe21d9eff799c3b8c07c51179c4224a3362e77",
        30,
        "動為始，變為終",
    ),
    "divination/huozhu-lin#HZL-M001": (
        "references/fulltext/divination/huozhu-lin/fulltext.md",
        "6239f9ef22be7deb5771b513dacfc9cc1e8eea8cc5e54164f971cd7de86e5293",
        55,
        "先看世应，后审浅深。",
    ),
    "divination/meihua-yishu#MR-01-01": (
        "references/fulltext/divination/meihua-yishu/fulltext.md",
        "6fa4f590c86623eda1d0109200100c25408d101e557e98f76fc9db35699b9b59",
        63,
        "乾，一；兌，二；離，三；震，四；巽，五；坎，六；艮，七；坤，八。",
    ),
    "divination/zhouyi-zhezhong#ZZR-M001": (
        "references/fulltext/divination/zhouyi-zhezhong/fulltext.md",
        "3b3dd34ee83c8b021ba63372d3cb1a5ade4b50747fa6ac72a8b9b2b08ef28cea",
        334,
        "故因其八卦而更重之卦有六爻遂重為六十四卦也",
    ),
    "divination/huangji-jingshi#HR-04-01": (
        "references/fulltext/divination/huangji-jingshi/fulltext.md",
        "bdc5c42a08d2b9591f1b4ccd457f709c9e9c6e8376e02fa6499478a7686683bc",
        36891,
        "順數之乾一兊二離三震四巽五坎六艮七坤八",
    ),
    "selection/xingli-kaoyuan#KR-05": (
        (
            "references/fulltext/selection/xingli-kaoyuan/fulltext.md",
            "419ee9d7fe62e6e9bf597d1325ae7476a952c14bcefe967cc1d622bf5e04f9ff",
            270,
            "甲巳之年丙作首乙庚之嵗戊為頭丙辛更向庚寅起丁壬壬位順行流戊癸年從何處起甲寅之上好推求",
        ),
        (
            "references/fulltext/selection/xingli-kaoyuan/fulltext.md",
            "419ee9d7fe62e6e9bf597d1325ae7476a952c14bcefe967cc1d622bf5e04f9ff",
            275,
            "甲巳還加甲乙庚丙作初丙辛從戊起丁壬庚子居戊癸尋壬子時元定不虚",
        ),
    ),
    "ziwei/taiwei-fu#TR-01": (
        "references/fulltext/ziwei/taiwei-fu/fulltext.md",
        "2f77ec8c47122cf18308e9c3fc06274df65695861526e4d1896e4fc59ce262c9",
        5,
        "斗數至玄至微，理旨難明，雖設問於百篇之中，猶有言而未盡，至如星之分野，各有所屬，壽夭賢愚，富貴貧賤，不可一概論議。",
    ),
    "ziwei/ziwei-doushu-quanshu#ZW-M01": (
        "references/fulltext/ziwei/ziwei-doushu-quanshu/fulltext.md",
        "75679206451ebfad7d7124168316ffaf72a516de9c149e4bef001dd3f3b7283d",
        963,
        "一 命宫、二兄弟、三妻妾、四子女、五财帛、六疾厄、七迁移、八奴仆、九官禄、十田宅、十一福德、十二父母",
    ),
    "bazi/qiongtong-baojian#QTB-M01": (
        "references/fulltext/bazi/qiongtong-baojian/fulltext.md",
        "fce5e9215be146435c533b15647849c03321577128e6fb7ac19258dc8b55cbaf",
        9,
        "土无常性，视四时所乘，欲使相济得所，勿令太过弗及。",
    ),
    "fengshui/zangshu#R-02": (
        "references/fulltext/fengshui/zangshu/fulltext.md",
        "5d38da6ceee94042299ceaae7136a39cb915297bb1dcf7f98f2eac4bd1a7e0af",
        27,
        "氣乘風則散，界水則止",
    ),
    "fengshui/xuexin-fu#XXF-R01": (
        "references/fulltext/fengshui/xuexin-fu/fulltext.md",
        "5e27d9aaf634f59e97cc1afb39382ae328425c437041eeb31447b6ba2c8cef83",
        25,
        "入山尋水口，登穴看明堂",
    ),
    "fengshui/hanlong-jing#R-01": (
        "references/fulltext/fengshui/hanlong-jing/fulltext.md",
        "d988005dfb7f7de267f19f550472af7eff79c16b18132ff082ebad8836709fe4",
        11,
        "髙山須認星峯起平地龍行别有名",
    ),
    "fengshui/yilong-jing#R-05": (
        "references/fulltext/fengshui/yilong-jing/fulltext.md",
        "b1bb72819575888442a7d49607b2e49754bcd2821ca355480b531b0ee3ebbff3",
        20,
        "明堂惜水如惜血，穴裏避風如避賊",
    ),
    "physiognomy/liuzhuang-xiangfa#LZ-R01": (
        "references/fulltext/physiognomy/liuzhuang-xiangfa/fulltext.md",
        "04459fbe4f5d48e0810a8f0290c6f8f851754db02a2344fc109380aee6059af8",
        26,
        "不可以一美而言善，不可以一恶而言凶。相有乘除加减之法也。",
    ),
}

AUDITED_RANGE_QUOTE_SOURCES = {
    "bazi/sanming-tonghui#R-02-04": (
        (
            "references/fulltext/bazi/sanming-tonghui/fulltext.md",
            "0f78de8e47b7cd1dc199d6488c5fdf40d01819e589b0f50e78273541e8c14ed7",
            636,
            636,
            "盛徳乘時曰旺如春木旺旺則生火火乃木之子子乗父業故火相木用水生生我者父母今子嗣得時登髙明顯赫之地而生我者當知退矣故水休休者羙之無極休然無事之義火能尅金金乃木之鬼被火尅制不能施設故金囚火能生土土為木之財財為隠藏之物草木發生土散氣塵所以春木尅土則死夏火旺火生土則土相木生火則木休水尅火則水因火尅金則金死六月土旺土生金則金相火生土則火休木尅土則木囚土尅水則水死秋金旺金生水則水相土生金則土休火尅金則火囚金尅木則木死冬水旺水生木則木相金生水則金休土尅水則土囚水尅火則火死",
        ),
    ),
    "divination/huangjin-ce#HJC-R009": (
        (
            "references/fulltext/divination/huangjin-ce/fulltext.md",
            "6a8569490397634b15c821116ebe21d9eff799c3b8c07c51179c4224a3362e77",
            962,
            964,
            None,
        ),
    ),
    "divination/meihua-yishu#MR-04-01": (
        (
            "references/fulltext/divination/meihua-yishu/fulltext.md",
            "6fa4f590c86623eda1d0109200100c25408d101e557e98f76fc9db35699b9b59",
            1169,
            1169,
            "凡占卜成卦，即畫成三重：本卦、互卦、變卦也。使於本卦分體用，此一體一用也。",
        ),
    ),
    "divination/meihua-yishu#MR-04-02": (
        (
            "references/fulltext/divination/meihua-yishu/fulltext.md",
            "6fa4f590c86623eda1d0109200100c25408d101e557e98f76fc9db35699b9b59",
            875,
            875,
            "體克用，諸事吉；用克體，諸事凶。體生用，有耗失之患；用生體，有進益之喜。體用比和，則百事順遂。",
        ),
    ),
    "divination/meihua-yishu#MR-04-04": (
        (
            "references/fulltext/divination/meihua-yishu/fulltext.md",
            "6fa4f590c86623eda1d0109200100c25408d101e557e98f76fc9db35699b9b59",
            1320,
            1320,
            "大凡占卜，以體為其主，互用變皆為應。卦用最緊，互次之，變卦又次之。故曰用為占之即應，互為中間之應，變為事占之終應。",
        ),
    ),
    "divination/zengshan-buyi#ZR-04-04": (
        (
            "references/fulltext/divination/zengshan-buyi/fulltext.md",
            "40cb50a05cbcb03ce3d42f2cc3de5daf1db6cf78e8dbae4c4b9b1e42dd6f50e0",
            5895,
            5895,
            "若兩爻俱動或都不發動，擇其旺者爲用神。如一爻動者擇其動者爲用神。",
        ),
        (
            "references/fulltext/divination/zengshan-buyi/fulltext.md",
            "40cb50a05cbcb03ce3d42f2cc3de5daf1db6cf78e8dbae4c4b9b1e42dd6f50e0",
            1076,
            1076,
            "得其驗者﹐應乎旬空月破﹐捨其不空﹐而用旬空﹐捨其不破﹐而用月破。",
        ),
    ),
    "divination/zengshan-buyi#ZR-05-05": (
        (
            "references/fulltext/divination/zengshan-buyi/fulltext.md",
            "40cb50a05cbcb03ce3d42f2cc3de5daf1db6cf78e8dbae4c4b9b1e42dd6f50e0",
            6159,
            6159,
            "七八月金旺，金生水，水爲相，其餘俱作休囚。",
        ),
        (
            "references/fulltext/divination/zengshan-buyi/fulltext.md",
            "40cb50a05cbcb03ce3d42f2cc3de5daf1db6cf78e8dbae4c4b9b1e42dd6f50e0",
            6162,
            6162,
            "十月十一月水旺，水生木，木爲相，其餘俱作休囚。",
        ),
    ),
    "physiognomy/mayi-shenxiang#MR-02": (
        (
            "references/fulltext/physiognomy/mayi-shenxiang/fulltext.md",
            "c9b02fe305c963d1e22ba694daf600297d9e4d8c3adad8bfaa7316f9471e8bc2",
            55,
            67,
            "第一天中对天岳，左厢内府相随续。",
        ),
        (
            "references/fulltext/physiognomy/mayi-shenxiang/fulltext.md",
            "c9b02fe305c963d1e22ba694daf600297d9e4d8c3adad8bfaa7316f9471e8bc2",
            116,
            127,
            "命宫者，居两眉之间，山根之上。",
        ),
        (
            "references/fulltext/physiognomy/mayi-shenxiang/fulltext.md",
            "c9b02fe305c963d1e22ba694daf600297d9e4d8c3adad8bfaa7316f9471e8bc2",
            258,
            258,
            "五官者，一曰耳为采听官，二曰眉为保寿官，三曰眼为监察官，四曰鼻为审辨官，五曰口为出纳官。",
        ),
    ),
    "physiognomy/shenxiang-quanbian#SR-02-04": (
        (
            "references/fulltext/physiognomy/shenxiang-quanbian/fulltext.md",
            "984eac109baef32a234be23f0612b604d65cd08d26c4f5e00411e61d9e638865",
            1062,
            1072,
            None,
        ),
    ),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _catalog() -> dict[str, Mapping[str, Any]]:
    payload = json.loads(
        (ROOT / "references/catalog/catalog.json").read_text(encoding="utf-8")
    )
    return {
        f"{item['system']}/{item['slug']}": item
        for item in payload["ready_reference_packs"]
    }


def _source(
    *,
    path: str,
    sha256: str,
    start: int,
    end: int,
    quote: str,
    location: str = "research_tree",
) -> dict[str, Any]:
    quote = canonicalize(quote)
    anchor = f"{Path(path).name}#L{start}"
    if end != start:
        anchor += f"-L{end}"
    return {
        "path": path,
        "sha256": sha256,
        "anchor": anchor,
        "verbatim_quote": quote,
        "verbatim_quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        "location": location,
    }


def _artifact_source(
    path: str,
    sha256: str,
    start: int,
    end: int,
    *,
    location: str = "research_tree",
) -> dict[str, Any]:
    base = ROOT if location == "release_tree" else RESEARCH_ROOT
    artifact = base / path
    if _sha(artifact) != sha256:
        raise ValueError(f"fixed classical artifact hash mismatch: {path}")
    lines = artifact.read_text(encoding="utf-8", errors="strict").splitlines()
    if not 1 <= start <= end <= len(lines):
        raise ValueError(f"classical source line outside artifact: {path} L{start}-L{end}")
    excerpt = "\n".join(lines[start - 1 : end])
    if not excerpt.strip():
        raise ValueError(f"empty classical source range: {path} L{start}-L{end}")
    return _source(
        path=path,
        sha256=sha256,
        start=start,
        end=end,
        quote=excerpt,
        location=location,
    )


def _fulltext_sources(
    record: Mapping[str, Any], catalog: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    anchor = str(record["source_anchor"])
    if "fulltext.md" not in anchor:
        return []
    ranges = [
        (int(match.group(1)), int(match.group(2) or match.group(1)))
        for match in LINE_RE.finditer(anchor)
    ]
    if not ranges:
        return []
    item = catalog[str(record["source_pack"])]
    path = str(item["local_fulltext_path"])
    sha256 = str(item["local_fulltext_sha256"])
    return [
        _artifact_source(path, sha256, start, end) for start, end in ranges
    ]


def _audited_fixed_sources(
    record: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> list[dict[str, Any]]:
    spec = registry.get(str(record["rule_id"]))
    if spec is None:
        return []
    specs = (spec,) if isinstance(spec[0], str) else spec
    sources: list[dict[str, Any]] = []
    for path, sha256, line_number, quote in specs:
        artifact = RESEARCH_ROOT / path
        if _sha(artifact) != sha256:
            raise ValueError(f"fixed methodology artifact hash mismatch: {path}")
        line = artifact.read_text(encoding="utf-8", errors="strict").splitlines()[
            line_number - 1
        ]
        if quote not in line:
            raise ValueError(
                f"audited source quote is outside exact line: {record['rule_id']}"
            )
        sources.append(
            _source(
                path=path,
                sha256=sha256,
                start=line_number,
                end=line_number,
                quote=quote,
            )
        )
    return sources


def _audited_methodology_sources(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _audited_fixed_sources(record, AUDITED_METHODOLOGY_SOURCES)


def _audited_qiongtong_sources(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _audited_fixed_sources(record, AUDITED_QIONGTONG_CHAPTER_SOURCES)


def _audited_range_quote_sources(
    record: Mapping[str, Any],
) -> list[dict[str, Any]]:
    specs = AUDITED_RANGE_QUOTE_SOURCES.get(str(record["rule_id"]))
    if specs is None:
        return []
    sources: list[dict[str, Any]] = []
    for path, sha256, start, end, fixed_quote in specs:
        artifact = RESEARCH_ROOT / path
        if _sha(artifact) != sha256:
            raise ValueError(f"fixed ranged artifact hash mismatch: {path}")
        lines = artifact.read_text(encoding="utf-8", errors="strict").splitlines()
        excerpt = "\n".join(lines[start - 1 : end])
        quote = excerpt if fixed_quote is None else fixed_quote
        if not quote.strip() or quote not in excerpt:
            raise ValueError(
                f"audited ranged quote is outside exact lines: {record['rule_id']}"
            )
        sources.append(
            _source(
                path=path,
                sha256=sha256,
                start=start,
                end=end,
                quote=quote,
            )
        )
    return sources


def _qimen_excerpt_source(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    anchors = {"QM-P26": "QMF-PAT-01", "QM-P36": "QMF-PAT-02"}
    marker = anchors.get(str(record["local_rule_id"]))
    if record["source_pack"] != "san-shi/qimen-faqiao" or marker is None:
        return []
    path = "references/source-excerpts/qimen-faqiao-chaibu-v1.md"
    artifact = ROOT / path
    lines = artifact.read_text(encoding="utf-8").splitlines()
    start = next(index for index, line in enumerate(lines, 1) if marker in line)
    end = next(
        (
            index - 1
            for index, line in enumerate(lines[start:], start + 1)
            if line.startswith("## ")
        ),
        len(lines),
    )
    quote = str(record["quote"])
    excerpt = "\n".join(lines[start - 1 : end])
    if canonicalize(quote) not in canonicalize(excerpt):
        raise ValueError(f"qimen allowlist quote is outside section: {record['rule_id']}")
    return [
        _source(
            path=path,
            sha256=_sha(artifact),
            start=start,
            end=end,
            quote=quote,
            location="release_tree",
        )
    ]


def _normalized_alias_sources(
    record: Mapping[str, Any], catalog: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    pack = str(record["source_pack"])
    local_id = str(record["local_rule_id"])
    anchor = str(record["source_anchor"])
    if pack == "physiognomy/bingjian" and re.fullmatch(r"normalized#L[1-9][0-9]*", anchor):
        start = int(anchor.rsplit("L", 1)[1])
        item = catalog[pack]
        return [
            _artifact_source(
                str(item["local_fulltext_path"]),
                str(item["local_fulltext_sha256"]),
                start,
                start,
            )
        ]
    if pack == "xingming/guotian-jing" and local_id in {"GR-01-01", "GR-01-02"}:
        # GR-01-01 explicitly combines the year-month and day-hour witnesses;
        # GR-01-02 is the complete twelve-palace verse, not its heading alone.
        start, end = ((31, 36) if local_id == "GR-01-01" else (39, 51))
        item = catalog[pack]
        return [
            _artifact_source(
                str(item["local_fulltext_path"]),
                str(item["local_fulltext_sha256"]),
                start,
                end,
            )
        ]
    return []


def _raw_rule_fields(record: Mapping[str, Any]) -> Mapping[str, str]:
    path = ROOT / str(record["source_path"])
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    raw = {rule.local_id: rule for rule in compiler._heading_rules(lines)}
    for rule in compiler._table_rules(lines):
        raw.setdefault(rule.local_id, rule)
    return raw[str(record["local_rule_id"])].fields


def _quote_registry(pack: str) -> dict[str, tuple[str, int, int]]:
    path = ROOT / f"references/books/{pack}/quote-index.md"
    text = path.read_text(encoding="utf-8")
    result: dict[str, tuple[str, int, int]] = {}
    # Markdown table registries (notably Liuren Zhiyin).
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3 or QUOTE_ID_RE.fullmatch(cells[0]) is None:
            continue
        line_match = LINE_RE.search(" ".join(cells[2:]))
        if line_match:
            start = int(line_match.group(1))
            end = int(line_match.group(2) or start)
            result[cells[0]] = (cells[1], start, end)
    # Heading/field registries (Daquan and Miben).
    blocks = list(
        re.finditer(
            r"^###\s+((?:DLQ-[0-9]{3}|(?:LZ|LM)-Q[0-9]{3}))\s*$",
            text,
            re.M,
        )
    )
    for offset, match in enumerate(blocks):
        end_offset = blocks[offset + 1].start() if offset + 1 < len(blocks) else len(text)
        block = text[match.end() : end_offset]
        quote_match = re.search(r"(?:\*\*)?exact_quote(?:\*\*)?\s*:\s*`([^`]+)`", block)
        anchor_match = LINE_RE.search(block)
        if quote_match and anchor_match:
            start = int(anchor_match.group(1))
            end = int(anchor_match.group(2) or start)
            result[match.group(1)] = (quote_match.group(1), start, end)
    return result


def _explicit_quote_id_sources(
    record: Mapping[str, Any], catalog: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    pack = str(record["source_pack"])
    if pack not in {"san-shi/daliuren-daquan", "san-shi/liuren-zhiyin"}:
        return []
    quote_ids = QUOTE_ID_RE.findall(str(_raw_rule_fields(record).get("quote_id") or ""))
    if not quote_ids:
        return []
    registry = _quote_registry(pack)
    item = catalog[pack]
    path = str(item["local_fulltext_path"])
    sha256 = str(item["local_fulltext_sha256"])
    sources: list[dict[str, Any]] = []
    artifact_lines = (RESEARCH_ROOT / path).read_text(encoding="utf-8").splitlines()
    for quote_id in quote_ids:
        quote, start, end = registry[quote_id]
        excerpt = "\n".join(artifact_lines[start - 1 : end])
        if canonicalize(quote) not in canonicalize(excerpt):
            raise ValueError(f"quote registry mismatch: {pack} {quote_id}")
        sources.append(
            _source(path=path, sha256=sha256, start=start, end=end, quote=quote)
        )
    return sources


def _lixuzhong_source(
    record: Mapping[str, Any], catalog: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    match = re.fullmatch(r"LX-01-([0-9]{2})", str(record["local_rule_id"]))
    if record["source_pack"] != "luming-nayin/li-xuzhong-mingshu" or match is None:
        return []
    number = int(match.group(1))
    if not 1 <= number <= 60:
        return []
    quote_id = f"LX-Q{number:03d}"
    table = (
        ROOT / "references/books/luming-nayin/li-xuzhong-mingshu/quote-index.md"
    ).read_text(encoding="utf-8")
    row = next(line for line in table.splitlines() if line.startswith(f"| {quote_id} |"))
    cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
    quote = cells[1]
    anchor_match = LINE_RE.search(cells[3])
    if anchor_match is None or not quote.startswith(compiler.LUMING_SIXTY_JIAZI[number - 1]):
        raise ValueError(f"Li Xuzhong deterministic quote mapping mismatch: {quote_id}")
    start = int(anchor_match.group(1))
    item = catalog[str(record["source_pack"])]
    path = str(item["local_fulltext_path"])
    sha256 = str(item["local_fulltext_sha256"])
    excerpt = (RESEARCH_ROOT / path).read_text(encoding="utf-8").splitlines()[start - 1]
    if canonicalize(quote) not in canonicalize(excerpt):
        raise ValueError(f"Li Xuzhong quote is absent from fixed fulltext: {quote_id}")
    return [_source(path=path, sha256=sha256, start=start, end=start, quote=quote)]


def generate() -> dict[str, Any]:
    catalog = _catalog()
    records = compiler.compile_evidence_rules(
        root=ROOT,
        enforce_classical_bindings=False,
    )
    bindings: dict[str, Any] = {}
    for record in records:
        if not record["required_fact_predicates"] and not record["excluded_fact_predicates"]:
            continue
        sources = (
            _audited_methodology_sources(record)
            or _audited_qiongtong_sources(record)
            or _audited_range_quote_sources(record)
            or _fulltext_sources(record, catalog)
            or _qimen_excerpt_source(record)
            or _normalized_alias_sources(record, catalog)
            or _explicit_quote_id_sources(record, catalog)
            or _lixuzhong_source(record, catalog)
        )
        mechanically_located = bool(sources)
        semantically_verified = record["rule_id"] in SEMANTICALLY_VERIFIED_RULE_IDS
        if semantically_verified and not mechanically_located:
            raise ValueError(
                f"semantic whitelist entry lacks an exact source: {record['rule_id']}"
            )
        status = "verified" if semantically_verified else "inactive_unverified"
        binding = {
            "rule_id": record["rule_id"],
            "verification_status": status,
            "semantic_verification_status": status,
            "verification_method": (
                "source_and_applicability_semantically_audited"
                if semantically_verified
                else "runtime_inactive_pending_semantic_source_applicability_audit"
            ),
            "mechanical_location_status": (
                "verified_exact" if mechanically_located else "unverified"
            ),
            "applicability_signature": compiler.canonical_predicate_signature(
                record["required_fact_predicates"],
                record["excluded_fact_predicates"],
            ),
            "rule_record_digest": compiler.canonical_rule_record_digest(record),
            "classical_sources": sources,
        }
        binding["binding_digest"] = compiler._classical_binding_digest(binding)
        bindings[str(record["rule_id"])] = binding
    return {
        "schema_version": "mingli-classical-evidence-bindings-v1",
        "policy": {
            "unverified_predicate_rules": "runtime_inactive",
            "runtime_requires_external_research_tree": False,
            "source_matching": "exact_only_no_fuzzy_fallback",
        },
        "audit_note": (
            "Exact location is not semantic authorization. Only independently "
            "audited source-and-applicability bindings are runtime active. Located "
            "candidates remain inactive until source meaning and applicability are "
            "independently audited; no similarity fallback exists."
        ),
        "bindings": dict(sorted(bindings.items())),
    }


def main() -> int:
    payload = generate()
    rendered = json.dumps(
        payload, ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
    OUTPUT.write_text(rendered, encoding="utf-8")
    verified = sum(
        item["verification_status"] == "verified"
        for item in payload["bindings"].values()
    )
    print(
        json.dumps(
            {
                "records": len(payload["bindings"]),
                "verified": verified,
                "inactive": len(payload["bindings"]) - verified,
                "sha256": hashlib.sha256(rendered.encode()).hexdigest(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
