"""Export factuality runs to a reviewer-friendly CSV and merge reviewed labels back."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


LABELS = {"supported", "unsupported", "undecidable"}


def export_csv(input_path: Path, output_path: Path) -> None:
    rows = [json.loads(line) for line in input_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id", "topic", "question", "model_answer", "rater_1_label", "rater_1_evidence",
        "rater_2_label", "rater_2_evidence", "ai_assisted_label", "ai_assisted_note",
        "adjudicated_label", "adjudication_note",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as sink:
        writer = csv.DictWriter(sink, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "id": row["item"]["id"], "topic": row["item"].get("topic", ""),
                "question": row["prompt"], "model_answer": row["raw_output"],
                "rater_1_label": "", "rater_1_evidence": "", "rater_2_label": "",
                "rater_2_evidence": "", "ai_assisted_label": "", "ai_assisted_note": "",
                "adjudicated_label": "", "adjudication_note": "",
            })
    print(json.dumps({"n": len(rows), "out": str(output_path)}, ensure_ascii=False))


def merge_csv(input_path: Path, csv_path: Path, output_path: Path) -> None:
    runs = [json.loads(line) for line in input_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        reviewed = {row["id"]: row for row in csv.DictReader(source)}
    missing = [row["item"]["id"] for row in runs if row["item"]["id"] not in reviewed]
    if missing:
        raise ValueError(f"CSV is missing {len(missing)} run IDs")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = 0
    with output_path.open("w", encoding="utf-8") as sink:
        for run in runs:
            review = reviewed[run["item"]["id"]]
            label = review.get("adjudicated_label", "").strip().lower()
            if label and label not in LABELS:
                raise ValueError(f"Invalid adjudicated label for {run['item']['id']}: {label}")
            run["annotation"] = {
                "rater_1_label": review.get("rater_1_label", "").strip().lower() or None,
                "rater_1_evidence": review.get("rater_1_evidence", "").strip() or None,
                "rater_2_label": review.get("rater_2_label", "").strip().lower() or None,
                "rater_2_evidence": review.get("rater_2_evidence", "").strip() or None,
                "adjudicated_label": label or None,
                "adjudication_note": review.get("adjudication_note", "").strip() or None,
            }
            if label:
                completed += 1
            sink.write(json.dumps(run, ensure_ascii=False) + "\n")
    print(json.dumps({"n": len(runs), "labeled": completed, "out": str(output_path)}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", action="store_true")
    group.add_argument("--merge", action="store_true")
    parser.add_argument("--input", required=True, help="Factual run JSONL")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out", required=True, help="CSV destination for export; JSONL destination for merge")
    args = parser.parse_args()
    if args.export:
        export_csv(Path(args.input), Path(args.out))
    else:
        merge_csv(Path(args.input), Path(args.csv), Path(args.out))


if __name__ == "__main__":
    main()
