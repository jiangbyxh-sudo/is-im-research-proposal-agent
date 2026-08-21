---
resource_id: DB-VIP
title: 维普中文期刊服务平台
source_url: https://www.cqvip.com/
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
- VIP
- CQVIP
- Chinese periodicals
- cross-check
- metadata
---

# 维普中文期刊服务平台

## Localization result

VIP is a Chinese periodical discovery and cross-check source used to improve recall and resolve journal metadata.

## Core knowledge

- Search title, keyword, author, journal, subject, institution, and year fields where supported.
- Capture title, authors, journal, year, volume, issue, pages, abstract, keywords, and identifier.
- Use VIP as a secondary check when CNKI and Wanfang disagree or miss an older journal record.
- Normalize traditional/simplified variants, punctuation, author order, journal aliases, and page formats.
- Verify FMS status separately.

## Agent workflow

1. Use the same query plan and date windows as the other Chinese databases.
2. Export/capture metadata and deduplicate across sources.
3. Resolve discrepancies through the journal site or DOI metadata.

## Limits and stop conditions

- Do not mirror subscription content.
- Do not count database inclusion as rank verification.
- Older metadata may require manual journal-site checking.

## Platform use

- 中文期刊论文检索与交叉核验

## Fields to extract or verify

- 题名
- 作者
- 期刊
- 年份

## Source and rights boundary

- Source URL: https://www.cqvip.com/
- Captured on: 2026-08-21
- Access class: institutional
- Local rights policy: database_usage_knowledge_no_corpus
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
