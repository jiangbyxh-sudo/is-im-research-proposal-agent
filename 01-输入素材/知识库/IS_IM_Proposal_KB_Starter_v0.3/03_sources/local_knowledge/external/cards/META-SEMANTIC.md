---
resource_id: META-SEMANTIC
title: Semantic Scholar Academic Graph API
source_url: https://api.semanticscholar.org/api-docs/
source_type: official_api
domain:
- metadata
- discovery
authority_level: discovery_and_crosscheck
access: open_api
captured_on: '2026-08-21'
localization_mode: official_api_operational_card_indexed
source_basis: official_public_page
rights_policy: official_docs_summary
fulltext_cached: false
runtime_fetch: live_query_for_current_records_only
refresh_days: 90
keywords:
- Semantic Scholar
- Academic Graph
- paperId
- citations
- references
- recommendations
---

# Semantic Scholar Academic Graph API

## Localization result

Semantic Scholar Academic Graph supports paper and author discovery, citation/reference traversal, recommendations, and selected metadata enrichment.

## Core knowledge

- Paper records can expose paperId, title, abstract, year, venue, publication types, authors, external IDs, fields of study, citations, references, and influence-related fields when available.
- Use explicit fields parameters so responses remain small and predictable.
- Batch endpoints are preferable when resolving many known paper IDs or external IDs.
- Recommendation and graph features are discovery aids, not substitutes for a documented systematic search.
- Store paperId together with DOI or other external identifiers to support deduplication.

## Agent workflow

1. Search broadly by topic, then resolve candidate records by DOI/title.
2. Traverse citations and references from verified seed papers.
3. Cache results, respect rate limits, and record API version/date and requested fields.
4. Verify final bibliographic metadata with Crossref, publisher, or another authoritative source.

## Limits and stop conditions

- Abstract availability is uneven and may be copyrighted.
- Recommendations can reproduce coverage and popularity bias.
- Venue strings may not be sufficient for exact journal verification.

## Operational examples

- `paper search with fields=title,year,authors,venue,externalIds`
- `batch paper lookup by DOI`

## Platform use

- 论文发现
- 引用关系
- 推荐

## Fields to extract or verify

- paperId
- title
- abstract
- citations
- references

## Source and rights boundary

- Source URL: https://api.semanticscholar.org/api-docs/
- Captured on: 2026-08-21
- Access class: open_api
- Local rights policy: official_docs_summary
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
