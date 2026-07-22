"""Check whether a run is complete enough to be used in the experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--expected-n", type=int)
    args = parser.parse_args()

    rows = [json.loads(x) for x in Path(args.input).read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    if args.expected_n is not None and len(rows) != args.expected_n:
        raise SystemExit(f"Expected {args.expected_n} rows, found {len(rows)}")
    missing = [r["item"].get("id", "<unknown>") for r in rows if not r.get("raw_output")]
    logprob_rows = sum(r.get("api_logprobs") is not None for r in rows)
    models = sorted({r.get("metadata", {}).get("model") for r in rows})
    print(json.dumps({
        "n": len(rows),
        "models": models,
        "empty_outputs": missing,
        "logprob_rows": logprob_rows,
        "logprob_return_rate": logprob_rows / len(rows) if rows else 0,
    }, ensure_ascii=False, indent=2))
    if missing:
        raise SystemExit("Run has empty outputs; do not use it.")


if __name__ == "__main__":
    main()
