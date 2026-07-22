# 假前提感知的选择性证据验证

本仓库对应个人研究报告《大语言模型事实性错误评测与选择性验证缓解方法研究》。项目使用 DeepSeek V4 Flash 的黑盒 API，研究模型在 **KG-FPQ YN 假前提是非问答** 中是否会顺从错误前提，并实现一种只对高风险肯定回答调用外部证据的缓解方法。

## 核心方法

**Premise-Aware Selective Evidence Verification（PASEV）** 的流程如下：

1. 对问题进行 Direct 回答（仅 `YES` / `NO`）；
2. 若 Direct 回答为 `NO`，保留该回答；
3. 若 Direct 回答为 `YES` 或无法解析，提供该题已知的真实知识图谱三元组并再次验证；
4. 输出验证后的答案。

该门控规则的含义是：在假前提问答中，`YES` 会认可题目所断言的外部实体关系，因而应优先核验。它仅针对本任务场景，不应被表述为对所有开放式幻觉都有效的通用方案。

## 主要结果

完整、可重新生成的汇总表见 [results/kgfpq_results.md](results/kgfpq_results.md)。

真假前提混合验证见 [results/kgfpq_mixed_results.md](results/kgfpq_mixed_results.md)。该验证表明 PASEV 仅能修正“假前提被错误肯定”，不能修正真实命题被错误否定，因此其适用范围必须限定为 FPQ 场景。

| 划分 | 方法 | 正确率 | 证据验证率 | 平均 token/题 |
|---|---|---:|---:|---:|
| 探索集（360 题） | Direct | 95.83% | 0.00% | 39.60 |
| 探索集（360 题） | 全量证据验证 | 99.44% | 100.00% | 103.88 |
| 探索集（360 题） | CoVe-style 自验证 | 70.83% | 100.00% | 168.81 |
| 探索集（360 题） | PASEV | 100.00% | 4.17% | 42.37 |
| 独立复现集（360 题） | Direct | 95.00% | 0.00% | 39.54 |
| 独立复现集（360 题） | PASEV | 100.00% | 5.00% | 42.78 |

在官方 TPQ/FPQ 配对的 720 题混合集中，Direct 为 82.08%，PASEV 为 84.58%。增益全部来自 FPQ 子集（95.00% 至 100.00%）；TPQ 子集均为 69.17%。

独立复现集采用种子 `20260821`，并排除了探索集使用过的全部源知识图谱记录。PASEV 的规则在探索结果出现后固定，未在复现集上继续调整。

## 重要负结果

早期的 **ConSC-Verify v1（Claim-Sensitive Calibrated Verification）** 使用一次额外的大模型调用，按回答中的日期、实体、数值等“事实断言表面”评分并选择是否验证。它在短关系型 KG-FPQ 问题上迁移失败：仅验证 2/360 题、准确率 96.39%，且平均 token/题为 220.62，高于全量证据验证。该消融结果被保留，避免选择性报告。

另实现了 CoVe-style 自验证基线：对原关系进行独立核验，再用初答与核验结果生成最终答案。它修正了 12 个 Direct 错误，却引入 102 个新错误，最终准确率为 70.83%。这说明在该任务中，不带外部证据的多轮自验证会放大不稳定性，不能替代可追溯证据验证。

## 环境配置

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item configs\config.example.json configs\config.json
$env:DEEPSEEK_API_KEY="你的密钥"
```

`configs/config.json` 和 API 密钥均不应提交到 GitHub。

## 复现实验

### 1. 下载并构建 KG-FPQ 划分

```powershell
python -m src.fetch_kgfpq --out-dir data/kgfpq/raw
python -m src.prepare_kgfpq_yn --raw-dir data/kgfpq/raw --out data/kgfpq/test_360.jsonl --per-stratum 20 --seed 20260820
python -m src.prepare_kgfpq_yn --raw-dir data/kgfpq/raw --out data/kgfpq/replication_360.jsonl --per-stratum 20 --seed 20260821 --exclude data/kgfpq/test_360.jsonl
```

### 2. Direct 与 PASEV

```powershell
python -m src.evaluate_kgfpq --config configs/config.json --input data/kgfpq/test_360.jsonl --out runs/kgfpq_direct_360.jsonl --method direct
python -m src.run_premise_aware_from_direct --config configs/config.json --input runs/kgfpq_direct_360.jsonl --out runs/kgfpq_premise_aware_360.jsonl
```

如网络中断，在第二条命令末尾加入 `--resume`。独立复现时，将两处文件名替换为 `replication_360` 即可。

### 3. 生成汇总表

```powershell
python -m src.summarize_kgfpq_comparison --primary-direct runs/kgfpq_direct_360.jsonl --primary-full runs/kgfpq_full_evidence_360.jsonl --primary-cove runs/kgfpq_cove_360.jsonl --primary-consc-v1 runs/kgfpq_consc_selective_360.jsonl --primary-pav runs/kgfpq_premise_aware_360.jsonl --replication-direct runs/kgfpq_replication_direct_360.jsonl --replication-pav runs/kgfpq_replication_premise_aware_360.jsonl --json-out results/kgfpq_results.json --markdown-out results/kgfpq_results.md
```

## 目录说明

- `src/`：数据构建、模型调用、选择性验证与汇总代码；
- `data/kgfpq/`：冻结的实验划分；原始数据可按上述命令下载；
- `runs/`：逐题运行日志（默认不提交，可能含 API 响应）；
- `results/`：由逐题日志生成、可公开的汇总结果；
- `docs/`：实验方案和研究记录。

## 引用

- Zhu Y, Xiao J, Wang Y, Sang J. *KG-FPQ: Evaluating Factuality Hallucination in LLMs with Knowledge Graph-based False Premise Questions*. COLING, 2025.
- Dhuliawala S, Komeili M, Xu J, et al. *Chain-of-Verification Reduces Hallucination in Large Language Models*. Findings of ACL, 2024.
