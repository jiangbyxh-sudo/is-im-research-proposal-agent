# P1 动态论文检索架构与配置边界

版本：`1.1.0-p1-retrieval`
范围：仅检索、规范化、去重、质量闸门、候选评分与可解释审计；不包含五方向聚类和开题 Prompt。

## 1. 本地优先路由

`01_taxonomy/generated/direction_profiles.json` 为61个方向提供版本化双语画像。生成源不再把业务规则写死在脚本中，而是由 `direction_profile_base.yaml`、`direction_profile_overrides.yaml`、Topic/Source注册表和方向目录编译。每个画像包含核心现象、必要情境、负面边界、中英文精确/召回查询、方向级来源分层、已审核OpenAlex路由、文献类型和覆盖目标。

Topic搜索候选保存名称、描述、Field/Subfield、样例论文和审核状态。未经审核的候选保持 `pending_review`，不进入Provider filter；禁止自动采用第一条。Source只在ISSN唯一解析时自动批准，歧义项保持待复核。

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

1. DirectionProfile先编译为可重放QueryPlan，按A Topic+Tier A、B精确短语+Tier A/B、C Topic/facet扩召、D可选Seed扩展、E中文专用Lane执行；日期、文献类型和已审核Topic/Source进入OpenAlex filter，支持cursor分页。
2. Provider原始记录转为统一 `PaperRecord P1`，外部题名、摘要和元数据一律作为不可信数据隔离，不能作为指令执行。
3. 去重优先级为DOI、Provider外部ID、规范化题名+年份+第一作者。模糊题名仅生成 `review_candidate`，不自动合并。
4. 所有来源经同一候选决策函数得到且只得到一个终态：`gate_reject / rank_reject / boundary / eligible / manual_review`；去重数必须等于五终态之和。
5. 完整性闸门、方向边界、来源质量、来源方向适配和内容相关性分开判断。Unknown来源不得自动进入正式候选。
6. Hybrid Reranker权重为Topic路线30%、透明多语种相似30%、facet覆盖15%、来源方向适配12%、证据5%、时效4%、归一影响4%。无embedding时明确标记为确定性加权重合，不冒充embedding。
7. 固定55/70/85准入阈值已移除；Checkpoint决定是否可排序，Reranker决定Top-K，最低相关性底线决定宁缺毋滥。引用量不主导相关性。
8. DOI/OA landing page与PDF/全文分开；只有核验到PDF URL时才标记 `verified_fulltext_available`。

Athlete/Judge只保留为Top-N低置信边界的可选精排接口，不是P1主链路和强制依赖。当前未启用，因此不得声明已有多模型裁判能力。

## 4. 缓存与失败策略

- 同一进程内按画像版本、方向、细分问题、数量、年限和可选 Provider 状态缓存 15 分钟；API key 不进入缓存键或日志。
- OpenAlex 遇到 429 后停止继续扩展，避免把三条回退查询都打到限流来源。
- Crossref 回退有界，确保匿名来源故障时仍能在前端超时前返回诊断。
- 零结果原因限定为：`route_missing`、`provider_empty`、`rate_limited`、`quality_gate_too_strict`、`language_coverage_gap`、`query_too_narrow`。
