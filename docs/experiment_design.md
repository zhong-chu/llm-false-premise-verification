# Final experiment design

## Scope

This project evaluates black-box inference-time mitigation of false-premise-induced factual errors. Its conclusion is restricted to KG-FPQ Yes/No questions with trusted knowledge-graph evidence. It does not claim general mitigation of open-ended hallucinations.

## Model and logging

The evaluated model is `deepseek-v4-flash` through the official OpenAI-compatible endpoint. Temperature is zero. Every API call records the returned model name, token usage, latency, raw answer, parsed answer, and method stage in a local JSONL run log. Secrets and raw run logs are excluded from the public repository.

## Data

KG-FPQ is a knowledge-graph false-premise benchmark. The primary false-premise split contains 360 questions: 3 domains x 6 confusability levels x 20 questions, seed `20260820`. The independent false-premise replication split contains another 360 questions, seed `20260821`, with no overlapping source records. A paired mixed split combines the 360 replication FPQs with their official true-premise questions (TPQs), for 720 questions total.

## Methods

- **Direct**: answer the original question once.
- **CoVe-style self-verification**: independently verify the relation with the same LLM, then generate a final answer. This is a binary-task adaptation of CoVe, not an exact reproduction of every CoVe stage.
- **Full evidence verification**: provide a trusted true triple for every item and answer again. It is a costed evidence upper bound.
- **ConSC-Verify v1**: claim-surface risk routing. It is retained as a failed ablation.
- **PASEV**: after Direct, provide trusted evidence only when the answer is affirmative or unparseable. It is a lightweight post-hoc policy for false-premise-induced false affirmations.

## Reporting rules

Report accuracy, Wilson 95% interval, verification rate, API calls, mean tokens per item, and mean latency per item. For paired experiments, also report corrected Direct errors and newly introduced errors. Results from the FPQ-only split and the TPQ/FPQ mixed split must be reported separately.

## Main boundary finding

PASEV corrected false affirmations on FPQ questions but did not correct true-premise questions that the model incorrectly rejected with `NO`. It is therefore not a general factuality method. The mixed result is included specifically to prevent over-generalization.
