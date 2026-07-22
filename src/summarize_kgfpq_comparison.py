"""Create reproducible KG-FPQ result tables from per-item JSONL logs."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def read_rows(path: str):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def wilson(successes: int, n: int):
    if not n:
        return [None, None]
    z = 1.96
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [max(0.0, center - radius), min(1.0, center + radius)]


def summarize(name: str, path: str):
    rows = read_rows(path)
    n = len(rows)
    correct = sum(bool(row["correct"]) for row in rows)
    verified = sum(bool(row.get("verified", False)) for row in rows)
    if name in {"Full evidence verification", "CoVe-style self-verification"}:
        verified = n
    calls = [call for row in rows for call in row.get("calls", [])]
    tokens = sum((call.get("usage") or {}).get("total_tokens", 0) or 0 for call in calls)
    latency = sum(call.get("latency_s", 0) or 0 for call in calls)
    return {
        "method": name,
        "n": n,
        "correct": correct,
        "accuracy": correct / n,
        "wilson_95_ci": wilson(correct, n),
        "verified_n": verified,
        "verification_rate": verified / n,
        "calls": len(calls),
        "total_tokens": tokens,
        "mean_tokens_per_item": tokens / n,
        "mean_latency_s_per_item": latency / n,
        "source": path,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--primary-direct", required=True)
    p.add_argument("--primary-full", required=True)
    p.add_argument("--primary-cove", required=True)
    p.add_argument("--primary-consc-v1", required=True)
    p.add_argument("--primary-pav", required=True)
    p.add_argument("--replication-direct", required=True)
    p.add_argument("--replication-pav", required=True)
    p.add_argument("--json-out", required=True)
    p.add_argument("--markdown-out", required=True)
    a = p.parse_args()
    primary = [
        summarize("Direct", a.primary_direct),
        summarize("Full evidence verification", a.primary_full),
        summarize("CoVe-style self-verification", a.primary_cove),
        summarize("ConSC-Verify v1 (failed ablation)", a.primary_consc_v1),
        summarize("Premise-aware selective verification (exploratory)", a.primary_pav),
    ]
    replication = [
        summarize("Direct", a.replication_direct),
        summarize("Premise-aware selective verification (independent replication)", a.replication_pav),
    ]
    result = {"primary_exploratory": primary, "independent_replication": replication}
    json_path = Path(a.json_out); md_path = Path(a.markdown_out)
    json_path.parent.mkdir(parents=True, exist_ok=True); md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def rows_to_markdown(rows):
        head = "| Method | Correct / n | Accuracy (95% Wilson CI) | Verification rate | Calls | Mean tokens/item | Mean latency/item (s) |\n|---|---:|---:|---:|---:|---:|---:|\n"
        body = []
        for r in rows:
            lo, hi = r["wilson_95_ci"]
            body.append(f"| {r['method']} | {r['correct']} / {r['n']} | {r['accuracy']:.2%} [{lo:.2%}, {hi:.2%}] | {r['verification_rate']:.2%} | {r['calls']} | {r['mean_tokens_per_item']:.2f} | {r['mean_latency_s_per_item']:.3f} |")
        return head + "\n".join(body) + "\n"

    md = "# KG-FPQ experiment results\n\n## Primary exploratory split\n\n" + rows_to_markdown(primary)
    md += "\n## Independent replication split\n\n" + rows_to_markdown(replication)
    md += "\n## Scope\n\nKG-FPQ YN contains false-premise questions. The premise-aware rule verifies an affirmative or unparseable Direct answer and preserves a clear negative answer. It is therefore a method for this false-premise setting, not evidence that the method mitigates every form of open-ended hallucination. ConSC-Verify v1 is retained as a negative ablation because its claim-surface risk score transferred poorly to short relational questions.\n"
    md_path.write_text(md, encoding="utf-8")
    print(json.dumps({"json_out": str(json_path), "markdown_out": str(md_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
