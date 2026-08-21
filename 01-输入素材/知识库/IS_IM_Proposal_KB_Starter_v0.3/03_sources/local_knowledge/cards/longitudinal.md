---
card_id: LOCAL-METHOD-LONGITUDINAL
status: source_mapped_local
aliases:
- 纵向研究
- 固定效应
- 随机效应
- 动态
- longitudinal
- fixed effects
- random effects
source_refs:
- METHOD-IACMR-EMPIRICAL-2018:ch18
- METHOD-IACMR-EMPIRICAL-2018:ch21
review_rule: 关键方法细节必须继续查询本地原文块并返回PDF页码
---

# 纵向、面板与动态研究

## 何时使用

研究变化、先后顺序、个体/组织内效应或动态过程。

## Agent执行要点

- 明确时间单位、波次和理论滞后
- 区分个体内与个体间变异
- 依据误差与未观测异质性假设选择固定/随机效应
- 处理缺失、流失、序列相关和时间趋势
- 限制对动态因果的表述

## 风险与停止信号

- 只有两个时间点时动态机制证据有限
- 固定效应不能估计时间不变变量的直接效应
- 任意选择滞后长度会产生研究者自由度

## 本地证据入口

- `METHOD-IACMR-EMPIRICAL-2018` / `ch18` / PDF页 576-593 / `03_sources/local_knowledge/books/METHOD-IACMR-EMPIRICAL-2018/chapters/ch18_longitudinal_panel_analysis.md`
- `METHOD-IACMR-EMPIRICAL-2018` / `ch21` / PDF页 644-681 / `03_sources/local_knowledge/books/METHOD-IACMR-EMPIRICAL-2018/chapters/ch21_diary_and_experience_sampling.md`

## 检索策略

先读取本卡；若需定义、假设、步骤、诊断或例证，使用 `local_retrieval.py` 在上述章节内检索。不得为节省上下文而跳过页码溯源。
