---
card_id: LOCAL-METHOD-EVENT-STUDY
status: source_mapped_local
aliases:
- 事件研究法
- 异常收益
- 事件窗
- 公告效应
- event study
- abnormal return
source_refs:
- METHOD-IACMR-EMPIRICAL-2018:ch20
review_rule: 关键方法细节必须继续查询本地原文块并返回PDF页码
---

# 资本市场事件研究

## 何时使用

评估公告、政策或组织事件对证券市场价值的短期影响。

## Agent执行要点

- 定义事件日、估计窗和事件窗
- 选择正常收益模型和基准
- 处理事件重叠、泄露和同期事件
- 检验异常收益及稳健性
- 说明市场有效性等核心假定

## 风险与停止信号

- 事件日不准确会污染估计
- 长事件窗更容易混入其他信息
- 市场反应不能自动解释具体组织机制

## 本地证据入口

- `METHOD-IACMR-EMPIRICAL-2018` / `ch20` / PDF页 615-643 / `03_sources/local_knowledge/books/METHOD-IACMR-EMPIRICAL-2018/chapters/ch20_event_study.md`

## 检索策略

先读取本卡；若需定义、假设、步骤、诊断或例证，使用 `local_retrieval.py` 在上述章节内检索。不得为节省上下文而跳过页码溯源。
