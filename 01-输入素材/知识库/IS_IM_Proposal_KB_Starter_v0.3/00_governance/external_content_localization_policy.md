# External Content Localization Policy

Version: 0.3.0
Captured: 2026-08-21

## Local-first rule

The agent must search local structured snapshots, source cards, and the SQLite FTS index before opening an external URL. External access is not allowed at task startup merely to relearn stable knowledge.

## What is localized

- Versioned ranking and journal-list snapshots.
- API and database operating rules, query fields, verification procedures, and failure conditions.
- Writing, theory, method, and domain knowledge cards derived from official public pages, public tables of contents, abstracts, and openly available author resources.
- 269 searchable chunks from 44 external-source records, combined with the two user-supplied empirical-method books.

## What is not mirrored

- Commercial books, paywalled journal articles, subscription database corpora, account-only material, and protected instructor resources.
- Raw copyrighted abstracts or full pages where redistribution rights are unclear.
- Dynamic paper results, citation counts, correction status, or newly published articles. These must be queried when the user requests current literature.

## Runtime exceptions

Live access is permitted only to retrieve current paper records, verify a stale ranking or submission rule, check corrections or retractions, obtain an authorized full text, or fill an explicit local gap. The result must be cached with provenance when licensing permits.

## Stop rule

If a claim requires content that is absent from the local card and cannot be lawfully accessed, raise KB_SOURCE_CONTENT_MISSING. Do not infer the missing content from the title or invent it.
