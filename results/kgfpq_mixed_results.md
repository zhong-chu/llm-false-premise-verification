# KG-FPQ TPQ/FPQ paired mixed evaluation

This evaluation uses 360 official false-premise questions (FPQ) and their 360 official true-premise counterparts (TPQ) from the independent KG-FPQ replication source records. The output-level PASEV gate verifies an affirmative or unparseable Direct answer only.

| Subset | Method | Correct / n | Accuracy | Verification rate |
|---|---|---:|---:|---:|
| FPQ | Direct | 342 / 360 | 95.00% | 0.00% |
| FPQ | PASEV | 360 / 360 | 100.00% | 5.00% |
| TPQ | Direct | 249 / 360 | 69.17% | 0.00% |
| TPQ | PASEV | 249 / 360 | 69.17% | 69.17% |
| Mixed | Direct | 591 / 720 | 82.08% | 0.00% |
| Mixed | PASEV | 609 / 720 | 84.58% | 37.08% |

PASEV corrected 18 false-premise errors and introduced no new errors. However, it did not correct the 111 true-premise cases that Direct incorrectly rejected with `NO`, because those answers do not meet its affirmative-answer routing condition. Therefore, PASEV is a lightweight mitigation for false-premise-induced false affirmations, not a general factuality mitigation method.
