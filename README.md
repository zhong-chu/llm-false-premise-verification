# 假前提感知的选择性证据验证

[English README](README_EN.md) · [实验设计](docs/experiment_design.md) · [主实验结果](results/kgfpq_results.md) · [TPQ/FPQ 边界测试](results/kgfpq_mixed_results.md)

本仓库包含一项个人研究的代码、冻结数据划分与汇总结果。研究使用 `deepseek-v4-flash`，在 [KG-FPQ](https://aclanthology.org/2025.coling-main.698/) 的“是/否”假前提问题上比较直接回答、自验证、全量证据验证和轻量级后验选择性验证策略。

## 方法

**Premise-Aware Selective Evidence Verification（PASEV，假前提感知的选择性证据验证）** 流程如下：

1. 对原问题回答一次（仅 `YES` 或 `NO`）。
2. 若为明确的 `NO`，保留原答案。
3. 若为 `YES` 或答案无法解析，加入该题可信的知识图谱三元组后再次回答。

在假前提问题中，肯定回答意味着认可题目所断言的外部关系，因此 PASEV 只将肯定回答路由到证据验证。

> **适用范围。** PASEV 是面向 KG-FPQ 风格二元假前提问题中“错误肯定”的后验策略。它不是开放式幻觉的通用解决方案，也不主张首创选择性验证或前提验证。

## 主要结果

| 划分 | 方法 | 准确率 | 证据验证率 | 平均 token/题 |
|---|---|---:|---:|---:|
| 主 FPQ 集（360） | Direct | 95.83% | 0.00% | 39.60 |
| 主 FPQ 集（360） | 全量证据验证 | 99.44% | 100.00% | 103.88 |
| 主 FPQ 集（360） | CoVe-style 自验证 | 70.83% | 100.00% | 168.81 |
| 主 FPQ 集（360） | PASEV | 100.00% | 4.17% | 42.37 |
| 独立 FPQ 复现集（360） | Direct | 95.00% | 0.00% | 39.54 |
| 独立 FPQ 复现集（360） | PASEV | 100.00% | 5.00% | 42.78 |

官方配对 TPQ/FPQ 测试避免了过度解读：Direct 与 PASEV 在真实前提问题上的准确率均为 69.17%，而 PASEV 将假前提问题的准确率从 95.00% 提升到 100.00%。详见[完整边界测试](results/kgfpq_mixed_results.md)。

仓库还保留两项负结果：基于断言表面的 ConSC-Verify v1 路由消融无法迁移到短关系问题；CoVe-style 自验证引入了大量新错误。保留这些结果是为了避免选择性报告。

## 仓库结构

```text
src/        实验代码与命令行入口
data/kgfpq/ 本研究使用的冻结 KG-FPQ 划分
docs/       最终实验方案与适用范围说明
results/    由私有 JSONL 日志生成的公开汇总表
configs/    安全的配置模板，不含密钥
```

主要代码入口如下：

- `src/fetch_kgfpq.py`：下载原始 KG-FPQ JSON 文件；
- `src/prepare_kgfpq_yn.py`：构建不重叠的 FPQ 划分；
- `src/evaluate_kgfpq.py`：运行 Direct 评测；
- `src/run_premise_aware_from_direct.py`：基于 Direct 输出运行 PASEV；
- `src/run_cove_kgfpq_from_direct.py`：运行 CoVe-style 对比；
- `src/summarize_kgfpq_comparison.py`：生成公开结果表。

## 环境配置

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
Copy-Item configs\config.example.json configs\config.json
$env:DEEPSEEK_API_KEY="YOUR_API_KEY"
```

不要提交 `configs/config.json`、API 密钥或逐题原始 JSONL 模型输出；它们已被 `.gitignore` 排除。

## 复现主要实验

### 1. 下载 KG-FPQ 并构建不重叠的 FPQ 划分

```powershell
python -m src.fetch_kgfpq --out-dir data/kgfpq/raw
python -m src.prepare_kgfpq_yn --raw-dir data/kgfpq/raw --out data/kgfpq/test_360.jsonl --per-stratum 20 --seed 20260820
python -m src.prepare_kgfpq_yn --raw-dir data/kgfpq/raw --out data/kgfpq/replication_360.jsonl --per-stratum 20 --seed 20260821 --exclude data/kgfpq/test_360.jsonl
```

### 2. Direct 与 PASEV 评测

```powershell
python -m src.evaluate_kgfpq --config configs/config.json --input data/kgfpq/test_360.jsonl --out runs/kgfpq_direct_360.jsonl --method direct
python -m src.run_premise_aware_from_direct --config configs/config.json --input runs/kgfpq_direct_360.jsonl --out runs/kgfpq_premise_aware_360.jsonl
```

如运行中断，在命令末尾加入 `--resume`。独立复现时，将两处 `test_360` 替换为 `replication_360`。

### 3. TPQ/FPQ 配对边界测试

```powershell
python -m src.prepare_kgfpq_mixed --false-input data/kgfpq/replication_360.jsonl --raw-dir data/kgfpq/raw --out data/kgfpq/replication_mixed_720.jsonl --seed 20260822
python -m src.evaluate_kgfpq --config configs/config.json --input data/kgfpq/replication_mixed_720.jsonl --out runs/kgfpq_mixed_direct_720.jsonl --method direct
python -m src.run_premise_aware_from_direct --config configs/config.json --input runs/kgfpq_mixed_direct_720.jsonl --out runs/kgfpq_mixed_premise_aware_720.jsonl
```

### 4. 重新生成主结果表

```powershell
python -m src.summarize_kgfpq_comparison --primary-direct runs/kgfpq_direct_360.jsonl --primary-full runs/kgfpq_full_evidence_360.jsonl --primary-cove runs/kgfpq_cove_360.jsonl --primary-consc-v1 runs/kgfpq_consc_selective_360.jsonl --primary-pav runs/kgfpq_premise_aware_360.jsonl --replication-direct runs/kgfpq_replication_direct_360.jsonl --replication-pav runs/kgfpq_replication_premise_aware_360.jsonl --json-out results/kgfpq_results.json --markdown-out results/kgfpq_results.md
```

## 参考文献

- Zhu, Y., Xiao, J., Wang, Y., & Sang, J. (2025). *KG-FPQ: Evaluating Factuality Hallucination in LLMs with Knowledge Graph-based False Premise Questions*. COLING 2025.
- Dhuliawala, S., Komeili, M., Xu, J., et al. (2024). *Chain-of-Verification Reduces Hallucination in Large Language Models*. Findings of ACL 2024.
