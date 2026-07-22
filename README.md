# Premise-Aware Selective Evidence Verification

[中文说明](README_zh.md) · [Experiment design](docs/experiment_design.md) · [Primary results](results/kgfpq_results.md) · [TPQ/FPQ boundary evaluation](results/kgfpq_mixed_results.md) · [Citation](CITATION.cff)

This repository contains the code, frozen data splits, and aggregate results for an individual study of false-premise-induced factual errors in `deepseek-v4-flash`. The study uses the Yes/No portion of [KG-FPQ](https://aclanthology.org/2025.coling-main.698/) and compares direct answering, self-verification, full evidence verification, and a lightweight post-hoc routing policy.

## Method

**Premise-Aware Selective Evidence Verification (PASEV)** proceeds as follows:

1. Answer the original question once (`YES` or `NO`).
2. Keep a clear `NO` answer.
3. For a `YES` or unparseable answer, add the item’s trusted knowledge-graph triple and answer again.

In a false-premise question, an affirmative answer accepts the asserted external relation. PASEV therefore routes only affirmative answers to evidence verification.

> **Scope.** PASEV is a post-hoc policy for false-premise-induced false affirmations in KG-FPQ-style binary questions. It is not presented as a general solution to open-ended hallucination, nor as the first work on selective verification or premise verification.

## Main results

| Split | Method | Accuracy | Evidence verification rate | Mean tokens / item |
|---|---|---:|---:|---:|
| Primary FPQ (360) | Direct | 95.83% | 0.00% | 39.60 |
| Primary FPQ (360) | Full evidence verification | 99.44% | 100.00% | 103.88 |
| Primary FPQ (360) | CoVe-style self-verification | 70.83% | 100.00% | 168.81 |
| Primary FPQ (360) | PASEV | 100.00% | 4.17% | 42.37 |
| Independent FPQ replication (360) | Direct | 95.00% | 0.00% | 39.54 |
| Independent FPQ replication (360) | PASEV | 100.00% | 5.00% | 42.78 |

The official paired TPQ/FPQ evaluation prevents an overly broad interpretation: Direct and PASEV achieve 69.17% on true-premise questions, while PASEV improves false-premise accuracy from 95.00% to 100.00%. See [the full boundary evaluation](results/kgfpq_mixed_results.md).

The repository also retains two negative results: a claim-surface routing ablation (ConSC-Verify v1) transferred poorly to short relational questions, and the CoVe-style self-verification baseline introduced many new errors. They are reported to avoid selective reporting.

## Repository layout

```text
src/        Experiment code and command-line entry points
data/kgfpq/ Frozen KG-FPQ splits used in this study
docs/       Final experimental protocol and scope
results/    Public aggregate tables generated from private JSONL logs
archive/    Clearly separated early-semester exploratory work
configs/    Safe configuration template; no credentials
tests/      Offline checks for the frozen public data splits
```

The main code entry points are:

- `src/fetch_kgfpq.py`: download the original KG-FPQ JSON files;
- `src/prepare_kgfpq_yn.py`: construct disjoint FPQ splits;
- `src/evaluate_kgfpq.py`: run Direct evaluation;
- `src/run_premise_aware_from_direct.py`: run PASEV from Direct outputs;
- `src/run_cove_kgfpq_from_direct.py`: run the CoVe-style baseline;
- `src/summarize_kgfpq_comparison.py`: generate the public result table.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item configs\config.example.json configs\config.json
$env:DEEPSEEK_API_KEY="YOUR_API_KEY"
```

Do not commit `configs/config.json`, API keys, or raw JSONL model outputs. They are excluded by `.gitignore`.

## Validate the public splits

The following offline check verifies sample counts, domain/level balance, and the absence of source-record overlap between the primary and replication FPQ splits:

```powershell
python -m unittest discover -s tests -v
```

## Reproduce the main experiments

### 1. Download KG-FPQ and create disjoint FPQ splits

```powershell
python -m src.fetch_kgfpq --out-dir data/kgfpq/raw
python -m src.prepare_kgfpq_yn --raw-dir data/kgfpq/raw --out data/kgfpq/test_360.jsonl --per-stratum 20 --seed 20260820
python -m src.prepare_kgfpq_yn --raw-dir data/kgfpq/raw --out data/kgfpq/replication_360.jsonl --per-stratum 20 --seed 20260821 --exclude data/kgfpq/test_360.jsonl
```

### 2. Direct and PASEV evaluation

```powershell
python -m src.evaluate_kgfpq --config configs/config.json --input data/kgfpq/test_360.jsonl --out runs/kgfpq_direct_360.jsonl --method direct
python -m src.run_premise_aware_from_direct --config configs/config.json --input runs/kgfpq_direct_360.jsonl --out runs/kgfpq_premise_aware_360.jsonl
```

Append `--resume` to resume an interrupted run. For the independent replication, replace both occurrences of `test_360` with `replication_360`.

### 3. TPQ/FPQ paired boundary evaluation

```powershell
python -m src.prepare_kgfpq_mixed --false-input data/kgfpq/replication_360.jsonl --raw-dir data/kgfpq/raw --out data/kgfpq/replication_mixed_720.jsonl --seed 20260822
python -m src.evaluate_kgfpq --config configs/config.json --input data/kgfpq/replication_mixed_720.jsonl --out runs/kgfpq_mixed_direct_720.jsonl --method direct
python -m src.run_premise_aware_from_direct --config configs/config.json --input runs/kgfpq_mixed_direct_720.jsonl --out runs/kgfpq_mixed_premise_aware_720.jsonl
```

### 4. Regenerate the primary result table

```powershell
python -m src.summarize_kgfpq_comparison --primary-direct runs/kgfpq_direct_360.jsonl --primary-full runs/kgfpq_full_evidence_360.jsonl --primary-cove runs/kgfpq_cove_360.jsonl --primary-consc-v1 runs/kgfpq_consc_selective_360.jsonl --primary-pav runs/kgfpq_premise_aware_360.jsonl --replication-direct runs/kgfpq_replication_direct_360.jsonl --replication-pav runs/kgfpq_replication_premise_aware_360.jsonl --json-out results/kgfpq_results.json --markdown-out results/kgfpq_results.md
```

## Early exploration

The repository preserves a small, clearly separated record of the author’s earlier GAOKAO-Bench, FactBench, annotation, and retrieval explorations. They are not included in the final ranking because their model versions, prompts, data cleaning, and parsing rules were not frozen. See [archive/gaokao_exploration](archive/gaokao_exploration/README.md) and [archive/early_exploration_code](archive/early_exploration_code/README.md). Full exam questions and answer keys are intentionally not redistributed.

## References

- Zhu, Y., Xiao, J., Wang, Y., & Sang, J. (2025). *KG-FPQ: Evaluating Factuality Hallucination in LLMs with Knowledge Graph-based False Premise Questions*. COLING 2025.
- Dhuliawala, S., Komeili, M., Xu, J., et al. (2024). *Chain-of-Verification Reduces Hallucination in Large Language Models*. Findings of ACL 2024.

## License

The code is released under the [MIT License](LICENSE). Please cite this repository using [CITATION.cff](CITATION.cff) if you build on the released implementation or frozen splits.
