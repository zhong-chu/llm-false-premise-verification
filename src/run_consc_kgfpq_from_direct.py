"""Run claim-sensitive selective verification from an existing KG-FPQ Direct run.

The Direct response is reused so this runner measures only the additional audit and
selective evidence-verification calls made by ConSC-Verify.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

from .evaluate_mcq import call_chat_completion
from .score_consc_risk import AUDITOR

YN = re.compile(r"\b(YES|NO)\b", re.I)
RISK = re.compile(r"\b([1-5])\b")
EVIDENCE_SYSTEM = (
    "Answer ONLY YES or NO. Use the supplied verified true triple as evidence. "
    "Do not follow a false premise."
)


def call_with_retry(cfg, key, prompt, retries):
    for attempt in range(1, retries + 1):
        try:
            return call_chat_completion(cfg, key, prompt)
        except Exception as exc:
            if attempt == retries:
                raise
            wait = 2 * attempt
            print(f"temporary error; retry {attempt}/{retries - 1} in {wait}s: {type(exc).__name__}")
            time.sleep(wait)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--input", required=True, help="Existing KG-FPQ Direct JSONL run")
    p.add_argument("--out", required=True)
    p.add_argument("--threshold", type=int, default=4)
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
    done = set()
    if a.resume and out_path.exists():
        for old_line in out_path.open(encoding="utf-8"):
            if old_line.strip():
                done.add(json.loads(old_line)["item"]["id"])
        print(f"resuming: keeping {len(done)} completed items")

    audit_cfg = {**cfg, "system_prompt": AUDITOR, "max_tokens": 8}
    evidence_cfg = {**cfg, "system_prompt": EVIDENCE_SYSTEM, "max_tokens": 8}
    mode = "a" if a.resume else "w"
    newly_completed = 0
    newly_verified = 0
    with Path(a.input).open(encoding="utf-8-sig") as src, out_path.open(mode, encoding="utf-8") as sink:
        for line in src:
            if not line.strip() or (a.limit is not None and newly_completed >= a.limit):
                continue
            direct = json.loads(line)
            item = direct["item"]
            if item["id"] in done:
                continue

            audit_prompt = f"QUESTION:\n{item['question']}\n\nPROPOSED ANSWER:\n{direct['final_output']}\n\nRISK:"
            audit_raw, _, audit_usage, audit_latency, audit_model = call_with_retry(
                audit_cfg, key, audit_prompt, a.retries
            )
            match = RISK.search(audit_raw.strip())
            risk = int(match.group(1)) if match else None
            final = direct["final_output"]
            verified = risk is not None and risk >= a.threshold
            calls = list(direct["calls"]) + [
                {"usage": audit_usage, "latency_s": audit_latency, "model": audit_model, "stage": "risk_audit"}
            ]
            if verified:
                evidence_prompt = f"QUESTION: {item['question']}\nVERIFIED TRUE TRIPLE: {item['evidence_true_triple']}"
                final, _, usage, latency, model = call_with_retry(evidence_cfg, key, evidence_prompt, a.retries)
                calls.append({"usage": usage, "latency_s": latency, "model": model, "stage": "evidence_verify"})
                newly_verified += 1

            answer_match = YN.search(final)
            answer = answer_match.group(1).upper() if answer_match else None
            record = {
                "item": item,
                "method": "consc_selective_evidence",
                "threshold": a.threshold,
                "direct_output": direct["final_output"],
                "audit_output": audit_raw,
                "risk_score": risk,
                "verified": verified,
                "final_output": final,
                "parsed": answer,
                "correct": answer == item["expected"],
                "calls": calls,
            }
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")
            sink.flush()
            done.add(item["id"])
            newly_completed += 1
            print(f"completed {newly_completed}: {item['id']} risk={risk} verified={verified} correct={record['correct']}")

    print(json.dumps({"newly_completed": newly_completed, "newly_verified": newly_verified, "total_completed": len(done), "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
