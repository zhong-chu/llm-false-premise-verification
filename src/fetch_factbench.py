"""Download a reproducible FactBench subset from the public Hugging Face API.

FactBench is an open-ended factuality benchmark, so this program deliberately
does not invent reference answers.  It only records the official prompt and
metadata, preserving an immutable input file for later model runs and review.
"""
from __future__ import annotations

import argparse
import json
import random
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "https://datasets-server.huggingface.co/rows"


def get_rows(split: str, length: int = 100) -> list[dict]:
    """Read a complete FactBench split through paginated dataset-server calls."""
    records: list[dict] = []
    offset = 0
    while True:
        query = urllib.parse.urlencode({
            "dataset": "launch/FactBench", "config": "version 1.0",
            "split": split, "offset": offset, "length": length,
        })
        with urllib.request.urlopen(f"{BASE_URL}?{query}", timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = payload.get("rows", [])
        records.extend(row.get("row", row) for row in rows)
        if len(rows) < length:
            return records
        offset += len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Destination JSONL file")
    parser.add_argument("--n", type=int, default=60, help="Number of prompts to retain")
    parser.add_argument("--seed", type=int, default=20260812)
    parser.add_argument("--splits", default="tier_1,tier_2,tier_3")
    args = parser.parse_args()
    if args.n <= 0:
        raise ValueError("--n must be positive")

    source_rows: list[dict] = []
    for split in [x.strip() for x in args.splits.split(",") if x.strip()]:
        for row in get_rows(split):
            row["_factbench_split"] = split
            source_rows.append(row)
    if args.n > len(source_rows):
        raise ValueError(f"Requested {args.n} prompts but only found {len(source_rows)}")

    chosen = random.Random(args.seed).sample(source_rows, args.n)
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as sink:
        for index, row in enumerate(chosen, start=1):
            item = {
                "id": f"factbench-{args.seed}-{index:04d}",
                "question": row["user_prompts"],
                "topic": row.get("topic_description"),
                "source": "FactBench",
                "source_split": row["_factbench_split"],
                "source_hallucination_score": row.get("hallucination_score"),
                "source_prompt_score": row.get("prompt_score"),
                "dataset_url": "https://huggingface.co/datasets/launch/FactBench",
            }
            sink.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(json.dumps({"n": args.n, "seed": args.seed, "out": str(destination)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
