---
resource_id: DB-WANFANG
title: 万方数据知识服务平台
source_url: https://www.wanfangdata.com.cn/
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
- Wanfang
- Chinese journal
- DOI verification
- cross-check
- metadata
---

# 万方数据知识服务平台

## Localization result

Wanfang provides Chinese journal and related scholarly metadata and is useful for discovery plus cross-verification of CNKI records.

## Core knowledge

- Use title, author, keyword, journal, institution, year, DOI, and subject filters where available.
- Capture full citation metadata and the Wanfang identifier.
- Use Wanfang to resolve DOI, page, issue, and author discrepancies found in another database.
- Deduplicate early-online and issue versions and distinguish journal articles from dissertations, conferences, standards, and patents.
- Journal rank is verified only through the local FMS list.

## Agent workflow

1. Run the planned bilingual topic query in Chinese.
2. Export metadata and preserve the exact query and retrieval date.
3. Compare duplicate candidates by title, authors, year, journal, DOI, and pages.
4. Cross-check final records with CNKI, VIP, journal site, or Crossref.

## Limits and stop conditions

- Do not mirror restricted full text.
- Coverage and metadata can differ from other Chinese databases.
- Do not infer article quality from database presence.

## Platform use

- 中文论文检索与交叉核验

## Fields to extract or verify

- 题名
- 作者
- 期刊
- 年份
- DOI

## Source and rights boundary

- Source URL: https://www.wanfangdata.com.cn/
- Captured on: 2026-08-21
- Access class: institutional
- Local rights policy: database_usage_knowledge_no_corpus
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
