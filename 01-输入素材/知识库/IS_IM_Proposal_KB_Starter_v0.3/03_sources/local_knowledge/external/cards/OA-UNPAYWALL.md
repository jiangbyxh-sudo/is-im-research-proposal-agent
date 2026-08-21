---
resource_id: OA-UNPAYWALL
title: Unpaywall API
source_url: https://unpaywall.org/products/api
source_type: official_api
domain:
- open_access
authority_level: access_locator
access: open_api
captured_on: '2026-08-21'
localization_mode: official_api_operational_card_indexed
source_basis: official_public_page
rights_policy: official_docs_summary
fulltext_cached: false
runtime_fetch: live_query_for_current_records_only
refresh_days: 90
keywords:
- Unpaywall
- open access
- best_oa_location
- license
- version
- accepted manuscript
---

# Unpaywall API

## Localization result

Unpaywall locates lawful open-access versions of DOI-identified scholarly works. It is an access locator, not a bibliographic or quality authority.

## Core knowledge

- The DOI endpoint returns OA status and locations, including best_oa_location and alternative oa_locations.
- Useful location fields include landing-page URL, PDF URL, host type, evidence, license, and version such as published, accepted, or submitted.
- Prefer the best lawful version that meets the intended use and preserve version/license metadata.
- Verify the DOI before querying and retain the publisher landing page even when an OA copy is used.
- A missing OA location means no location was indexed, not proof that no lawful copy exists.

## Agent workflow

1. Verify DOI with Crossref.
2. Query Unpaywall using the required contact email.
3. Select a lawful location and record URL, version, license, host type, and retrieval date.
4. Do not automatically ingest full text unless the license and platform policy permit it.

## Limits and stop conditions

- Do not use unofficial or pirated repositories.
- OA status does not establish peer review, validity, or journal rank.
- Licenses and versions must not be discarded during caching.

## Platform use

- 查找合法开放获取版本

## Fields to extract or verify

- best_oa_location
- license
- version

## Source and rights boundary

- Source URL: https://unpaywall.org/products/api
- Captured on: 2026-08-21
- Access class: open_api
- Local rights policy: official_docs_summary
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
