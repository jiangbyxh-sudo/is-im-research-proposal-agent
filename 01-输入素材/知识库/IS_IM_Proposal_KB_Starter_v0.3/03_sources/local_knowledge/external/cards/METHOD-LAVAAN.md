---
resource_id: METHOD-LAVAAN
title: lavaan Tutorial
source_url: https://lavaan.ugent.be/tutorial/
source_type: official_tutorial
domain:
- SEM
- CFA
authority_level: introductory_to_intermediate
access: open
captured_on: '2026-08-21'
localization_mode: official_tutorial_knowledge_card_indexed
source_basis: official_public_page
rights_policy: cc_by_official_tutorial_derived_map
fulltext_cached: false
runtime_fetch: periodic_refresh_only
refresh_days: 180
keywords:
- lavaan
- CFA
- SEM
- mediation
- measurement invariance
- categorical data
- growth curve
- multilevel SEM
---

# lavaan Tutorial

## Localization result

The official lavaan tutorial provides a local operational map for confirmatory factor analysis, structural equation modeling, mediation, growth, multigroup, categorical, and multilevel models in R.

## Core knowledge

- Core syntax specifies latent variables, regressions, covariances, intercepts, thresholds, indirect effects, equality constraints, and defined parameters.
- Primary fitting functions include cfa, sem, and growth; extractor functions include summary, coef, fitted, and inspect.
- The tutorial covers mean structures, multiple groups, growth curves, categorical data, covariance-matrix input, estimators, missing values, standard errors, bootstrapping, mediation, modification indices, multilevel SEM, ESEM, and EFA.
- Model identification, estimator choice, sample size, missing-data assumptions, measurement quality, and distributional properties must be justified.
- Fit indices are diagnostic evidence, not a substitute for theory, residual inspection, parameter plausibility, and alternative models.

## Agent workflow

1. Specify and validate the measurement model before interpreting structural paths.
2. Match estimator and standard errors to variable type, missingness, clustering, and distribution.
3. Report syntax, identification choices, fit statistics, parameter estimates with uncertainty, residual diagnostics, and sensitivity tests.
4. For group comparisons, test measurement invariance before comparing latent means or structural relations.

## Limits and stop conditions

- Do not add paths solely from modification indices without theory and validation.
- Cross-sectional SEM does not establish temporal or causal ordering.
- Parceling, correlated errors, and item deletion require substantive justification and transparent reporting.

## Platform use

- CFA、SEM、中介、多组与分类变量模型

## Fields to extract or verify

- syntax
- fit indices
- examples

## Source and rights boundary

- Source URL: https://lavaan.ugent.be/tutorial/
- Captured on: 2026-08-21
- Access class: open
- Local rights policy: cc_by_official_tutorial_derived_map
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
