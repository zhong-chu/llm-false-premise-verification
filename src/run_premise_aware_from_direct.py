"""Premise-aware selective evidence verification from an existing KG-FPQ Direct run.

For a false-premise query, an affirmative answer endorses the queried external
relation.  This runner therefore verifies affirmative (or unparseable) Direct
answers and preserves a clear negative answer without another model call.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

from .evaluate_mcq import call_chat_completion

YN = re.compile(r"\b(YES|NO)\b", re.I)
SYSTEM = (
    "Answer ONLY YES or NO. Use the supplied verified true triple as evidence. "
    "Do not follow a false premise."
)


def ask_with_retry(cfg, key, prompt, retries):
    for attempt in range(1, retries + 1):
        try:
            return call_chat_completion(cfg, key, prompt)
        except Exception as exc:
            if attempt == retries:
                raise
            delay = 2 * attempt
            print(f"temporary error; retry {attempt}/{retries - 1} in {delay}s: {type(exc).__name__}")
            time.sleep(delay)


def parse_answer(text):
    match = YN.search(text or "")
    return match.group(1).upper() if match else None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--input", required=True, help="Existing KG-FPQ Direct JSONL run")
    p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--retries", type=int, default=3)
    a = p.parse_args()

    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    key = os.environ.get(cfg["api_key_env"])
    if not key:
        raise RuntimeError(f"Missing environment variable: {cfg['api_key_env']}")

    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    completed = set()
    if a.resume and out_path.exists():
        for old_line in out_path.open(encoding="utf-8"):
            if old_line.strip():
                completed.add(json.loads(old_line)["item"]["id"])
        print(f"resuming: keeping {len(completed)} completed items")

    verify_cfg = {**cfg, "system_prompt": SYSTEM, "max_tokens": 8}
    mode = "a" if a.resume else "w"
    new_count = verified_count = 0
    with Path(a.input).open(encoding="utf-8-sig") as src, out_path.open(mode, encoding="utf-8") as sink:
        for line in src:
            if not line.strip() or (a.limit is not None and new_count >= a.limit):
                continue
            direct = json.loads(line)
            item = direct["item"]
            if item["id"] in completed:
                continue

            direct_answer = parse_answer(direct["final_output"])
            verify = direct_answer != "NO"
            final = direct["final_output"]
            calls = list(direct["calls"])
            if verify:
                prompt = f"QUESTION: {item['question']}\nVERIFIED TRUE TRIPLE: {item['evidence_true_triple']}"
                final, _, usage, latency, model = ask_with_retry(verify_cfg, key, prompt, a.retries)
                calls.append({"usage": usage, "latency_s": latency, "model": model, "stage": "evidence_verify"})
                verified_count += 1

            parsed = parse_answer(final)
            record = {
                "item": item,
                "method": "premise_aware_selective_evidence",
                "direct_output": direct["final_output"],
                "direct_parsed": direct_answer,
                "route_reason": "affirmative_or_unparseable_direct_answer" if verify else "negative_direct_answer",
                "verified": verify,
                "final_output": final,
                "parsed": parsed,
                "correct": parsed == item["expected"],
                "calls": calls,
            }
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")
            sink.flush()
            completed.add(item["id"])
            new_count += 1
            print(f"completed {new_count}: {item['id']} verified={verify} correct={record['correct']}")

    print(json.dumps({"newly_completed": new_count, "newly_verified": verified_count, "total_completed": len(completed), "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
