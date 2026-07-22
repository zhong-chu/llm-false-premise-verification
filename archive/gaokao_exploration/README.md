# GAOKAO-Bench early exploration

This folder documents the author's early-semester work on API evaluation, answer-option parsing, and per-item logging for GAOKAO-style multiple-choice questions. The reusable implementation is retained in `src/evaluate_mcq.py` and `src/metrics.py`.

The early results are not part of the final model ranking because the model versions, prompt variants, data cleaning, and parsing rules were not fully frozen across comparisons. They are included in the research report only as personal exploratory work that motivated the later reproducible protocol.

The repository intentionally does not redistribute complete exam questions, answer keys, or other potentially restricted source material. Users should obtain benchmark data from the original source and convert it to the documented JSONL format.
