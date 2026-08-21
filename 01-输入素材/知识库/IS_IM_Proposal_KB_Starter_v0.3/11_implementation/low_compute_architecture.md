# 低算力知识库实现架构

## 1. 推荐组件

不依赖特定云厂商的最小组合：

- **结构化库：**SQLite（单机MVP）或 PostgreSQL（多人/生产）；
- **全文与附件：**本地对象存储、S3兼容存储或学校授权系统；
- **关键词检索：**SQLite FTS5 / PostgreSQL Full Text Search / OpenSearch；
- **向量检索：**只对知识卡和论文证据摘要建立向量，可使用 pgvector 或轻量本地索引；
- **版本管理：**Git；
- **文献管理：**Zotero作为人工采集和引用出口，而非运行时唯一数据库。

## 2. 建议数据库表

### 规则与目录

- `journal_registry`
- `journal_rank_versions`
- `journal_pool_membership`
- `kb_resources`
- `paradigms`
- `theories`
- `methods`

### 会话与证据

- `search_sessions`
- `search_queries`
- `paper_records`
- `paper_versions`
- `evidence_claims`
- `gap_candidates`
- `innovation_candidates`
- `user_selections`
- `proposal_runs`

## 3. 运行时检索

```text
期刊知识库
  → 方向目录编译器（提取全部主题、按章节分组、别名合并）
  → 用户选择大方向，可选填细分研究问题
  → 路由器（YAML精确读取）
  → 期刊池ID
  → 结构化数据库筛选期刊白名单
  → 数据库/API检索论文元数据
  → 期刊/论文/撤稿验证
  → BM25筛选相关论文
  → 对少量候选做embedding与rerank
  → 按需读取全文相关章节
```

输入分支：

- 大方向＋细分研究问题：定向检索最新与经典文献；
- 仅大方向：在最近五个日历年合格论文中聚类，代码按论文数排序前五，再为五个小方向补充经典文献与研究空白分析。

动态论文发现通过 `PaperDiscoveryProvider` 接口接入。当前Crossref实现先读取本地期刊注册表，再按ISSN查询期刊端点；接口限流、中文覆盖不足或验证失败时返回结构化状态，不能静默回退到伪造样例。配置见 `dynamic_retrieval_configuration.md`。

## 4. 不要做的事情

- 每次请求把整个知识库塞进prompt；
- 把所有教材和PDF预先切块向量化；
- 用向量相似度判断期刊等级；
- 让LLM自行记忆用户是否已选择创新点；
- 用自然语言日志替代结构化中间产物。

## 5. 缓存建议

缓存键建议包含：

`normalized_topic + language + journal_pool_version + date_window + query_hash`

可长期缓存期刊与元数据验证；检索结果按周/月刷新；“最新论文”查询应保存搜索日期。

## 6. 最小模型调用策略

1. 范围分类：小模型/规则；
2. 查询扩展：小模型，一次；
3. 元数据过滤和去重：代码；
4. 摘要相关性判断：批量小模型或embedding；
5. 全文证据抽取：只处理最终候选；
6. 研究空白合成：高能力模型；
7. 开题生成：用户选择后才调用高能力模型。

高成本模型只用于“证据综合”和“最终写作”，而不是目录查找、去重和状态判断。

## 7. MVP 技术实现

- Python 3：知识库构建、方向目录编译、校验与外部检索适配器；
- SQLite + FTS5：本地规则、方法书、知识卡和会话级论文元数据；
- YAML/JSON Schema：稳定规则、状态机输入输出和门禁；
- Python标准库HTTP服务：当前V0向页面暴露方向目录和检索任务接口，保持零额外依赖；多人或生产环境再替换为FastAPI；
- 原生 HTML/CSS/JavaScript：本地 Demo 页面，避免在 V0 引入复杂前端依赖；
- 已接入Crossref的可替换 `PaperDiscoveryProvider`；后续在同一边界增加中文数据库、OpenAlex或学校授权检索连接器；
- 模型接口：仅用于关键词扩展、相关性判断、主题命名、证据综合与写作，不负责期刊等级、计数、去重或状态推进。
