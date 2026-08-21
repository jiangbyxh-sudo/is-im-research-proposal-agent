---
resource_id: METHOD-BDA
title: Bayesian Data Analysis
source_url: https://sites.stat.columbia.edu/gelman/book/
source_type: book_and_author_resources
domain:
- bayesian
authority_level: advanced
access: author_resources
captured_on: '2026-08-21'
localization_mode: public_toc_and_knowledge_map_indexed
source_basis: official_public_page
rights_policy: author_noncommercial_resource_derived_map_no_redistribution
fulltext_cached: false
runtime_fetch: not_required_for_stable_knowledge
refresh_days: 365
keywords:
- Bayesian
- prior
- likelihood
- posterior
- hierarchical model
- posterior predictive check
- MCMC
- Stan
---

# Bayesian Data Analysis

## Localization result

Bayesian Data Analysis supplies a local conceptual map of Bayesian modeling, hierarchical models, computation, model checking, prediction, and decision analysis, while the public author page supplies legal non-commercial access and code links.

## Core knowledge

- Bayesian inference combines a probability model, prior information, likelihood, and observed data to obtain a posterior distribution.
- Posterior predictive distributions connect parameter uncertainty to observable implications and are central to model checking.
- Hierarchical models support partial pooling across people, groups, firms, items, time periods, or contexts.
- Computation includes simulation, Markov chain Monte Carlo, Hamiltonian methods through Stan, and convergence diagnostics.
- Model criticism, sensitivity to priors, predictive evaluation, and decision-relevant quantities are more important than reporting a posterior mean alone.

## Agent workflow

1. Specify the generative model, likelihood, priors, estimands, and predictive quantities before fitting.
2. Use prior predictive checks, fit the model, diagnose chains and effective sample size, and conduct posterior predictive checks.
3. Compare substantively plausible alternatives and report sensitivity to priors and modeling choices.
4. Archive code, data, seeds, software versions, and simulation diagnostics.

## Limits and stop conditions

- A prior is part of the model and requires justification; default priors are not automatically neutral.
- Converged computation does not imply a well-specified or causally identified model.
- The public PDF is offered for non-commercial purposes; public platform redistribution must follow the authors terms.

## Platform use

- 贝叶斯建模、层级模型、后验预测检验

## Fields to extract or verify

- chapters
- datasets
- errata

## Source and rights boundary

- Source URL: https://sites.stat.columbia.edu/gelman/book/
- Captured on: 2026-08-21
- Access class: author_resources
- Local rights policy: author_noncommercial_resource_derived_map_no_redistribution
- This file is a structured, source-derived knowledge representation. It is not a raw website mirror and does not replace licensed full text.
- Runtime retrieval is permitted only under the declared runtime_fetch rule and platform access controls.
