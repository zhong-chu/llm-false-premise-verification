"""Choose a verification threshold on a labeled development run only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from risk_features import extract_risk_features


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Labeled development JSONL with `correct` fields")
    parser.add_argument("--out", required=True)
    parser.add_argument("--target-error-recall", type=float, default=0.80)
    args = parser.parse_args()
    if not 0 < args.target_error_recall <= 1:
        raise ValueError("--target-error-recall must be in (0, 1]")

    rows = [json.loads(x) for x in Path(args.input).read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    if not rows or not all("correct" in row for row in rows):
        raise ValueError("The development run must contain non-empty `correct` labels.")
    enriched = [{**row, "risk_features": extract_risk_features(row)} for row in rows]
    errors = [row for row in enriched if not row["correct"]]
    if not errors:
        raise ValueError("Development set has no errors; it cannot calibrate a risk threshold.")

    candidates = []
    for i in range(101):
        threshold = i / 100
        triggered = [row for row in enriched if row["risk_features"]["risk"] >= threshold]
        caught_errors = sum(not row["correct"] for row in triggered)
        candidates.append({
            "threshold": threshold,
            "trigger_rate": len(triggered) / len(enriched),
            "error_recall": caught_errors / len(errors),
            "error_miss_rate": 1 - caught_errors / len(errors),
        })
    feasible = [x for x in candidates if x["error_recall"] >= args.target_error_recall]
    selected = max(feasible, key=lambda x: x["threshold"]) if feasible else max(candidates, key=lambda x: x["error_recall"])
    result = {
        "selection_rule": "highest threshold reaching target error recall on development set",
        "target_error_recall": args.target_error_recall,
        "selected": selected,
        "curve": candidates,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["selected"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
