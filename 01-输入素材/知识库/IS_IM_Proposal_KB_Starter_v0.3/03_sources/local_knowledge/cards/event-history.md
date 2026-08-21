---
card_id: LOCAL-METHOD-EVENT-HISTORY
status: source_mapped_local
aliases:
- 事件历史
- 生存分析
- 风险率
- 删失
- Cox
- event history
- survival analysis
- hazard
source_refs:
- METHOD-IACMR-EMPIRICAL-2018:ch19
review_rule: 关键方法细节必须继续查询本地原文块并返回PDF页码
---

# 事件历史与生存分析

## 何时使用

因变量是某事件是否以及何时发生，如采用、退出、失败、晋升或合作终止。

## Agent执行要点

- 定义客体、事件、起始时间和风险集
- 处理右删失和时间变化协变量
- 选择离散/连续时间与比例风险等模型
- 检验核心模型假设
- 报告时间尺度和事件重复规则

## 风险与停止信号

- 只分析已发生事件会产生选择偏差
- 不同时间起点不可随意混用
- 比例风险假设不满足时需调整模型

## 本地证据入口

- `METHOD-IACMR-EMPIRICAL-2018` / `ch19` / PDF页 594-614 / `03_sources/local_knowledge/books/METHOD-IACMR-EMPIRICAL-2018/chapters/ch19_event_history_analysis.md`

## 检索策略

先读取本卡；若需定义、假设、步骤、诊断或例证，使用 `local_retrieval.py` 在上述章节内检索。不得为节省上下文而跳过页码溯源。
