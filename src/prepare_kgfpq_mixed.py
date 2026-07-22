"""Create a paired true/false KG-FPQ evaluation split from frozen false premises."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--false-input", required=True, help="Frozen KG-FPQ false-premise JSONL")
    p.add_argument("--raw-dir", required=True, help="Official KG-FPQ raw directory containing TPQ fields")
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=20260822)
    a = p.parse_args()
    false_rows = [json.loads(line) for line in Path(a.false_input).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    official = {}
    for domain in ("art", "people", "place"):
        for row in json.loads((Path(a.raw_dir) / f"{domain}_YN.json").read_text(encoding="utf-8")):
            official[(domain, row["id"])] = row
    output = []
    for row in false_rows:
        source_id = row.get("source_record_id")
        if not source_id:
            raise ValueError("false-input must include source_record_id; regenerate it with prepare_kgfpq_yn.py")
        source = official[(row["domain"], source_id)]
        base_id = row["id"]
        false_row = {**row, "id": f"{base_id}-false", "pair_id": base_id, "polarity": "false", "source": "KG-FPQ YN false premise"}
        true_row = {
            **row,
            "id": f"{base_id}-true",
            "pair_id": base_id,
            "polarity": "true",
            "question": source["TPQ"],
            "expected": "YES",
            "source": "KG-FPQ official true premise question (TPQ)",
        }
        output.extend([false_row, true_row])
    random.Random(a.seed).shuffle(output)
    out_path = Path(a.out); out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output), encoding="utf-8")
    print(json.dumps({"n": len(output), "false_n": len(false_rows), "true_n": len(false_rows), "seed": a.seed, "out": str(out_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
