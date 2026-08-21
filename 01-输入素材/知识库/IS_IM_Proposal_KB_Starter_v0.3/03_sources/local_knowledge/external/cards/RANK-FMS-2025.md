---
resource_id: RANK-FMS-2025
title: FMS管理科学高质量期刊推荐列表2025
source_url: https://www.fms-journal.net/
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
- FMS
- journal ranking
- A
- B
- T1
- T2
- whitelist
---

# FMS管理科学高质量期刊推荐列表2025

## Localization result

FMS 2025 is the hard-ranking source for international A/B journals and Chinese T1/T2 journals. The two scales are separate and must never be mixed.

## Core knowledge

- The 2025 list contains 1,183 international journals classified A, B, C, or D and 94 Chinese journals classified T1 or T2.
- For the platform English quota, only international A/B journals are eligible under the current rule. For the Chinese quota, use T1/T2.
- Treat the list as a versioned whitelist. Match normalized title and, where available, ISSN; do not infer rank from impact factor, publisher, or database inclusion.
- Store ranking system, edition, tier, verification date, and the local record used for every included paper.
- FMS itself cautions against mechanical use of journal ratings as a direct measure of individual research quality.

## Agent workflow

1. Normalize the journal title and aliases.
2. Resolve the journal against the local IS/IM journal pool and the Chinese T1/T2 list.
3. If no exact verified match exists, raise JOURNAL_RANK_UNVERIFIED and exclude the paper from the formal count.
4. Refresh only when the creator adopts a new FMS edition.

## Limits and stop conditions

- Do not label Chinese T1/T2 journals as A/B.
- Do not use FMS C/D papers to pad the requested count.
- A third-party ranking or citation index is not a substitute for the local official snapshot.

## Platform use

- 验证国际A/B与中文T1/T2
- 期刊名单版本控制

## Fields to extract or verify

- 期刊名
- 等级
- 版本
- 发布日期

## Source and rights boundary

- Source URL: https://www.fms-journal.net/
- Captured on: 2026-08-21
- Access class: open
- Local rights policy: official_list_snapshot
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
