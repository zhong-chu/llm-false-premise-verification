"""Merge AI-assisted review labels into an auditable JSONL run."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

LABELS = {"supported", "unsupported", "undecidable"}

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True); p.add_argument("--csv", required=True); p.add_argument("--out", required=True)
    a = p.parse_args()
    runs = [json.loads(x) for x in Path(a.input).read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    with Path(a.csv).open(encoding="utf-8-sig", newline="") as f:
        reviews = {x["id"]: x for x in csv.DictReader(f)}
    counts = {x: 0 for x in LABELS}
    with Path(a.out).open("w", encoding="utf-8") as sink:
        for row in runs:
            review = reviews[row["item"]["id"]]
            label = review.get("ai_assisted_label", "").strip().lower()
            if label not in LABELS: raise ValueError(f"Invalid label: {label}")
            row["annotation"] = {"label": label, "source": "ai_assisted_initial_review", "note": review.get("ai_assisted_note") or None}
            counts[label] += 1
            sink.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"n": len(runs), "labels": counts, "out": a.out}, ensure_ascii=False))

if __name__ == "__main__": main()
