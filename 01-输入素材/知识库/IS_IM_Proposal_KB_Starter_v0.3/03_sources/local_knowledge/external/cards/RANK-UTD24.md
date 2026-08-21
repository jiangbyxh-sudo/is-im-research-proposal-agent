---
resource_id: RANK-UTD24
title: UTD Top 100 Journal List
source_url: https://jsom.utdallas.edu/the-utd-top-100-business-school-research-rankings/list-of-journals
source_type: official_ranking
domain:
- governance
- journals
authority_level: authoritative
access: open
captured_on: '2026-08-21'
localization_mode: structured_snapshot_indexed
source_basis: official_public_page
rights_policy: official_list_snapshot
fulltext_cached: false
runtime_fetch: periodic_refresh_only
refresh_days: 180
keywords:
- UTD24
- membership
- business journals
- MIS Quarterly
- ISR
---

# UTD Top 100 Journal List

## Localization result

UTD24 is a membership list of 24 leading business journals used by the UT Dallas research-ranking database; it is not an A/B tier system.

## Core knowledge

- Store UTD status as Boolean membership plus list version, never as a fabricated tier.
- The current list covers accounting, finance, IS, marketing, operations, and management journals.
- IS members include Information Systems Research, Journal on Computing, and MIS Quarterly.
- Management Science, Marketing Science, and Organization Science can be relevant to digital-platform and digital-organization research but remain multidisciplinary outlets.
- Topic scope must still be checked; publication in a UTD journal does not automatically make a paper IS or IM.

## Agent workflow

1. Resolve the exact journal title against the local UTD24 list.
2. Write ranking_system=UTD24 and membership=true.
3. If the journal is not a UTD member, continue to the FMS A/B branch before rejecting it.

## Limits and stop conditions

- Do not call a journal UTD A or UTD B.
- Do not infer membership from a similar title or publisher.

## Platform use

- 验证UTD24成员

## Fields to extract or verify

- 期刊名
- 名单版本

## Source and rights boundary

- Source URL: https://jsom.utdallas.edu/the-utd-top-100-business-school-research-rankings/list-of-journals
- Captured on: 2026-08-21
- Access class: open
- Local rights policy: official_list_snapshot
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
