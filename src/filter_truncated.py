"""Create an analysis-ready factuality run by excluding mechanically truncated outputs.

The source run remains untouched.  The exclusion manifest makes all attrition
auditable and prevents incomplete answers from being mislabeled as hallucination.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--excluded", required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    kept, excluded = [], []
    for row in rows:
        usage = row.get("metadata", {}).get("usage", {})
        actual = usage.get("completion_tokens")
        cap = row.get("metadata", {}).get("max_tokens")
        if isinstance(actual, int) and isinstance(cap, int) and actual >= cap:
            excluded.append({
                "id": row["item"].get("id"), "reason": "completion_tokens_reached_max_tokens",
                "completion_tokens": actual, "max_tokens": cap,
            })
        else:
            kept.append(row)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in kept), encoding="utf-8")
    Path(args.excluded).write_text(json.dumps({"input_n": len(rows), "analysis_n": len(kept), "excluded": excluded}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"input_n": len(rows), "analysis_n": len(kept), "excluded_n": len(excluded)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
