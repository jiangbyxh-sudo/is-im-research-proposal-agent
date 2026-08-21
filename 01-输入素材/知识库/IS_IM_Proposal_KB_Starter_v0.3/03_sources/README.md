# 03_sources：来源与本地知识层

`source_registry.yaml` 现在承担**来源治理和溯源**，不再是 Agent 启动时逐条访问的URL清单。

## 运行时顺序

1. `local_knowledge/index/method_topic_router.yaml`：按方法主题精确路由；
2. `local_knowledge/cards/`：读取低成本结构化知识卡；
3. `local_knowledge/index/local_fts.sqlite`：需要细节时检索本地原文块；
4. `source_registry.yaml`：核对来源身份、版本与本地化状态；
5. 只有本地缺失、时效内容过期或图表资产缺失时，才访问外部来源。

## 状态含义

- `fulltext_chaptered_chunked_indexed`：全文已本地化、章节化、切块并建立全文索引；
- `structured_snapshot`：稳定规则已保存为本地结构化快照，只需定期刷新；
- `summary_card_only`：已有本地摘要卡，但详细内容仍可能需要授权全文；
- `pointer_only`：仅保留来源指针，必须显式视为知识缺口，不能在启动时自动抓取。

## 两本实证方法书

- 2018第三版是默认主来源；
- 2008版用于版本对照以及中国管理理论建构、组织社会资本、跨文化研究和发表历程等补充专题；
- 原始Markdown为OCR整理文本，仍可能有识别噪声；上传中未包含Markdown引用的 `images/` 资产；
- 公开部署时不向最终用户提供整书或整章导出，只提供知识卡和必要的短证据片段。

本地化总表见 `localization_status.yaml`；人工可读版见 `localization_status.md`。
