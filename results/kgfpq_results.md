# KG-FPQ experiment results

## Primary exploratory split

| Method | Correct / n | Accuracy (95% Wilson CI) | Verification rate | Calls | Mean tokens/item | Mean latency/item (s) |
|---|---:|---:|---:|---:|---:|---:|
| Direct | 345 / 360 | 95.83% [93.24%, 97.46%] | 0.00% | 360 | 39.60 | 0.761 |
| Full evidence verification | 358 / 360 | 99.44% [98.00%, 99.85%] | 100.00% | 720 | 103.88 | 1.495 |
| CoVe-style self-verification | 255 / 360 | 70.83% [65.94%, 75.29%] | 100.00% | 1080 | 168.81 | 2.190 |
| ConSC-Verify v1 (failed ablation) | 347 / 360 | 96.39% [93.92%, 97.88%] | 0.56% | 722 | 220.62 | 1.547 |
| Premise-aware selective verification (exploratory) | 360 / 360 | 100.00% [98.94%, 100.00%] | 4.17% | 375 | 42.37 | 0.797 |

## Independent replication split

| Method | Correct / n | Accuracy (95% Wilson CI) | Verification rate | Calls | Mean tokens/item | Mean latency/item (s) |
|---|---:|---:|---:|---:|---:|---:|
| Direct | 342 / 360 | 95.00% [92.24%, 96.81%] | 0.00% | 360 | 39.54 | 0.708 |
| Premise-aware selective verification (independent replication) | 360 / 360 | 100.00% [98.94%, 100.00%] | 5.00% | 378 | 42.78 | 0.741 |

## Scope

KG-FPQ YN contains false-premise questions. The premise-aware rule verifies an affirmative or unparseable Direct answer and preserves a clear negative answer. It is therefore a method for this false-premise setting, not evidence that the method mitigates every form of open-ended hallucination. ConSC-Verify v1 is retained as a negative ablation because its claim-surface risk score transferred poorly to short relational questions.
