# IS/IM 论文开题辅助平台知识库 v0.4.1

本目录是面向 IS（Information Systems）与 IM（Information Management）社科研究者的开题辅助知识库。它不是简单的链接清单，也不是无差别堆放 PDF，而是一个可审计、可扩展、低算力、**本地优先**的 Agent/RAG 知识层。

## 1. v0.4 的核心变化

v0.2 仅对创建者提供的两本《组织与管理研究的实证方法》进行了全文本地化。v0.3 进一步处理了原 `03_sources/source_registry.yaml` 中全部 44 个外部来源：

- 每个来源均生成本地结构化知识卡；
- 按来源类型生成期刊规则快照、API 操作卡、数据库检索卡、写作卡、理论卡、方法卡或 IM 领域知识卡；
- 所有知识卡进入统一 JSONL 与 SQLite FTS5 检索索引；
- Agent 启动任务时禁止遍历外部 URL；
- 只有查询最新论文、最新元数据、撤稿/更正状态、过期规则或明确知识缺口时，才允许访问外部服务。

当前没有任何外部来源停留在 `pointer_only` 或 `summary_card_only` 状态。

v0.4 进一步合并创建者提供的 `supplement_cn_cas`：CSSCI 2025–2026来源刊、CSSCI扩展版、北大核心2023及CAS 2025 SSCI 1/2区均以独立字段保存。规范化结果位于 `02_journals/supplements/supplement_cn_cas_merged.json`，运行时注册表包含179本期刊。中文默认资格为FMS T1/T2、CSSCI来源刊或北大核心；CAS-only记录不改变默认英文UTD/FMS范围。

## 2. 当前本地知识规模

| 项目 | 数量 |
|---|---:|
| 来源总数 | 46 |
| 创建者提供的全文书籍 | 2 |
| 已本地化外部来源 | 44 |
| 两本书原文检索块 | 1,600 |
| 外部来源知识块 | 269 |
| 统一检索块 | 1,869 |
| 方法主题卡 | 20 |
| 期刊/名单结构化快照 | 4 |

统一索引位于：

```text
03_sources/local_knowledge/index/all_chunks.jsonl
03_sources/local_knowledge/index/local_fts.sqlite
```

可选研究方向目录由期刊知识库自动编译：共提取75个原始主题，合并为61个方向，按原知识库章节分组并保留跨组来源：

```text
01_taxonomy/generated/research_direction_catalog.json
```

## 3. “本地化”具体指什么

本包采用**知识抽取与结构化本地化**，不是整站镜像。

### 3.1 可以直接本地使用的内容

- UTD24、FMS 2025、AIS Premier 的版本化名单与验证规则；
- Crossref、OpenAlex、Semantic Scholar、Unpaywall 的字段、调用顺序、核验流程、错误边界与缓存规则；
- AIS eLibrary、CNKI、万方、维普、国家哲学社会科学文献中心的检索、导出、去重与来源核验流程；
- 研究问题、论证、研究设计、报告规范、MISQ/ISR 投稿评价要点；
- Gregor 理论类型、设计科学、TAM、UTAUT、TTF 等 IS 理论卡；
- 统计、因果推断、SEM、实验、质化研究、系统综述、贝叶斯、博弈论、在线实验等方法卡；
- 信息科学、信息行为、信息检索、知识管理、数据治理、NLP/LLM、网络科学与文献计量等 IM 知识地图。

### 3.2 不会非法镜像的内容

- 商业图书全文；
- 付费或订阅论文全文；
- CNKI、万方、维普等数据库的整库语料；
- 需要账号、机构权限或受保护的教师资源；
- 权利不明确的网页全文或摘要批量复制。

对于这些来源，本地保存的是官方公开元数据、公开目录、公开摘要支持的信息、平台可执行知识卡和停止规则。若某个结论需要未本地化且无法合法取得的内容，必须触发 `KB_SOURCE_CONTENT_MISSING`，不得根据题名自行补写。

## 4. 本地优先运行顺序

```text
用户研究方向
  ↓
01_taxonomy/research_direction_router.yaml
  ↓
03_sources/local_knowledge/external/external_topic_router.yaml
或 03_sources/local_knowledge/index/method_topic_router.yaml
  ↓
本地来源知识卡
  ↓
SQLite FTS5 本地检索
  ↓
只有在需要最新论文/元数据/完整性核验时才调用外部服务
  ↓
新获得的合法资料按许可缓存、登记、版本化
```

Agent 不得在任务启动时逐个访问 `source_registry.yaml` 中的 URL。

## 5. 目录说明

