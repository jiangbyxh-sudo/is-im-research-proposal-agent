---
resource_id: DB-CNKI
title: 中国知网
source_url: https://www.cnki.net/
source_type: bibliographic_database
domain:
- zh_database
authority_level: authoritative_database
access: institutional
captured_on: '2026-08-21'
localization_mode: database_workflow_card_indexed
source_basis: official_public_page
rights_policy: database_usage_knowledge_no_corpus
fulltext_cached: false
runtime_fetch: live_query_for_current_records_only
refresh_days: 180
keywords:
- CNKI
- Chinese literature
- topic search
- journal verification
- deduplication
---

# 中国知网

## Localization result

CNKI is a major Chinese scholarly discovery source. The local card stores a reproducible query, export, deduplication, and verification protocol; current records remain live.

## Core knowledge

- Construct Chinese queries from phenomenon, technology, actor, context, outcome, theory, and method synonyms.
- Use fielded search such as topic, title, keyword, abstract, author, source, funding, and year where available.
- Capture title, authors, journal, year, volume, issue, pages or article number, affiliation, abstract, keywords, funding, DOI, and database identifier.
- Separate journal articles from dissertations, conference papers, newspapers, books, and duplicate online-first records.
- After discovery, verify the journal against the local FMS Chinese T1/T2 list.

## Agent workflow

1. Run a broad topic search, then narrower title/keyword searches.
2. Apply date and source filters only after inspecting recall.
3. Export metadata; normalize author names, journal titles, DOI, volume, issue, and page fields.
4. Cross-check uncertain records with Wanfang, VIP, NCPSSD, the journal site, or Crossref.

## Limits and stop conditions

- Do not scrape or redistribute subscription full text without permission.
- Database inclusion does not establish FMS rank.
- Do not count non-journal document types toward the requested journal quota.

## Operational examples

- `Broad topic query plus a title/keyword precision query`
- `Separate recent and classic date windows`

## Platform use

- 中文论文检索与元数据核验

## Fields to extract or verify

- 题名
- 作者
- 来源
- 年份
- 摘要
- 基金

## Source and rights boundary

- Source URL: https://www.cnki.net/
- Captured on: 2026-08-21
- Access class: institutional
- Local rights policy: database_usage_knowledge_no_corpus
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
