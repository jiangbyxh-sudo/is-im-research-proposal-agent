---
resource_id: METHOD-MIXTAPE
title: 'Causal Inference: The Mixtape'
source_url: https://mixtape.scunning.com/
source_type: open_textbook
domain:
- causal_inference
authority_level: intermediate
access: open
captured_on: '2026-08-21'
localization_mode: open_resource_learning_map_indexed
source_basis: official_public_page
rights_policy: public_online_resource_derived_map
fulltext_cached: false
runtime_fetch: periodic_refresh_only
refresh_days: 180
keywords:
- causal inference
- DAG
- potential outcomes
- RDD
- IV
- DiD
- event study
- synthetic control
---

# Causal Inference: The Mixtape

## Localization result

Causal Inference: The Remix provides a local design map for social-science causal inference from DAGs and potential outcomes through quasi-experimental estimators.

## Core knowledge

- Foundations include counterfactual outcomes, treatment assignment, estimands, directed acyclic graphs, identification, and the difference between association and causation.
- Design families include unconfoundedness, matching or weighting, regression discontinuity, instrumental variables, causal panel designs, difference-in-differences, event studies, and synthetic control.
- Each estimator is credible only under explicit design assumptions such as exchangeability, continuity, exclusion, parallel trends, or stable treatment definitions.
- Diagnostics, falsification tests, sensitivity analysis, treatment timing, heterogeneous effects, and interference must be considered before interpreting estimates.
- Code implementation is secondary to a defensible assignment mechanism and a clearly defined estimand.

## Agent workflow

1. State the causal question, treatment, outcome, unit, timing, target population, and estimand.
2. Draw the causal structure and identify the source of variation before choosing an estimator.
3. Document assumptions, diagnostics, alternative specifications, and plausible violations.
4. Separate design-stage decisions from outcome-driven specification searching.

## Limits and stop conditions

- A fixed-effects regression is not automatically causal.
- Pre-trend non-rejection does not prove parallel trends, and post-treatment controls can induce bias.
- Do not use an instrument without a defensible relevance, exclusion, and monotonicity argument appropriate to the estimand.
- If identification assumptions cannot be defended, downgrade the claim to descriptive or associational.

## Platform use

- 潜在结果、DAG、RDD、IV、DiD、合成控制

## Fields to extract or verify

- assumptions
- estimators
- code

## Source and rights boundary

- Source URL: https://mixtape.scunning.com/
- Captured on: 2026-08-21
- Access class: open
- Local rights policy: public_online_resource_derived_map
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
