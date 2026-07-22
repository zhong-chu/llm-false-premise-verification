"""Audit an open-ended factuality run without claiming unperformed scoring."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not rows:
        raise ValueError("No records found")
    outputs = [row.get("raw_output", "") for row in rows]
    latencies = [row.get("metadata", {}).get("latency_s") for row in rows]
    token_counts = [row.get("metadata", {}).get("usage", {}).get("total_tokens") for row in rows]
    report = {
        "n": len(rows),
        "method": rows[0].get("method"),
        "models": sorted({row.get("metadata", {}).get("returned_model") for row in rows}),
        "empty_outputs": [row["item"].get("id") for row, output in zip(rows, outputs) if not output.strip()],
        "logprob_return_rate": sum(bool(row.get("api_logprobs")) for row in rows) / len(rows),
        "mean_latency_s": sum(x for x in latencies if isinstance(x, (int, float))) / len(rows),
        "mean_total_tokens": sum(x for x in token_counts if isinstance(x, (int, float))) / len(rows),
        "factuality_labels_present": sum(row.get("annotation") is not None for row in rows),
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
