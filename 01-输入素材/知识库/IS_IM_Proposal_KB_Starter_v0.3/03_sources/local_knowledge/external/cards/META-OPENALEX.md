---
resource_id: META-OPENALEX
title: OpenAlex API
source_url: https://help.openalex.org/
source_type: official_api
domain:
- metadata
- bibliometrics
authority_level: discovery_and_crosscheck
access: open_api
captured_on: '2026-08-21'
localization_mode: official_api_operational_card_indexed
source_basis: official_public_page
rights_policy: cc0_metadata_and_docs_summary
fulltext_cached: false
runtime_fetch: live_query_for_current_records_only
refresh_days: 90
keywords:
- OpenAlex
- works
- authors
- sources
- institutions
- topics
- citation graph
---

# OpenAlex API

## Localization result

OpenAlex is an open scholarly graph used for broad discovery, citation networks, authors, institutions, sources, topics, and bibliometric enrichment.

## Core knowledge

- Primary entities include works, authors, sources, institutions, topics, publishers, funders, and concepts or related classifications exposed by the current API.
- Work records can include OpenAlex ID, DOI, title, publication date, type, authorships, primary location, source, topics, citations, references, open-access status, and abstract inverted index when available.
- Filters, search, select, group_by, sort, cursor paging, and entity endpoints support reproducible discovery workflows.
- Use OpenAlex identifiers to connect works, authors, institutions, and sources, but retain DOI and journal identifiers for cross-system matching.
- OpenAlex is excellent for recall and network analysis but should be cross-checked for formal bibliographic verification.

## Agent workflow

1. Start with a topic query and explicit date/type/source filters.
2. Use cursor pagination, cache raw JSON, and record the query and retrieval date.
3. Normalize DOI and source identifiers; cross-check final candidates with Crossref and the journal whitelist.
4. Use citation/reference links for backward and forward chaining after seed-paper validation.

## Limits and stop conditions

- Coverage and disambiguation errors can occur for authors, institutions, sources, and topics.
- Citation counts are time-dependent and database-specific.
- Do not use OpenAlex inclusion as evidence of journal quality.

## Operational examples

- `/works?search=human-AI+interaction&filter=type:article`
- `/works?filter=primary_location.source.issn:xxxx-xxxx`

## Platform use

- 论文发现
- 引用网络
- 作者/机构/主题元数据

## Fields to extract or verify

- work_id
- DOI
- cited_by_count
- topics
- source

## Source and rights boundary

- Source URL: https://help.openalex.org/
- Captured on: 2026-08-21
- Access class: open_api
- Local rights policy: cc0_metadata_and_docs_summary
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
