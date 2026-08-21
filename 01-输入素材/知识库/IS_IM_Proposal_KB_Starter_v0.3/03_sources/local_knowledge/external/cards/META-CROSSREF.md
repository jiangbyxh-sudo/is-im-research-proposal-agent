---
resource_id: META-CROSSREF
title: Crossref REST API
source_url: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
source_type: official_api
domain:
- metadata
- integrity
authority_level: authoritative
access: open_api
captured_on: '2026-08-21'
localization_mode: official_api_operational_card_indexed
source_basis: official_public_page
rights_policy: official_docs_summary
fulltext_cached: false
runtime_fetch: live_query_for_current_records_only
refresh_days: 90
keywords:
- Crossref
- DOI
- metadata
- update-to
- retraction
- correction
- cursor
---

# Crossref REST API

## Localization result

Crossref is the primary DOI and publisher-deposited metadata verification service. Its operational knowledge is local; current records are queried only when needed.

## Core knowledge

- Core endpoints include works, journals, members, funders, prefixes, types, and licenses; exact DOI lookup uses /works/{doi}.
- Useful fields include DOI, title, authors, container-title, ISSN, type, publisher, dates, references, licenses, links, relations, and post-publication updates.
- Crossref metadata is deposited by publishers and supplemented by trusted sources such as Retraction Watch; missing fields mean not deposited, not necessarily absent in reality.
- Use relation and update metadata to inspect corrections, retractions, expressions of concern, preprint/article links, and versions.
- Most metadata is openly reusable, but abstracts may remain copyrighted.

## Agent workflow

1. Normalize the DOI by removing URL prefixes, spaces, and trailing punctuation.
2. Use the exact DOI endpoint first; otherwise search bibliographic fields and confirm title, first author, journal, and year.
3. Use the polite pool with mailto/User-Agent, cache responses, handle 429/5xx with backoff, and use cursors for deep paging.
4. Store the raw identifier and selected verification fields in the paper record.

## Limits and stop conditions

- Publisher-deposited metadata can be incomplete or inconsistent.
- Do not treat a successful DOI response as proof of journal rank or topical scope.
- Do not redistribute copyrighted abstracts merely because they appear in metadata.

## Operational examples

- `GET /v1/works/{doi}`
- `GET /v1/journals/{issn}/works?filter=type:journal-article`

## Platform use

- DOI元数据验证
- 版本/更正/撤稿检查

## Fields to extract or verify

- DOI
- 题名
- 作者
- 期刊
- 日期
- update-to

## Source and rights boundary

- Source URL: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- Captured on: 2026-08-21
- Access class: open_api
- Local rights policy: official_docs_summary
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
