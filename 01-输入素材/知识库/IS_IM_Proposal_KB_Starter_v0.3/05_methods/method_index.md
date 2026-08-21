# 方法知识索引

## 本地已入库的管理实证方法

- 快速路由：`03_sources/local_knowledge/index/empirical_methods_quick_reference.md`
- 主题规则：`03_sources/local_knowledge/index/method_topic_router.yaml`
- 全文索引：`03_sources/local_knowledge/index/local_fts.sqlite`
- 查询脚本：`11_implementation/local_retrieval.py`
- 范式覆盖：`04_paradigms/local_source_map.yaml`

运行时先使用上述本地入口。下表中的外部资源只在本地覆盖不足时使用。

| 方法模块 | 入门入口 | 进阶入口 | 适用范式 |
|---|---|---|---|
| 统计与回归 | `METHOD-OPENINTRO` | 计量/领域论文 | 定量、实验、问卷 |
| 因果推断 | 回归与潜在结果基础 | `METHOD-MIXTAPE` + 现代方法原文 | 档案/面板/政策冲击 |
| CFA/SEM | `METHOD-LAVAAN` | 测量不变性、多层SEM、纵向SEM | 问卷 |
| 实验/A-B | 研究设计基础 | `METHOD-ONLINE-EXPERIMENTS` | 实验 |
| 定性 | `METHOD-THEMATIC` | `METHOD-GIOIA` + 过程理论 | 案例/归纳 |
| 贝叶斯 | 概率基础 | `METHOD-BDA`、`METHOD-PROBML` | 层级模型、AI/不确定性 |
| 博弈论 | `METHOD-YALE-GAME` | 信息经济学/机制设计教材与论文 | 分析建模 |
| IR/NLP | `IM-IR-BOOK` | `IM-SLP3` | IM、LLM/RAG、文本 |
| 网络/文献计量 | `IM-NETWORK` | `IM-BIBLIOMETRIX` + 方法论文 | 科学计量、社媒网络 |

## 知识卡建设规则

每个方法卡至少包含：适用问题、数据要求、核心假设、估计/分析步骤、诊断、稳健性、常见误用、结果解释、代码入口、IS/IM代表性论文。
