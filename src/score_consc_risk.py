"""Score factual-answer risk with an independently prompted consistency auditor."""
from __future__ import annotations
import argparse, json, os, re
from datetime import datetime, timezone
from pathlib import Path
from .evaluate_mcq import call_chat_completion

AUDITOR = """You are a claim-risk auditor for factuality verification. Do NOT judge whether the answer is true. Instead assess how much external checking it needs, based on its factual-claim surface: dates, quantities, named entities, precise locations, legal/medical/financial advice, current policies, contact details, and specific rankings. Return ONLY one integer:
1 = generic advice or definition with almost no externally verifiable claim;
2 = a few stable, low-stakes factual claims;
3 = several specific factual claims or named entities;
4 = multiple precise claims (dates, numbers, titles, institutions) or a high-stakes domain;
5 = time-sensitive, medical, legal, financial, emergency/contact, or many precise claims that need external verification."""
RISK = re.compile(r"\b([1-5])\b")

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True); p.add_argument("--input", required=True); p.add_argument("--out", required=True); p.add_argument("--limit", type=int)
    a = p.parse_args(); cfg = json.loads(Path(a.config).read_text(encoding="utf-8")); key = os.environ.get(cfg["api_key_env"])
    if not key: raise RuntimeError(f"Missing environment variable: {cfg['api_key_env']}")
    audit_cfg = {**cfg, "system_prompt": AUDITOR, "max_tokens": 8}; Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with Path(a.input).open(encoding="utf-8-sig") as source, Path(a.out).open("w", encoding="utf-8") as sink:
        for line in source:
            if not line.strip() or (a.limit is not None and count >= a.limit): continue
            direct = json.loads(line); prompt = f"QUESTION:\n{direct['prompt']}\n\nPROPOSED ANSWER:\n{direct['raw_output']}\n\nRISK:"
            raw, lp, usage, latency, model = call_chat_completion(audit_cfg, key, prompt)
            match = RISK.search(raw.strip()); score = int(match.group(1)) if match else None
            rec = {"direct": direct, "audit_prompt": prompt, "audit_output": raw, "risk_score": score, "audit_logprobs": lp, "metadata": {"model": cfg["model"], "returned_model": model, "max_tokens": 8, "usage": usage, "latency_s": latency, "timestamp_utc": datetime.now(timezone.utc).isoformat()}}
            sink.write(json.dumps(rec, ensure_ascii=False) + "\n"); count += 1; print(f"completed {count}: {direct['item']['id']} risk={score}")
    print(json.dumps({"n": count, "out": a.out}, ensure_ascii=False))

if __name__ == "__main__": main()
