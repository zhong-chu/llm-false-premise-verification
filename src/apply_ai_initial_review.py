"""Record a transparent AI-assisted initial factuality review in the CSV.

This is not presented as human annotation.  It gives the researcher a focused
set of entries for manual checking and retains the reasoning behind flags.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


FLAGS = {
    "factbench-20260812-0010": (
        "unsupported",
        "The cited 2022 film Bunker is not accurately described as a lone-soldier story; the answer's recommendation contains a material plot error.",
    ),
    "factbench-20260812-0026": (
        "unsupported",
        "It incorrectly dates routine UK childhood chickenpox vaccination to November 2023; the routine MMRV rollout began in January 2026.",
    ),
    "factbench-20260812-0044": (
        "unsupported",
        "The phonetic example is internally wrong: Ukrainian and Russian both spell 'milk' as молоко; the claimed o-to-i example is not supported.",
    ),
    "factbench-20260812-0052": (
        "unsupported",
        "800-HOPE is an official UAE mental-support line, but the response adds unverified claims about operator, 24/7 availability, and a suicide-prevention designation.",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    args = parser.parse_args()
    path = Path(args.csv)
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        rows = list(reader)
        fields = reader.fieldnames or []
    for required in ("ai_assisted_label", "ai_assisted_note"):
        if required not in fields:
            raise ValueError("Re-export the CSV with the current export_annotations.py before applying review")
    for row in rows:
        label, note = FLAGS.get(row["id"], ("supported", "No material unsupported factual claim identified in AI-assisted initial review."))
        row["ai_assisted_label"] = label
        row["ai_assisted_note"] = note
    with path.open("w", encoding="utf-8-sig", newline="") as sink:
        writer = csv.DictWriter(sink, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print({"n": len(rows), "supported": len(rows) - len(FLAGS), "unsupported": len(FLAGS)})


if __name__ == "__main__":
    main()
