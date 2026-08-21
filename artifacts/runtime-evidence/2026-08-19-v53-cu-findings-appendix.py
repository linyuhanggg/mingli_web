#!/usr/bin/env python3
import json
from pathlib import Path

PREPARES = [
    ("1994_career", Path("/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json")),
    ("1992_career", Path("/tmp/mingli-oneshot-v53-fixture2-20260819/out/prepare.stdout.json")),
    ("yiyou_overview", Path("/Volumes/Lexar/code/mingli_web/.runtime/oneshot-20260819-claim-unit/prepare-out.json")),
]
KEYS = ("claim_unit_id", "day_element", "month_command_element", "seasonal_state",
        "status", "pattern_label", "day_stem", "month_branch", "priority_stems", "hard_verdict")

def main() -> int:
    for label, path in PREPARES:
        print("===", label, "===")
        print("path", path)
        d = json.loads(path.read_text(encoding="utf-8"))
        rows = []
        for f in d["brief"]["findings"]:
            data = f.get("data") or {}
            cid = data.get("claim_unit_id")
            if not cid:
                continue
            row = {k: data.get(k) for k in KEYS if k in data}
            row["public_text"] = f.get("public_text")
            rows.append(row)
            print("claim_unit_id", cid)
            print("public_text", f.get("public_text"))
            for k in KEYS:
                if k in data and k != "claim_unit_id":
                    print("data." + k, data.get(k))
            print()
        print("n_cu_findings", len(rows))
        print("ids", [r["claim_unit_id"] for r in rows])
        print()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
