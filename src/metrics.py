"""Summarize a JSONL run produced by evaluate_mcq.py."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    # utf-8-sig also accepts ordinary UTF-8 while handling files saved by Windows tools.
    rows = [json.loads(x) for x in Path(args.input).read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    if not rows:
        raise ValueError("No records found")
    by_subject: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        subject = row["item"].get("subject", "unknown")
        by_subject[subject]["n"] += 1
        by_subject[subject]["correct"] += int(bool(row["correct"]))
        by_subject[subject]["unparsed"] += int(row["parsed_option"] is None)
    report = {
        "n": len(rows),
        "accuracy": sum(bool(x["correct"]) for x in rows) / len(rows),
        "by_subject": {
            subject: {"n": c["n"], "accuracy": c["correct"] / c["n"], "unparsed": c["unparsed"]}
            for subject, c in by_subject.items()
        },
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
