"""Run a multiple-choice benchmark through an OpenAI-compatible API.

Each output line retains the source item, rendered prompt, raw answer, parsed
option, correctness flag, and invocation metadata. This makes later audits and
manual corrections possible without re-querying the model.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OPTION_RE = re.compile(r"(?<![A-Z])([A-J])(?![A-Z])", re.IGNORECASE)


def parse_option(text: str) -> str | None:
    """Return the first standalone option letter, or None for an audit case."""
    match = OPTION_RE.search(text.strip().upper())
    return match.group(1) if match else None


def render_prompt(item: dict) -> str:
    choices = "\n".join(f"{key}. {value}" for key, value in item["choices"].items())
    return f"题目：{item['question']}\n选项：\n{choices}\n请仅输出一个选项字母。"


def call_chat_completion(cfg: dict, api_key: str, prompt: str) -> tuple[str, object | None, dict, float, str]:
    """Call the standard OpenAI-compatible /chat/completions endpoint."""
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg["model"],
        "temperature": cfg.get("temperature", 0),
        "top_p": cfg.get("top_p", 1),
        "max_tokens": cfg.get("max_tokens", 64),
        "messages": [
            {"role": "system", "content": cfg["system_prompt"]},
            {"role": "user", "content": prompt},
        ],
    }
    # The fields below are optional in OpenAI-compatible APIs. DeepSeek V4
    # supports them; retaining them in item logs enables later risk analysis.
    if "thinking" in cfg:
        payload["thinking"] = cfg["thinking"]
    if cfg.get("logprobs"):
        payload["logprobs"] = True
        payload["top_logprobs"] = cfg.get("top_logprobs", 5)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned HTTP {exc.code}: {body}") from exc
    choice = data["choices"][0]
    return (
        choice["message"].get("content") or "",
        choice.get("logprobs"),
        data.get("usage", {}),
        round(time.perf_counter() - started, 4),
        data.get("model", cfg["model"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    key = os.environ.get(cfg["api_key_env"])
    if not key:
        raise RuntimeError(f"Missing environment variable: {cfg['api_key_env']}")
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)

    with Path(args.input).open(encoding="utf-8") as source, output.open("w", encoding="utf-8") as sink:
        for line in source:
            if not line.strip():
                continue
            item = json.loads(line)
            prompt = render_prompt(item)
            raw, logprob_data, usage, latency_s, returned_model = call_chat_completion(cfg, key, prompt)
            parsed = parse_option(raw)
            record = {
                "item": item,
                "prompt": prompt,
                "raw_output": raw,
                "api_logprobs": logprob_data,
                "parsed_option": parsed,
                "correct": parsed == item["answer"],
                "metadata": {
                    "model": cfg["model"], "base_url": cfg["base_url"],
                    "returned_model": returned_model,
                    "temperature": cfg.get("temperature", 0), "top_p": cfg.get("top_p", 1),
                    "max_tokens": cfg.get("max_tokens", 64),
                    "thinking": cfg.get("thinking"),
                    "logprobs_requested": bool(cfg.get("logprobs")),
                    "usage": usage,
                    "latency_s": latency_s,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                },
            }
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
