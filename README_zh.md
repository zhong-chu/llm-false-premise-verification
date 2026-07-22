# 假前提感知的选择性证据验证：中文说明

[English README](README.md)

这是一个个人研究项目，研究 DeepSeek V4 Flash 在 KG-FPQ 假前提“是/否”问题中是否会错误肯定题目中的虚假关系，并比较不同验证策略的效果与调用成本。

## 代码在哪里？

所有可运行的代码都在 [`src/`](src/)：

- `evaluate_kgfpq.py`：直接回答基线；
- `run_premise_aware_from_direct.py`：PASEV 方法；
- `run_cove_kgfpq_from_direct.py`：CoVe-style 对比方法；
- `prepare_kgfpq_yn.py`：构造不重叠的测试划分；
- `summarize_kgfpq_comparison.py`：由逐题日志生成结果表。

根目录的英文 README 是面向研究者和老师的正式入口，包含环境配置、复现实验命令与主要结果；这里保留中文导航，方便阅读。

## 研究结论的边界

PASEV 的规则是：模型先回答；若回答 `YES` 或无法解析，才加入可信知识图谱三元组进行第二次验证；明确 `NO` 则保留。它在本项目的 FPQ 假前提题上能以较低验证率修正“错误肯定”，但不能修正真实命题被错误回答为 `NO` 的情况。因此，不能把它写成通用的大模型幻觉缓解方案。

完整设计与结果请见：

- [实验设计](docs/experiment_design.md)
- [主实验结果](results/kgfpq_results.md)
- [真假前提混合边界测试](results/kgfpq_mixed_results.md)
- [GAOKAO 早期探索说明](archive/gaokao_exploration/README.md)
