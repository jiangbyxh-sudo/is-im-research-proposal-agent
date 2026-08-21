# Release Notes v0.4

Released: 2026-08-21

## Journal supplement merge

- Normalized the creator-supplied `supplement_cn_cas` materials into `02_journals/supplements/supplement_cn_cas_merged.json`.
- Added CSSCI 2025–2026 source journals, CSSCI extended journals as a separate non-equivalent label, PKU Core 2023, and CAS 2025 SSCI Zone 1/2.
- Preserved independent ranking labels and provenance; no custom A/B conversion is performed.
- Expanded the runtime registry from 86 to 179 journal records: 68 English and 111 Chinese.
- Kept default English eligibility at UTD24/FMS A/B; CAS-only titles remain an opt-in extension.
- Expanded default Chinese eligibility to FMS T1/T2, CSSCI source journals, and PKU Core 2023.

## Runtime and interface

- Enabled eligible Chinese Crossref routes by default while retaining honest shortages when metadata coverage is insufficient.
- Added supplemental direction-to-pool routes for IS, HCI, psychology, communication, IM, and data/knowledge directions.
- Made synthesis success, limitations, five subdirections, evidence-linked gap candidates, and gap selection explicit in the interface.
- Kept an honest empty state when the synthesis provider is not configured; no mock gap is generated.

## Verification boundary

The merged supplement is creator-supplied and versioned. CAS records preserve their secondary-cross-check status and official-account recheck rule. A journal without an exact Crossref match remains in the eligibility knowledge base but is not queried through a fabricated ISSN.

## v0.4.1 maintenance update

- Added a visible, language-grouped audit of the Chinese and English journals actually queried for each request.
- Added a local password input for process-memory-only DeepSeek configuration, plus an explicit clear action.
- The key is never returned by the API, written to files, or logged; the page clears the input before sending the request.
- Restricted runtime configuration to the official DeepSeek base URL and `deepseek-v4-pro` model.
