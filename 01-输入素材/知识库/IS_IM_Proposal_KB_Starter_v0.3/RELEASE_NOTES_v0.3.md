# Release Notes v0.3

Released: 2026-08-21

## Added

- Local source cards for all 44 external records in the v0 source registry.
- Versioned UTD24, AIS Premier 2025, and FMS 2025 scope snapshots.
- External-source topic router, audit manifest, rights policy, and capture hashes.
- Unified JSONL and SQLite FTS5 index with 1869 chunks (1600 empirical-book chunks and 269 external-source chunks).
- Local-first retrieval CLI and validation scripts.

## v0.3.1 maintenance update

- Added all 180 creator-supplied book images and cleared the missing-asset register.
- Compiled 75 raw journal-knowledge topics into 61 grouped, alias-merged user-selectable directions.
- Added automatic input branching: broad direction only → top five recent subdirections; broad direction plus a fine-grained question → focused search.
- Added a five-calendar-year popularity rule, initial request schema, and replaceable live paper-discovery provider boundary.
- Fixed rebuild safety so book ingestion preserves the 44 localized external resources and rebuilds the unified FTS index atomically.

## Runtime behavior

Stable writing, theory, method, domain, API, and database-operating knowledge is read locally. Live access is reserved for current literature, current metadata, correction/retraction checks, authorized full text, stale rules, and explicit gaps.

## v0.3.2 dynamic-retrieval update

- Added a generated runtime registry for 86 eligible journals; 75 have local ISSNs and 44 currently expose a verified Crossref journal endpoint.
- Activated Crossref paper discovery behind the replaceable provider boundary.
- Added direction-group to journal-pool routing, five-calendar-year queries, DOI/title deduplication, ranking evidence and search logs.
- Added retraction/correction exclusion and a minimum relevance gate; quotas remain visibly short instead of being padded.
- Kept OpenAlex and licensed Chinese databases as explicit future connectors requiring their own lawful access configuration.

## Rights boundary

Commercial books, subscription databases, and paywalled articles are represented through public metadata, tables of contents, abstracts, and derived knowledge cards. Their protected full text is not included.

## v0.3.3 evidence-synthesis update

- Disabled Chinese retrieval by default until a lawful Chinese database connector is configured.
- Added environment-only DeepSeek configuration; secrets are never stored or returned by the application.
- Added evidence-bounded clustering for the five most populated recent subdirections and research-gap candidates.
- Added code-side validation of input paper IDs, DOI mentions, recomputed cluster counts and minimum two-paper evidence anchors.
- Added an interactive gap-selection step; proposal generation remains gated by full-text verification.
