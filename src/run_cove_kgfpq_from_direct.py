"""CoVe-style self-verification baseline for KG-FPQ Yes/No questions.

KG-FPQ questions contain one factual relation, so the verification-question
planning stage of CoVe is collapsed to an independent assessment of that same
relation. The verifier never receives the Direct answer; a final stage then
uses the independently generated verification result to answer the question.
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
VERIFY_SYSTEM = (
    "You are an independent factual verification stage. Decide whether the "
    "relation asserted by the question is true, using only your own knowledge. "
    "Do not assume the premise is true. Answer ONLY YES or NO."
)
FINAL_SYSTEM = (
    "Answer the original question ONLY YES or NO. Use the independent "
    "verification result to check the initial draft; do not follow a false premise."
)


def parse(text):
    match = YN.search(text or "")
    return match.group(1).upper() if match else None


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
        for line in out_path.open(encoding="utf-8"):
            if line.strip():
                completed.add(json.loads(line)["item"]["id"])
        print(f"resuming: keeping {len(completed)} completed items")

    verify_cfg = {**cfg, "system_prompt": VERIFY_SYSTEM, "max_tokens": 8}
    final_cfg = {**cfg, "system_prompt": FINAL_SYSTEM, "max_tokens": 8}
    mode = "a" if a.resume else "w"
    new_count = 0
    with Path(a.input).open(encoding="utf-8-sig") as source, out_path.open(mode, encoding="utf-8") as sink:
        for line in source:
            if not line.strip() or (a.limit is not None and new_count >= a.limit):
                continue
            direct = json.loads(line)
            item = direct["item"]
            if item["id"] in completed:
                continue
            verification, _, usage_v, latency_v, model_v = ask_with_retry(
                verify_cfg, key, f"QUESTION: {item['question']}", a.retries
            )
            final_prompt = (
                f"ORIGINAL QUESTION: {item['question']}\n"
                f"INITIAL DRAFT: {direct['final_output']}\n"
                f"INDEPENDENT VERIFICATION: {verification}\n"
                "FINAL ANSWER:"
            )
            final, _, usage_f, latency_f, model_f = ask_with_retry(final_cfg, key, final_prompt, a.retries)
            answer = parse(final)
            record = {
                "item": item,
                "method": "cove_style_self_verification",
                "direct_output": direct["final_output"],
                "verification_output": verification,
                "final_output": final,
                "parsed": answer,
                "correct": answer == item["expected"],
                "calls": list(direct["calls"]) + [
                    {"usage": usage_v, "latency_s": latency_v, "model": model_v, "stage": "independent_verify"},
                    {"usage": usage_f, "latency_s": latency_f, "model": model_f, "stage": "final_answer"},
                ],
            }
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")
            sink.flush()
            completed.add(item["id"])
            new_count += 1
            print(f"completed {new_count}: {item['id']} correct={record['correct']}")
    print(json.dumps({"newly_completed": new_count, "total_completed": len(completed), "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
