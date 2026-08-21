---
resource_id: IM-IR-BOOK
title: Introduction to Information Retrieval
source_url: https://nlp.stanford.edu/IR-book/
source_type: open_textbook
domain:
- IM
- information_retrieval
authority_level: foundational
access: open
captured_on: '2026-08-21'
localization_mode: open_resource_learning_map_indexed
source_basis: official_public_page
rights_policy: author_online_book_derived_map
fulltext_cached: false
runtime_fetch: not_required_for_stable_knowledge
refresh_days: 365
keywords:
- information retrieval
- inverted index
- TF-IDF
- vector space
- probabilistic retrieval
- evaluation
- web search
- RAG
---

# Introduction to Information Retrieval

## Localization result

Introduction to Information Retrieval is locally mapped from its public online edition and chapter structure, covering indexing, retrieval models, evaluation, text classification, clustering, web search, crawling, and link analysis.

## Core knowledge

- Foundations include Boolean retrieval, vocabularies, postings lists, tolerant retrieval, index construction, and compression.
- Ranking topics include term weighting, vector-space scoring, probabilistic retrieval, language models, and complete-system score computation.
- Evaluation includes relevance judgments, precision, recall, ranked metrics, test collections, and experimental comparison.
- Expansion and learning topics include relevance feedback, query expansion, text classification, naive Bayes, vector classifiers, support vector machines, clustering, and latent semantic indexing.
- Web topics include web search, crawling, indexes, and link analysis; modern dense retrieval and RAG should be compared with transparent lexical baselines.

## Agent workflow

1. Define corpus, documents, queries, users, relevance, retrieval task, and evaluation protocol.
2. Build a lexical baseline, document preprocessing, index construction, ranking model, and held-out evaluation set.
3. Report dataset version, split, relevance construction, metrics, ablations, latency or cost, and error analysis.
4. For social-science applications, validate whether retrieval metrics correspond to user understanding, decision quality, fairness, or other substantive outcomes.

## Limits and stop conditions

- Offline benchmark gains may not transfer to real users or changing corpora.
- Test-collection leakage and repeated benchmark tuning inflate performance.
- Dense retrieval and RAG do not remove the need for source provenance, evidence quality, and hallucination controls.

## Platform use

- 倒排索引、TF-IDF、检索评价、分类、聚类与Web搜索

## Fields to extract or verify

- chapters
- slides
- exercises

## Source and rights boundary

- Source URL: https://nlp.stanford.edu/IR-book/
- Captured on: 2026-08-21
- Access class: open
- Local rights policy: author_online_book_derived_map
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
