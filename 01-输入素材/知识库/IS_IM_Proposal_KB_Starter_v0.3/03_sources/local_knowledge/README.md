# 本地实证方法知识层

该目录用于回答稳定的研究设计与实证方法问题，默认不访问互联网。

## 入口

- `index/method_topic_router.yaml`：方法主题和别名路由；
- `cards/`：20张低成本方法卡；
- `index/local_fts.sqlite`：1,869个统一知识块的SQLite FTS5索引，其中1,600个来自两本书、269个来自外部知识卡；
- `index/chunks.jsonl`：可迁移到其他检索系统的原文块；
- `books/*/chapter_index.yaml`：章节、PDF页、原始行号、标签和路径；
- `index/missing_assets.jsonl`：图表资产缺失审计清单；当前为空。

## 命令行检索

```bash
python 11_implementation/local_retrieval.py "研究问题 现象驱动" --limit 8
python 11_implementation/local_retrieval.py "结构方程模型 拟合指数" --resource-id METHOD-IACMR-EMPIRICAL-2018
python 11_implementation/local_retrieval.py "共同方法偏差" --chapter-id ch07 --json
```

返回结果包含 `resource_id`、`chapter_id`、PDF页码、本地路径与原文片段，可直接进入证据链。

## Agent策略

1. 先匹配主题卡；
2. 方法卡足够时，不加载原文；
3. 需要定义、步骤、假设、诊断或边界时，只检索相关章节的少量chunk；
4. 2018第三版优先，2008版补充；
5. `asset_missing=true` 时不得重建图表或公式；当前两本书引用的180张图片均已入库；
6. 只有本地覆盖缺失或时效内容过期时，才使用外部检索。

## 权利与部署

两本全文是创建者提供的私人研究副本。平台可以内部检索，但未确认再分发许可前，不应向最终用户提供整章、整书或批量逐字导出。