- `00_governance/`：范围、停止规则、来源验证、版权与本地化政策。
- `01_taxonomy/`：研究方向、关键词扩展、研究空白与创新分类。
- `02_journals/`：IS/IM 期刊库、中文期刊目录、期刊池与记录结构。
- `03_sources/`：来源注册表、本地化状态、外部知识卡、两本书全文、索引与审计记录。
- `04_paradigms/`：九类研究范式。
- `05_methods/`：方法知识入口。
- `06_theories/`：理论索引与模板。
- `07_workflows/`：检索、证据综合、空白与创新、开题生成、写作指导流程。
- `08_schemas/`：论文、证据、空白、创新、用户选择与开题上下文的数据契约。
- `09_agent_contract/`：Agent 系统契约、门禁与检索规则。
- `10_templates/`：论文卡、理论卡、方法卡等模板。
- `11_implementation/`：本地检索、构建、验证与低算力架构。

## 6. 外部来源本地层的关键文件

```text
03_sources/source_registry.yaml
03_sources/localization_status.yaml
03_sources/external_localization_report.md

03_sources/local_knowledge/external/cards/
03_sources/local_knowledge/external/structured/
03_sources/local_knowledge/external/catalog.yaml
03_sources/local_knowledge/external/external_topic_router.yaml
03_sources/local_knowledge/external/source_capture_manifest.yaml
03_sources/local_knowledge/external/source_capture_manifest.csv

03_sources/local_knowledge/index/external_chunks.jsonl
03_sources/local_knowledge/index/all_chunks.jsonl
03_sources/local_knowledge/index/local_fts.sqlite
```

`source_capture_manifest` 记录每个来源的本地卡路径、来源类型、处理方式、许可边界、刷新策略和 SHA-256 哈希。

## 7. 本地检索

```bash
python 11_implementation/local_retrieval.py "研究问题 理论贡献" --limit 8

python 11_implementation/local_retrieval.py   "difference in differences parallel trends"   --limit 8

python 11_implementation/local_retrieval.py   "信息需求 信息搜寻 信息回避"   --limit 8

python 11_implementation/local_retrieval.py   "结构方程模型 测量效度"   --resource-id METHOD-IACMR-EMPIRICAL-2018   --limit 8

python 11_implementation/local_retrieval.py --stats
```

检索器支持：

- 中英文关键词；
- 多词严格匹配优先、宽松召回兜底；
- 来源 ID、章节 ID、来源优先级与标签过滤；
- 标题、小节、标签、正文的字段加权；
- JSON 输出；
- 页码或本地知识卡定位。

## 8. 两本创建者提供的全文来源

以下两本书保留全文、章节拆分、页码锚点、原文块和本地 FTS 索引：

```text
METHOD-IACMR-EMPIRICAL-2008
METHOD-IACMR-EMPIRICAL-2018
```

运行时默认优先使用 2018 第三版；2008 版作为历史与补充来源。公开部署时，应限制整章、整书和批量逐字导出，只向最终用户提供必要的短证据片段、页码和平台生成的结构化解释。

两本书 Markdown 引用的图片已经完整入库：2008版67张、2018第三版113张。图片保存在各自书籍目录的 `images/` 下，并继续遵守私人研究副本的访问与导出限制。

## 9. 动态信息仍需现场查询

以下内容不能靠一次抓取永久替代：

- 用户指定主题的最新中文与英文论文；
- DOI、作者、期刊、年份等当前元数据；
- 撤稿、更正、表达关切与版本关系；
- 引用次数、开放获取位置和数据库收录状态；
- 更新后的期刊目录、投稿规则与软件版本。

本地化的目标是让 Agent 不再重复学习“如何检索、如何验证、如何写、如何选择方法”，而不是冻结不断变化的论文世界。

## 10. 验证

运行：

```bash
python 11_implementation/validate_external_kb.py
python 11_implementation/validate_local_kb.py
```

验证范围包括：

- YAML、JSON、JSONL 语法；
- 44 个外部来源卡与路径覆盖；
- 1,869 个检索块与 SQLite 数量一致性；
- SQLite `PRAGMA integrity_check`；
- 内容哈希；
- 整包 checksums；
- 中英文检索命中。

## 11. 平台必须继续执行的门禁

即使知识已本地化，以下情况仍必须停止：

- 研究方向不属于 IS/IM；
- 论文来源或期刊等级无法验证；
- 本地证据不足以支持研究现状、空白或因果判断；
- 研究范式卡缺失或与问题不匹配；
- 用户尚未明确选择研究空白和创新点；
- 需要受限内容但未取得合法访问权限；
- 来源版本过期且无法核验。

本知识库降低重复检索和上下文成本，但不会取消证据核验与学术诚信要求。
