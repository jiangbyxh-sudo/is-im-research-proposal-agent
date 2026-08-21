# 来源本地化状态

> 该文件区分“本地可直接检索”与“仅有外部指针”。Agent启动时不得遍历外部指针。

## 汇总

- `abstract_and_method_card_indexed`：1
- `author_resource_knowledge_card_indexed`：1
- `bibliographic_abstract_and_concept_card_indexed`：6
- `database_workflow_card_indexed`：5
- `fulltext_chaptered_chunked_indexed`：2
- `journal_guideline_knowledge_card_indexed`：2
- `official_api_operational_card_indexed`：4
- `official_framework_knowledge_card_indexed`：1
- `official_guideline_knowledge_card_indexed`：1
- `official_project_knowledge_card_indexed`：1
- `official_standard_knowledge_card_indexed`：1
- `official_tutorial_knowledge_card_indexed`：1
- `open_author_resource_learning_map_indexed`：2
- `open_course_learning_map_indexed`：1
- `open_resource_learning_map_indexed`：5
- `public_description_and_knowledge_map_indexed`：1
- `public_toc_and_knowledge_map_indexed`：8
- `structured_snapshot_indexed`：3

| Source ID | 本地状态 | 运行时外部访问 | 下一步 |
|---|---|---|---|
| `RANK-FMS-2025` | `structured_snapshot_indexed` | `periodic_refresh_only` | `localize_or_keep_explicit_gap` |
| `RANK-UTD24` | `structured_snapshot_indexed` | `periodic_refresh_only` | `localize_or_keep_explicit_gap` |
| `RANK-AIS-2025` | `structured_snapshot_indexed` | `periodic_refresh_only` | `localize_or_keep_explicit_gap` |
| `META-CROSSREF` | `official_api_operational_card_indexed` | `live_query_for_current_records_only` | `localize_or_keep_explicit_gap` |
| `META-OPENALEX` | `official_api_operational_card_indexed` | `live_query_for_current_records_only` | `localize_or_keep_explicit_gap` |
| `META-SEMANTIC` | `official_api_operational_card_indexed` | `live_query_for_current_records_only` | `localize_or_keep_explicit_gap` |
| `OA-UNPAYWALL` | `official_api_operational_card_indexed` | `live_query_for_current_records_only` | `localize_or_keep_explicit_gap` |
| `DB-AISEL` | `database_workflow_card_indexed` | `live_query_for_current_records_only` | `localize_or_keep_explicit_gap` |
| `DB-CNKI` | `database_workflow_card_indexed` | `live_query_for_current_records_only` | `localize_or_keep_explicit_gap` |
| `DB-WANFANG` | `database_workflow_card_indexed` | `live_query_for_current_records_only` | `localize_or_keep_explicit_gap` |
| `DB-VIP` | `database_workflow_card_indexed` | `live_query_for_current_records_only` | `localize_or_keep_explicit_gap` |
| `DB-NCPSSD` | `database_workflow_card_indexed` | `live_query_for_current_records_only` | `localize_or_keep_explicit_gap` |
| `WRITE-CRAFT-5E` | `public_toc_and_knowledge_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `WRITE-CRESWELL-6E` | `public_toc_and_knowledge_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `WRITE-SWALES-FEAK` | `public_toc_and_knowledge_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `WRITE-APA-JARS` | `official_guideline_knowledge_card_indexed` | `refresh_if_stale_or_submission_specific` | `localize_or_keep_explicit_gap` |
| `WRITE-MISQ-GUIDE` | `journal_guideline_knowledge_card_indexed` | `refresh_if_stale_or_submission_specific` | `localize_or_keep_explicit_gap` |
| `WRITE-ISR-GUIDE` | `journal_guideline_knowledge_card_indexed` | `refresh_if_stale_or_submission_specific` | `localize_or_keep_explicit_gap` |
| `WRITE-WEBSTER-WATSON` | `bibliographic_abstract_and_concept_card_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `THEORY-GREGOR-2006` | `bibliographic_abstract_and_concept_card_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `THEORY-HEVNER-2004` | `bibliographic_abstract_and_concept_card_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `THEORY-TAM-1989` | `bibliographic_abstract_and_concept_card_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `THEORY-UTAUT-2003` | `bibliographic_abstract_and_concept_card_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `THEORY-TTF-1995` | `bibliographic_abstract_and_concept_card_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `METHOD-OPENINTRO` | `open_resource_learning_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `METHOD-R4DS` | `open_resource_learning_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `METHOD-ISLR` | `public_toc_and_knowledge_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `METHOD-MIXTAPE` | `open_resource_learning_map_indexed` | `periodic_refresh_only` | `localize_or_keep_explicit_gap` |
| `METHOD-LAVAAN` | `official_tutorial_knowledge_card_indexed` | `periodic_refresh_only` | `localize_or_keep_explicit_gap` |
| `METHOD-GIOIA` | `abstract_and_method_card_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `METHOD-THEMATIC` | `author_resource_knowledge_card_indexed` | `periodic_refresh_only` | `localize_or_keep_explicit_gap` |
| `METHOD-PRISMA` | `official_standard_knowledge_card_indexed` | `periodic_refresh_only` | `localize_or_keep_explicit_gap` |
| `METHOD-BDA` | `public_toc_and_knowledge_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `METHOD-PROBML` | `open_author_resource_learning_map_indexed` | `periodic_refresh_only` | `localize_or_keep_explicit_gap` |
| `METHOD-YALE-GAME` | `open_course_learning_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `METHOD-ONLINE-EXPERIMENTS` | `public_toc_and_knowledge_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `IM-INTRO` | `public_toc_and_knowledge_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `IM-LOOKING` | `public_toc_and_knowledge_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `IM-IR-BOOK` | `open_resource_learning_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `IM-KM-DALKIR` | `public_description_and_knowledge_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `IM-DMBOK` | `official_framework_knowledge_card_indexed` | `periodic_refresh_only` | `localize_or_keep_explicit_gap` |
| `IM-SLP3` | `open_author_resource_learning_map_indexed` | `periodic_refresh_only` | `localize_or_keep_explicit_gap` |
| `IM-NETWORK` | `open_resource_learning_map_indexed` | `not_required_for_stable_knowledge` | `localize_or_keep_explicit_gap` |
| `IM-BIBLIOMETRIX` | `official_project_knowledge_card_indexed` | `periodic_refresh_only` | `localize_or_keep_explicit_gap` |
| `METHOD-IACMR-EMPIRICAL-2008` | `fulltext_chaptered_chunked_indexed` | `not_required` | `none_runtime_ready` |
| `METHOD-IACMR-EMPIRICAL-2018` | `fulltext_chaptered_chunked_indexed` | `not_required` | `none_runtime_ready` |
