"""Run an open-ended factuality benchmark through an OpenAI-compatible API.

Unlike multiple-choice evaluation, FactBench has no single answer key.  This
runner therefore never guesses a correctness label: it retains each original
prompt, answer, API metadata, and log probabilities for later VERIFY/human
annotation.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .evaluate_mcq import call_chat_completion


SYSTEM_PROMPT = (
    "You are a careful factual assistant. Answer the user's request directly. "
    "Do not invent sources, dates, statistics, products, or quotations. "
    "When the request needs up-to-date information you cannot verify, say what "
    "cannot be confirmed instead of presenting a guess as fact. Keep the answer "
    "under 220 English words (or an equivalently concise length in another language)."
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--method", default="direct")
    parser.add_argument("--limit", type=int, default=None, help="Optional smoke-test limit")
    parser.add_argument(
        "--max-tokens", type=int, default=None,
        help="Override config output limit; use 512 for the FactBench baseline",
    )
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    key = os.environ.get(cfg["api_key_env"])
    if not key:
        raise RuntimeError(f"Missing environment variable: {cfg['api_key_env']}")
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    system_prompt = cfg.get("factual_system_prompt", SYSTEM_PROMPT)
    request_cfg = {**cfg, "system_prompt": system_prompt}
    if args.max_tokens is not None:
        if args.max_tokens <= 0:
            raise ValueError("--max-tokens must be positive")
        request_cfg["max_tokens"] = args.max_tokens

    n = 0
    with Path(args.input).open(encoding="utf-8-sig") as source, output.open("w", encoding="utf-8") as sink:
        for line in source:
            if not line.strip():
                continue
            if args.limit is not None and n >= args.limit:
                break
            item = json.loads(line)
            prompt = item["question"]
            raw, logprob_data, usage, latency_s, returned_model = call_chat_completion(request_cfg, key, prompt)
            record = {
                "item": item,
                "method": args.method,
                "prompt": prompt,
                "raw_output": raw,
                "api_logprobs": logprob_data,
                "annotation": None,
                "metadata": {
                    "model": cfg["model"], "base_url": cfg["base_url"],
                    "returned_model": returned_model,
                    "temperature": cfg.get("temperature", 0), "top_p": cfg.get("top_p", 1),
                    "max_tokens": request_cfg.get("max_tokens", 64), "thinking": cfg.get("thinking"),
                    "logprobs_requested": bool(cfg.get("logprobs")), "usage": usage,
                    "latency_s": latency_s, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                },
            }
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")
            n += 1
            print(f"completed {n}: {item['id']}")
    print(json.dumps({"n": n, "method": args.method, "out": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
