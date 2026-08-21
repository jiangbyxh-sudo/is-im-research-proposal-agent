# IS/IM 论文开题辅助平台知识库 v0.4.1：交付概览

## 本次升级

v0.4 保留v0.3的44个外部来源本地化能力，并新增 `supplement_cn_cas` 规范化合并：运行时注册表扩展为179本期刊，CSSCI、北大核心、CAS与原FMS/UTD等级独立保存。

## 本地知识规模

| 项目 | 数量 |
|---|---:|
| 来源总数 | 46 |
| 创建者提供的全文书籍 | 2 |
| 外部来源知识卡 | 44 |
| 两本书原文块 | 1,600 |
| 外部来源知识块 | 269 |
| 统一检索块 | 1,869 |
| 期刊/名单结构化快照 | 4 |
| 方法主题卡 | 20 |

## 已本地化的内容

- UTD24、FMS 2025、AIS Premier 的名单快照与验证规则；
- Crossref、OpenAlex、Semantic Scholar、Unpaywall 的 API 字段、调用与核验流程；
- AIS eLibrary、CNKI、万方、维普、国家哲学社会科学文献中心的检索与去重流程；
- 写作、研究设计、报告规范与期刊投稿评价知识；
- IS 理论卡；
- 定量、定性、因果、SEM、实验、综述、贝叶斯、博弈论等方法卡；
- IM 的信息科学、信息行为、信息检索、知识管理、数据治理、NLP/LLM、网络科学和文献计量知识地图。

## 本地化边界

本包进行的是**知识抽取和结构化本地化**，不是整站镜像。

商业图书、付费论文、订阅数据库语料和受限资源没有被绕过权限或复制全文。它们以公开元数据、目录、公开摘要支持的信息、平台知识卡和停止规则进入本地库。两本由创建者提供的实证方法书仍作为全文本地来源。

## 默认运行方式

```text
研究方向路由
→ 本地主题卡
→ SQLite FTS 检索
→ 论文检索与元数据核验（仅动态部分）
→ 证据综合
```

只有以下情况访问外部服务：

- 查询当前最新论文；
- 验证 DOI、撤稿、更正或开放获取状态；
- 期刊名单/投稿规则已过期；
- 本地知识出现明确缺口；
- 取得授权后获取全文。

## 关键入口

- `README.md`
- `kb_manifest.yaml`
- `03_sources/source_registry.yaml`
- `03_sources/localization_status.md`
- `03_sources/external_localization_report.md`
- `03_sources/local_knowledge/external/catalog.yaml`
- `03_sources/local_knowledge/external/external_topic_router.yaml`
- `03_sources/local_knowledge/external/source_capture_manifest.yaml`
- `03_sources/local_knowledge/external/source_capture_manifest.csv`
- `03_sources/local_knowledge/index/all_chunks.jsonl`
- `03_sources/local_knowledge/index/local_fts.sqlite`
- `11_implementation/local_retrieval.py`
- `11_implementation/validate_external_kb.py`
- `11_implementation/validate_local_kb.py`
- `01_taxonomy/generated/research_direction_catalog.json`
- `08_schemas/research_request.schema.json`
- `11_implementation/paper_discovery_provider.py`
- `02_journals/supplements/supplement_cn_cas_merged.json`
- `11_implementation/research_synthesis_provider.py`

## 验证结果

- 外部来源：44
- 外部知识块：269
- 统一知识块：1,869
- 可选方向：75个原始主题合并为61个方向
- 本地图片：2008版67张、2018版113张，缺失0张
- SQLite 完整性：通过
- 路径与哈希校验：通过
- 中英文检索命中：通过
