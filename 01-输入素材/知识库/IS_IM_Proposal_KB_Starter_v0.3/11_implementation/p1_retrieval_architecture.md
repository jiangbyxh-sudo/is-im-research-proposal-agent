# P1 动态论文检索架构与配置边界

版本：`1.0.0-p1`  
范围：仅检索、规范化、去重、质量闸门、候选评分与可解释审计；不包含五方向聚类和开题 Prompt。

## 1. 本地优先路由

`01_taxonomy/generated/direction_profiles.json` 为 61 个方向提供版本化双语画像。每个画像包含中英文标签、近义表达、纳入/排除边界、Provider 查询、Topic 路由状态、期刊池、文献类型、回退查询和覆盖目标。生成源为 `11_implementation/build_direction_profiles.py`。

当前 OpenAlex Topic ID 没有经过人工校准，因此保留空数组并明确标注 `text_route_active; topic_ids_require_calibration`，不可伪造 Topic ID。

## 2. Provider 状态

| Provider | 当前角色 | 状态 | 配置 |
|---|---|---|---|
| OpenAlex | 主发现 | 已实现 | 匿名额度可用；`OPENALEX_API_KEY` 可在前端仅写入进程内存 |
| Crossref | DOI/期刊核验、白名单回退 | 已实现 | 可选 `PROPOSAL_CROSSREF_MAILTO`；回退默认每种语言 3 本、单次 6 秒 |
| Semantic Scholar | 摘要/引用补充 | 已实现连接器、默认关闭 | `PROPOSAL_ENABLE_OPTIONAL_PROVIDERS=1`；可选 `SEMANTIC_SCHOLAR_API_KEY` |
| DBLP | IS×CS/HCI/AI 补充 | 已实现连接器、默认关闭 | 同上，仅画像声明 DBLP 时调用 |
| CORE | OA 全文补充 | 未配置 | 需要 CORE API key 与字段映射验收 |
| Unpaywall | OA 位置补充 | 未配置 | 需要邮箱参数与 DOI enrichment 实现 |
| Scopus / Web of Science | 授权库补充 | 未配置 | 必须提供机构授权后接入 |
| CNKI / 万方 | 中文授权库补充 | 未配置 | 必须提供机构授权后接入 |

未配置来源只返回 `not_configured`，不得显示为已查询。

官方接口依据：

- OpenAlex API、认证与检索：<https://help.openalex.org/api/>、<https://help.openalex.org/api/authentication/>、<https://help.openalex.org/api/searching/>
- Semantic Scholar Graph API：<https://api.semanticscholar.org/api-docs/graphs>
- Crossref REST API：<https://api.crossref.org/swagger-ui/index.html>
- DBLP Publication Search API：<https://dblp.org/search/publ/api>
- CORE API：<https://files.core.ac.uk/services/api>
- Unpaywall API：<https://data.unpaywall.org/products/api>

## 3. 数据与质量流水线

1. Provider 原始记录先转为统一 `PaperRecord P1`，外部题名、摘要和元数据一律作为不可信数据隔离，不能作为指令执行。
2. 去重优先级为 DOI、Provider 外部 ID、规范化题名+年份+第一作者。模糊题名仅生成 `review_candidate`，不自动合并。
3. 字段冲突保留 `field_sources`；合并记录保留全部 `providers`。任何来源给出撤稿或关注表达时，完整性状态向风险侧提升。
4. 硬闸门检查撤稿/更正、题名/年份/来源缺失、时间窗、文献类型和本地合格期刊池。
5. `MetadataScore` 固定权重为语义相关 35%、词汇覆盖 15%、来源质量 15%、影响 10%、时效 10%、证据完整 10%、跨来源一致 5%。当前语义与影响分量仍是确定性代理，所有返回均标记 `uncalibrated`。
6. `<55` 拒绝、`55–69` 边界、`70–84` 候选、`≥85` 高候选。阈值完成人工 Precision@20 校准前不得宣称已验证。

Athlete A/B 检索与盲评 Judge 尚未实现，因此当前没有 `PaperMatchScore = 0.70 JudgeSemanticScore + 0.30 MetadataScore` 的产品能力声明。

## 4. 缓存与失败策略

- 同一进程内按画像版本、方向、细分问题、数量、年限和可选 Provider 状态缓存 15 分钟；API key 不进入缓存键或日志。
- OpenAlex 遇到 429 后停止继续扩展，避免把三条回退查询都打到限流来源。
- Crossref 回退有界，确保匿名来源故障时仍能在前端超时前返回诊断。
- 零结果原因限定为：`route_missing`、`provider_empty`、`rate_limited`、`quality_gate_too_strict`、`language_coverage_gap`、`query_too_narrow`。

