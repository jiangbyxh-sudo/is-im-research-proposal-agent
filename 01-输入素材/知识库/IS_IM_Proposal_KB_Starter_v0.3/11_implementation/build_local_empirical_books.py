#!/usr/bin/env python3
"""Build a local-first empirical-methods knowledge layer from user-supplied Markdown books.

Outputs:
- preserved full text and per-chapter files
- portable JSONL chunks with page/line provenance
- SQLite FTS5 trigram index for Chinese/English local retrieval
- topic router and concise source-grounded method cards
- source registry, manifest, coverage, governance, and retrieval-rule updates

This script does not download external material. It treats the two inputs as private,
user-supplied research copies, indexes available local images, and records only genuinely
missing image assets rather than inventing them.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml

TODAY = "2026-08-21"

BOOKS: dict[str, dict[str, Any]] = {
    "METHOD-IACMR-EMPIRICAL-2008": {
        "year": 2008,
        "title": "组织与管理研究的实证方法（2008版）",
        "editors": ["陈晓萍", "徐淑英", "樊景立"],
        "publisher": "北京大学出版社",
        "isbn": "978-7-301-13909-7",
        "input_name": "组织与管理研究的实证方法（2008版）(1).md",
        "priority": "supplementary",
        "edition_role": "历史版本与第三版未保留专题的补充来源",
    },
    "METHOD-IACMR-EMPIRICAL-2018": {
        "year": 2018,
        "title": "组织与管理研究的实证方法（第三版，2018）",
        "editors": ["陈晓萍", "沈伟"],
        "publisher": "北京大学出版社",
        "isbn": "978-7-301-29643-1",
        "input_name": "组织与管理研究的实证方法（第三版，2018）(1).md",
        "priority": "primary",
        "edition_role": "管理与组织实证研究方法的首选本地来源",
    },
}

# Curated chapter metadata. These are routing summaries, not substitutes for the source chapter.
META_2018: dict[Any, dict[str, Any]] = {
    "intro": {"slug": "publication_rigor_and_relevance", "tags": ["research_rigor", "relevance", "publication", "research_question", "ethics"], "summary": "从严谨性、现实关联、研究问题与常见投稿错误切入，说明高质量管理研究和论文发表的基本判断标准。"},
    1: {"slug": "scientific_process_and_research_design", "tags": ["scientific_process", "epistemology", "research_design", "contextualization", "ethics"], "summary": "介绍科学求知、理论与数据循环、研究设计目标、情境化以及科学伦理，为后续方法选择提供认识论基础。"},
    2: {"slug": "research_question_and_proposal", "tags": ["research_question", "phenomenon_driven", "literature_review", "hypothesis", "proposal"], "summary": "说明好的研究问题的标准、问题来源及其向变量、假设、设计和开题报告的转化过程。"},
    3: {"slug": "theory_building", "tags": ["theory", "construct", "mechanism", "theoretical_contribution", "induction", "deduction"], "summary": "讨论理论的构成与层级、理论建构过程、理论贡献途径，以及如何用逻辑和故事组织理论论证。"},
    4: {"slug": "empirical_design_and_validity", "tags": ["empirical_design", "causality", "validity", "variance_control", "data_method_fit"], "summary": "以因果关系、研究问题与数据匹配、变异量控制及构念/统计/内部/外部效度评价实证研究。"},
    5: {"slug": "experimental_research", "tags": ["experiment", "manipulation", "randomization", "lab_experiment", "field_experiment", "online_experiment", "validity"], "summary": "覆盖实验假设、实验室/实地/网上实验、效度威胁、操纵与组间/组内/因素设计及可复制性。"},
    6: {"slug": "quasi_experimental_research", "tags": ["quasi_experiment", "natural_experiment", "control_group", "pretest_posttest", "causal_inference"], "summary": "介绍准实验的优势、常见设计、控制组与自然干预，并以组织管理案例分析识别与效度问题。"},
    7: {"slug": "survey_research", "tags": ["survey", "questionnaire", "sampling", "measurement", "multi_source", "common_method_bias"], "summary": "覆盖问卷目的与类型、题项和量尺设计、抽样与数据收集、多来源设计，以及中国情境下的应用问题。"},
    8: {"slug": "secondary_and_archival_data", "tags": ["secondary_data", "archival_data", "panel_data", "text_data", "data_quality", "provenance"], "summary": "说明二手数据的类型、研究贡献、文本与结构化数据、面板优势、数据能力要求和使用风险。"},
    9: {"slug": "case_study", "tags": ["case_study", "field_research", "case_selection", "validity", "reliability", "qualitative"], "summary": "界定案例研究，说明质量标准、准备与执行、现场关系、对话分析和常见问题。"},
    10: {"slug": "qualitative_research_and_analysis", "tags": ["qualitative", "grounded_theory", "open_coding", "axial_coding", "selective_coding", "theory_building"], "summary": "说明质化研究与扎根理论，并以开放式、轴心和选择性编码展示数据分析和写作。"},
    11: {"slug": "meta_analysis", "tags": ["meta_analysis", "effect_size", "systematic_search", "moderator", "publication_bias", "meta_sem"], "summary": "覆盖元分析的问题设定、检索与编码、固定/随机模型、调节检验、Meta-SEM、发表偏差及工具。"},
    12: {"slug": "contextualized_research", "tags": ["contextualization", "context", "china_research", "boundary_condition", "method_adaptation"], "summary": "区分不同类型的情境依赖，提出四种情境化路径，并强调理论、现象和方法与研究情境的匹配。"},
    13: {"slug": "construct_measurement", "tags": ["construct_measurement", "scale_development", "content_validity", "reliability", "convergent_validity", "discriminant_validity"], "summary": "介绍构念测量、题项生成、内容效度、内部结构、信度、聚合/区分效度和逻辑关系网络。"},
    14: {"slug": "unidimensional_and_multidimensional_constructs", "tags": ["construct_dimensionality", "reflective_indicator", "formative_indicator", "measurement_model"], "summary": "区分单维与多维构念、效果与构成指标，并讨论不同构念结构的测量和估计。"},
    15: {"slug": "structural_equation_modeling", "tags": ["SEM", "CFA", "measurement_model", "path_model", "fit_index", "Mplus"], "summary": "介绍结构方程模型的逻辑、测量误差、测量/路径/全模型、均值结构、软件实现与模型评价。"},
    16: {"slug": "moderation_and_mediation", "tags": ["moderation", "mediation", "interaction", "indirect_effect", "statistical_power"], "summary": "从理论意义到统计检验系统讨论调节、中介、交互作用、间接效应、功效和常见分析问题。"},
    17: {"slug": "multilevel_theory_and_hlm", "tags": ["multilevel", "HLM", "aggregation", "centering", "cross_level", "sample_size"], "summary": "讨论多层次理论、构念与聚合、HLM分析流程、中心化、统计假设、样本量及延伸模型。"},
    18: {"slug": "longitudinal_panel_analysis", "tags": ["longitudinal", "panel_data", "fixed_effects", "random_effects", "GLS", "Stata"], "summary": "说明面板数据优势、OLS假设、固定效应、随机效应、广义最小二乘及软件操作。"},
    19: {"slug": "event_history_analysis", "tags": ["event_history", "survival_analysis", "hazard", "censoring", "proportional_hazards", "accelerated_failure_time"], "summary": "介绍事件、时间与数据结构，讨论风险模型、比例风险与加速时间模型及研究设计。"},
    20: {"slug": "event_study", "tags": ["event_study", "abnormal_return", "event_window", "capital_market", "event_system_theory"], "summary": "介绍资本市场事件研究的原理、假定、事件窗与实施步骤，并讨论中国市场应用及事件系统理论。"},
    21: {"slug": "diary_and_experience_sampling", "tags": ["diary_study", "experience_sampling", "ESM", "intensive_longitudinal", "multilevel"], "summary": "覆盖日记与体验抽样的类型、计划、测量、技术、招募执行、数据分析和组织研究应用。"},
    22: {"slug": "moderated_mediation_and_mediated_moderation", "tags": ["moderated_mediation", "mediated_moderation", "conditional_process", "multilevel"], "summary": "区分被中介的调节和被调节的中介，说明单层与多层模型的理论构建、检验和统计问题。"},
    23: {"slug": "academic_writing_review_and_revision", "tags": ["academic_writing", "title", "abstract", "introduction", "method", "discussion", "peer_review", "revision"], "summary": "覆盖论文题目、摘要、导言、方法、结果讨论、结论，以及投稿、审阅、修改、回复和发表。"},
}

META_2008: dict[Any, dict[str, Any]] = {
    "intro": {"slug": "publication_rigor_legacy", "tags": ["research_rigor", "publication", "research_question", "validity"], "summary": "以一流期刊发表为线索讨论研究问题、理论、方法、效度、贡献与研究伦理，是第三版引言的早期版本。"},
    1: META_2018[1],
    2: {"slug": "research_question_legacy", "tags": ["research_question", "proposal", "literature_review"], "summary": "讨论问题来源、一般问题向研究课题的转化及开题报告形成，可与第三版第2章对照使用。"},
    3: META_2018[3],
    4: {"slug": "china_management_theory", "tags": ["china_theory", "indigenous_theory", "emic_etic", "contextualization"], "summary": "讨论中国管理学理论建构的哲学基础、主位/客位取向及本土现象形成理论的机会与挑战。"},
    5: META_2018[4],
    6: META_2018[5],
    7: META_2018[6],
    8: {"slug": "field_survey_legacy", "tags": ["survey", "scale_adaptation", "sampling", "data_collection"], "summary": "重点讨论实地问卷中的既有量表沿用、自编量表、问卷发放与回收。"},
    9: META_2018[8],
    10: META_2018[9],
    11: META_2018[13],
    12: META_2018[14],
    13: META_2018[15],
    14: META_2018[16],
    15: META_2018[17],
    16: {"slug": "organizational_social_capital_measurement", "tags": ["social_capital", "network_ties", "trust", "network_structure", "measurement"], "summary": "从个体/集体和组织内/外层次区分关系面与结构面社会资本，并讨论相应测量。"},
    17: {"slug": "cross_cultural_research", "tags": ["cross_cultural", "emic_etic", "measurement_equivalence", "sampling", "multilevel"], "summary": "介绍跨文化研究类型、主位/客位取向、概念与测量对等性、抽样实施和数据分析。"},
    18: {"slug": "writing_and_peer_review_legacy", "tags": ["academic_writing", "deductive", "inductive", "peer_review", "revision"], "summary": "分别讨论演绎式和归纳式研究报告、通用写作准则、审稿过程及修改再投。"},
    19: {"slug": "paper_publication_journey", "tags": ["research_process", "publication_journey", "revision", "case_example"], "summary": "以一篇论文为案例呈现从问题提出到文章发表的完整研究与修改过程。"},
    20: {"slug": "publishing_china_management_research", "tags": ["china_research", "theory_context_fit", "generalizability", "publication"], "summary": "讨论中国情境研究与西方理论的结合、整合性理论框架和实证结果的普适化。"},
}

# Local retrieval cards. These are concise decision aids; detailed claims should retrieve the cited chapter chunks.
TOPIC_CARDS: list[dict[str, Any]] = [
    {
        "id": "LOCAL-METHOD-RESEARCH-QUESTION",
        "title": "研究问题、研究空白与开题转化",
        "aliases": ["研究问题", "选题", "开题", "研究空白", "创新点", "现象驱动", "literature gap", "research question"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch02"), ("METHOD-IACMR-EMPIRICAL-2018", "intro"), ("METHOD-IACMR-EMPIRICAL-2008", "ch02")],
        "use_when": "用户只有宽泛方向，需要形成重要、可研究且可执行的问题，并映射到构念、假设和研究设计。",
        "core_actions": ["区分现象、问题和解决方案", "评估重要性、新颖性及理论/实践相关性", "从现象驱动、方法驱动、灵感驱动和文献驱动路径寻找问题", "将问题收敛为变量/构念、关系、边界和可执行设计", "在开题中明确问题、理论、方法、预期贡献与可行性"],
        "warnings": ["不能仅把单篇论文的未来研究建议当作已证实空白", "研究问题不清楚时不得直接生成假设", "空白必须附检索边界和支持/反对证据"],
    },
    {
        "id": "LOCAL-METHOD-THEORY-BUILDING",
        "title": "理论建构与理论贡献",
        "aliases": ["理论建构", "理论贡献", "构念", "机制", "边界条件", "theory building", "theoretical contribution"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch03"), ("METHOD-IACMR-EMPIRICAL-2008", "ch03"), ("METHOD-IACMR-EMPIRICAL-2008", "ch04")],
        "use_when": "需要判断论文的理论对象、核心机制、贡献类型和假设推理链。",
        "core_actions": ["明确核心构念及其层级", "解释构念之间为何产生关系", "区分演绎与归纳路径", "识别扩展、整合、挑战或情境化贡献", "用逻辑叙事和框图检查理论闭环"],
        "warnings": ["变量清单、文献堆叠或假设数量不等于理论", "理论层级必须与测量和分析层级一致", "理论贡献不得只写成更换国家、行业或样本"],
    },
    {
        "id": "LOCAL-METHOD-DESIGN-VALIDITY",
        "title": "实证研究设计、因果关系与效度",
        "aliases": ["研究设计", "因果关系", "效度", "内部效度", "外部效度", "构念效度", "统计结论效度", "research design", "validity"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch04"), ("METHOD-IACMR-EMPIRICAL-2018", "ch01"), ("METHOD-IACMR-EMPIRICAL-2008", "ch05")],
        "use_when": "为任何实证开题选择设计、数据和分析方法，或审查因果主张是否超出证据。",
        "core_actions": ["让研究问题、理论、数据来源和分析方法相互匹配", "识别系统变异、外生变异和误差变异", "分别评估构念、统计结论、内部和外部效度", "列出替代解释和控制策略", "根据设计强度限制因果措辞"],
        "warnings": ["横截面相关数据通常不能单独支撑强因果结论", "控制变量不能替代识别策略", "单位层次不匹配会使理论和结论失效"],
    },
    {
        "id": "LOCAL-METHOD-EXPERIMENT",
        "title": "实验、在线实验与因素设计",
        "aliases": ["实验", "实验室实验", "实地实验", "网上实验", "A/B测试", "操纵检验", "experiment", "field experiment", "online experiment"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch05"), ("METHOD-IACMR-EMPIRICAL-2008", "ch06")],
        "use_when": "研究操纵某一因素对行为、判断或技术使用结果的影响，常见于Behavioral IS与Human-AI Interaction。",
        "core_actions": ["把理论假设转化为可操纵因素和可观测结果", "选择组间、组内或因素设计", "规划随机分派、控制条件和操纵检查", "同时评估内部与外部效度", "预先规定排除、功效和可复制性策略"],
        "warnings": ["操纵同时改变多个理论构念会破坏解释", "只报告显著结果会增加选择性报告风险", "实验场景和样本不能代表目标情境时应限制外推"],
    },
    {
        "id": "LOCAL-METHOD-QUASI-EXPERIMENT",
        "title": "准实验与自然干预",
        "aliases": ["准实验", "自然实验", "前后测", "对照组", "政策冲击", "quasi experiment", "natural experiment"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch06"), ("METHOD-IACMR-EMPIRICAL-2008", "ch07")],
        "use_when": "存在外生事件或组织干预但无法完全随机分派，需要用比较组、前后测或自然变化增强识别。",
        "core_actions": ["说明干预为何近似外生", "选择合适的对照和观察窗口", "检查处理前差异与同期冲击", "记录设计对内部效度的剩余威胁", "将分析模型与准实验结构对齐"],
        "warnings": ["把普通前后对比称为准实验并不足够", "没有可信对照时不能消除时间趋势", "事后选择事件和窗口会放大研究者自由度"],
    },
    {
        "id": "LOCAL-METHOD-SURVEY",
        "title": "问卷、抽样与多来源设计",
        "aliases": ["问卷", "调查研究", "量表", "抽样", "共同方法偏差", "survey", "questionnaire", "sampling"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch07"), ("METHOD-IACMR-EMPIRICAL-2018", "ch13"), ("METHOD-IACMR-EMPIRICAL-2008", "ch08")],
        "use_when": "通过受访者报告测量态度、认知、行为或组织情境，并计划使用回归、CFA或SEM。",
        "core_actions": ["先决定调查目的、目标总体和分析层级", "优先使用与情境匹配且有证据的量表", "审查题项语言、量尺、顺序和封面", "制定抽样、回收和缺失数据计划", "尽量采用多时间点、多来源或客观结果"],
        "warnings": ["同源、同时点、自陈数据会限制因果和共同方法解释", "翻译量表不能跳过语义和测量等价性检查", "便利样本必须说明适用边界"],
    },
    {
        "id": "LOCAL-METHOD-ARCHIVAL-PANEL",
        "title": "二手数据、档案数据与面板研究",
        "aliases": ["二手数据", "档案数据", "面板数据", "数据库", "文本数据", "archival data", "secondary data", "panel data"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch08"), ("METHOD-IACMR-EMPIRICAL-2018", "ch18"), ("METHOD-IACMR-EMPIRICAL-2008", "ch09")],
        "use_when": "利用企业、平台、政府或公开数据库研究组织、市场与技术现象。",
        "core_actions": ["记录数据生产过程、口径、覆盖和版本", "判断文本、关系或矩阵数据如何对应理论构念", "检查面板结构、缺失、选择和测量变化", "在固定效应、随机效应等模型间依据假设选择", "为数据拼接和清洗保留审计轨迹"],
        "warnings": ["大样本不能弥补构念测量错误", "数据可得性不等于研究问题重要", "面板模型不能自动解决时间变化的混杂"],
    },
    {
        "id": "LOCAL-METHOD-CASE-QUALITATIVE",
        "title": "案例研究、质化分析与归纳建构",
        "aliases": ["案例研究", "质化研究", "扎根理论", "编码", "访谈", "case study", "qualitative", "grounded theory"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch09"), ("METHOD-IACMR-EMPIRICAL-2018", "ch10"), ("METHOD-IACMR-EMPIRICAL-2008", "ch10")],
        "use_when": "研究过程、机制、新现象或情境嵌入问题，需要深度现场材料和归纳理论。",
        "core_actions": ["说明案例为何能回答研究问题", "规划案例选择、进入现场和多源证据", "建立可审计的数据管理和编码过程", "在开放、轴心、选择性编码或其他分析之间说明逻辑", "把证据、概念和理论主张清晰连接"],
        "warnings": ["案例描述不等于案例研究", "编码标签不能替代理论解释", "研究者角色、反例和替代解释必须被处理"],
    },
    {
        "id": "LOCAL-METHOD-META-ANALYSIS",
        "title": "元分析与证据综合",
        "aliases": ["元分析", "效应量", "发表偏差", "异质性", "Meta-SEM", "meta analysis", "effect size"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch11")],
        "use_when": "同一关系已有足量可比实证研究，需要估计总体效应、异质性或调节因素。",
        "core_actions": ["制定可复现检索和纳入排除标准", "定义效应量和独立性处理", "建立双人或可核查的编码规则", "根据异质性选择估计模型并检验调节", "评估发表偏差、敏感性和语言覆盖"],
        "warnings": ["元分析不是只统计显著研究", "同一样本多篇论文会破坏独立性", "构念不等价时不能机械合并效应"],
    },
    {
        "id": "LOCAL-METHOD-CONTEXTUALIZATION",
        "title": "中国情境、情境化与跨文化研究",
        "aliases": ["情境化", "中国情境", "本土理论", "跨文化", "测量等价性", "contextualization", "cross cultural", "emic", "etic"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch12"), ("METHOD-IACMR-EMPIRICAL-2008", "ch04"), ("METHOD-IACMR-EMPIRICAL-2008", "ch17"), ("METHOD-IACMR-EMPIRICAL-2008", "ch20")],
        "use_when": "研究结论依赖国家、文化、制度、产业或平台情境，或需要比较不同情境。",
        "core_actions": ["判断现象是情境无关、情境嵌入还是情境敏感", "说明情境进入理论的机制而非只作为样本标签", "区分主位与客位研究取向", "验证概念和测量等价性", "谨慎界定跨情境普适化范围"],
        "warnings": ["更换到中国样本本身不是贡献", "不同文化的均值差异不能自动证明文化机制", "缺乏测量等价性时组间比较可能无效"],
    },
    {
        "id": "LOCAL-METHOD-MEASUREMENT",
        "title": "构念测量、量表开发与效度",
        "aliases": ["构念测量", "量表开发", "内容效度", "聚合效度", "区分效度", "信度", "measurement", "scale development"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch13"), ("METHOD-IACMR-EMPIRICAL-2018", "ch14"), ("METHOD-IACMR-EMPIRICAL-2008", "ch11"), ("METHOD-IACMR-EMPIRICAL-2008", "ch12")],
        "use_when": "需要采用、翻译、修改或新开发构念量表，或判断反映式/构成式和维度结构。",
        "core_actions": ["先给出构念定义、边界和层级", "建立题项生成与内容效度证据", "检验内部结构、信度、聚合与区分效度", "区分效果指标与构成指标", "为多维构念说明维度关系和计分方式"],
        "warnings": ["高Cronbach alpha不能单独证明效度", "删题不能只以统计拟合为依据", "反映式与构成式设定错误会改变模型含义"],
    },
    {
        "id": "LOCAL-METHOD-SEM",
        "title": "CFA与结构方程模型",
        "aliases": ["结构方程模型", "CFA", "SEM", "测量模型", "路径模型", "拟合指数", "Mplus"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch15"), ("METHOD-IACMR-EMPIRICAL-2018", "ch13"), ("METHOD-IACMR-EMPIRICAL-2008", "ch13")],
        "use_when": "理论包含潜变量、测量误差和多条关系，需要同时评价测量模型与结构模型。",
        "core_actions": ["先确认构念和指标关系", "区分测量模型、路径模型和全模型", "报告识别、估计方法、拟合和替代模型", "将模型修改限制在理论可解释范围", "分别解释测量质量和结构关系"],
        "warnings": ["良好拟合不证明理论为真", "不能只依赖单一拟合指数", "用同一数据反复修改并确认模型会造成过拟合"],
    },
    {
        "id": "LOCAL-METHOD-MODERATION-MEDIATION",
        "title": "调节、中介与条件过程",
        "aliases": ["调节变量", "中介变量", "被调节的中介", "被中介的调节", "交互作用", "moderation", "mediation", "conditional process"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch16"), ("METHOD-IACMR-EMPIRICAL-2018", "ch22"), ("METHOD-IACMR-EMPIRICAL-2008", "ch14")],
        "use_when": "理论需要说明作用机制、边界条件或两者的组合，并计划进行单层或多层检验。",
        "core_actions": ["先用理论区分机制和边界", "明确调节发生在哪一条路径", "估计交互和间接效应并报告不确定性", "根据层级选择单层或多层条件过程模型", "使用简单斜率或条件效应解释结果"],
        "warnings": ["显著中介不能仅凭逐步回归判断", "横截面中介通常不能确认时间因果顺序", "复杂模型必须有理论必要性而非追求统计新颖"],
    },
    {
        "id": "LOCAL-METHOD-MULTILEVEL",
        "title": "多层次理论、聚合与HLM",
        "aliases": ["多层次", "HLM", "聚合", "跨层", "中心化", "multilevel", "hierarchical linear model"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch17"), ("METHOD-IACMR-EMPIRICAL-2018", "ch21"), ("METHOD-IACMR-EMPIRICAL-2018", "ch22"), ("METHOD-IACMR-EMPIRICAL-2008", "ch15")],
        "use_when": "个体嵌套于团队/组织，或高频重复测量嵌套于个体，需要构建跨层机制。",
        "core_actions": ["区分理论层级、测量层级和分析层级", "为聚合提供概念和统计证据", "选择中心化策略并说明含义", "检查组数、组内样本和方差结构", "将跨层调节/中介与时间结构明确化"],
        "warnings": ["把聚类标准误当作完整多层理论不足够", "中心化选择会改变系数含义", "第二层样本过少会造成不稳定估计"],
    },
    {
        "id": "LOCAL-METHOD-LONGITUDINAL",
        "title": "纵向、面板与动态研究",
        "aliases": ["纵向研究", "固定效应", "随机效应", "动态", "longitudinal", "fixed effects", "random effects"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch18"), ("METHOD-IACMR-EMPIRICAL-2018", "ch21")],
        "use_when": "研究变化、先后顺序、个体/组织内效应或动态过程。",
        "core_actions": ["明确时间单位、波次和理论滞后", "区分个体内与个体间变异", "依据误差与未观测异质性假设选择固定/随机效应", "处理缺失、流失、序列相关和时间趋势", "限制对动态因果的表述"],
        "warnings": ["只有两个时间点时动态机制证据有限", "固定效应不能估计时间不变变量的直接效应", "任意选择滞后长度会产生研究者自由度"],
    },
    {
        "id": "LOCAL-METHOD-EVENT-HISTORY",
        "title": "事件历史与生存分析",
        "aliases": ["事件历史", "生存分析", "风险率", "删失", "Cox", "event history", "survival analysis", "hazard"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch19")],
        "use_when": "因变量是某事件是否以及何时发生，如采用、退出、失败、晋升或合作终止。",
        "core_actions": ["定义客体、事件、起始时间和风险集", "处理右删失和时间变化协变量", "选择离散/连续时间与比例风险等模型", "检验核心模型假设", "报告时间尺度和事件重复规则"],
        "warnings": ["只分析已发生事件会产生选择偏差", "不同时间起点不可随意混用", "比例风险假设不满足时需调整模型"],
    },
    {
        "id": "LOCAL-METHOD-EVENT-STUDY",
        "title": "资本市场事件研究",
        "aliases": ["事件研究法", "异常收益", "事件窗", "公告效应", "event study", "abnormal return"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch20")],
        "use_when": "评估公告、政策或组织事件对证券市场价值的短期影响。",
        "core_actions": ["定义事件日、估计窗和事件窗", "选择正常收益模型和基准", "处理事件重叠、泄露和同期事件", "检验异常收益及稳健性", "说明市场有效性等核心假定"],
        "warnings": ["事件日不准确会污染估计", "长事件窗更容易混入其他信息", "市场反应不能自动解释具体组织机制"],
    },
    {
        "id": "LOCAL-METHOD-ESM",
        "title": "日记法与体验抽样",
        "aliases": ["日记法", "体验抽样", "ESM", "高频跟踪", "密集纵向", "diary study", "experience sampling"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch21"), ("METHOD-IACMR-EMPIRICAL-2018", "ch17")],
        "use_when": "研究短期波动、情绪、认知、行为和人机互动的日内或日际动态。",
        "core_actions": ["选择时距、信号、事件或混合触发方式", "规划测量频率、持续期和参与负担", "设计招募、培训、提醒和激励", "使用多层或密集纵向分析", "记录依从率、时间戳和缺失机制"],
        "warnings": ["高频测量可能反过来改变被测行为", "低依从率和非随机漏答会偏倚结果", "题项必须足够短但仍保持测量质量"],
    },
    {
        "id": "LOCAL-METHOD-WRITING-PUBLICATION",
        "title": "论文写作、投稿、审稿与修改",
        "aliases": ["论文写作", "摘要", "导言", "讨论", "投稿", "审稿意见", "修改说明", "academic writing", "peer review", "revision"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2018", "ch23"), ("METHOD-IACMR-EMPIRICAL-2018", "intro"), ("METHOD-IACMR-EMPIRICAL-2008", "ch18"), ("METHOD-IACMR-EMPIRICAL-2008", "ch19"), ("METHOD-IACMR-EMPIRICAL-2008", "ch20")],
        "use_when": "根据已选研究问题和设计生成开题/论文结构，或准备投稿、回复审稿和修改。",
        "core_actions": ["题目和摘要准确呈现问题、设计和贡献", "导言围绕问题、既有解释不足和新答案推进", "方法部分保证可评估和可复制", "讨论区分发现、解释、贡献、局限和边界", "逐条、可追踪地回复编辑与审稿意见"],
        "warnings": ["写作不能掩盖设计和证据缺陷", "不得补写来源中不存在的方法或结果", "用户未选择研究空白和创新点前不能生成完整开题"],
    },
    {
        "id": "LOCAL-METHOD-SOCIAL-CAPITAL",
        "title": "组织社会资本的分类与测量",
        "aliases": ["社会资本", "关系网络", "信任", "网络位置", "social capital", "network ties"],
        "sources": [("METHOD-IACMR-EMPIRICAL-2008", "ch16")],
        "use_when": "研究个人、团队或组织的关系资源、信任、网络连带和结构位置。",
        "core_actions": ["明确个体、集体和组织间层级", "区分关系面与结构面社会资本", "让网络数据、感知量表和结果变量与理论层级一致", "分别说明组织内与组织外关系", "避免把所有关系变量合并为单一社会资本指数"],
        "warnings": ["该专题来自2008版，应结合当前网络方法与领域文献更新", "关系数量不等于关系质量", "横截面网络与绩效关系容易受到反向因果影响"],
    },
]

PARADIGM_SOURCE_MAP = {
    "quantitative_archival_causal": {
        "coverage": "substantial_local",
        "refs": ["2018:ch04", "2018:ch06", "2018:ch08", "2018:ch18", "2018:ch19", "2018:ch20"],
        "limits": ["现代DiD、RDD、IV和合成控制需要其他本地来源"],
    },
    "survey_sem": {
        "coverage": "substantial_local",
        "refs": ["2018:ch07", "2018:ch13", "2018:ch14", "2018:ch15", "2018:ch16", "2018:ch17", "2018:ch22"],
        "limits": ["最新软件语法和新估计方法仍需版本化补充"],
    },
    "experiment": {
        "coverage": "substantial_local",
        "refs": ["2018:ch05", "2018:ch06", "2018:ch21"],
        "limits": ["平台级A/B测试工程、序贯检验和现代在线实验治理需其他来源"],
    },
    "qualitative_case_process": {
        "coverage": "substantial_local",
        "refs": ["2018:ch09", "2018:ch10", "2018:ch12"],
        "limits": ["过程理论和特定质化流派需另建专题卡"],
    },
    "systematic_review_bibliometric": {
        "coverage": "partial_local",
        "refs": ["2018:ch11"],
        "limits": ["覆盖元分析；PRISMA、科学计量和知识图谱流程未由这两本书完整覆盖"],
    },
    "mixed_methods": {
        "coverage": "partial_local",
        "refs": ["2018:ch04", "2018:ch09", "2018:ch10", "2018:ch12"],
        "limits": ["未提供完整混合方法设计类型和整合标准"],
    },
    "computational_text_network": {
        "coverage": "partial_local",
        "refs": ["2018:ch08", "2018:ch10", "2008:ch16"],
        "limits": ["NLP、机器学习、现代网络建模和可复现计算流程需其他来源"],
    },
    "analytical_modeling": {
        "coverage": "not_covered_by_books",
        "refs": [],
        "limits": ["博弈论、优化、信息经济学和机制设计需独立本地知识源"],
    },
    "design_science": {
        "coverage": "not_covered_by_books",
        "refs": [],
        "limits": ["设计科学研究循环、制品评价和设计理论需独立本地知识源"],
    },
}

CHINESE_NUM = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def chinese_to_int(s: str) -> int:
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if "十" in s:
        left, right = s.split("十", 1)
        tens = CHINESE_NUM.get(left, 1) if left else 1
        ones = CHINESE_NUM.get(right, 0) if right else 0
        return tens * 10 + ones
    if len(s) == 1 and s in CHINESE_NUM:
        return CHINESE_NUM[s]
    raise ValueError(f"Unsupported Chinese numeral: {s}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def dump_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")


def parse_toc(lines: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for idx, line in enumerate(lines[:240], start=1):
        if line.strip() == "---":
            break
        m = re.match(r"^(\s*)- \[(.+?)\]\(#pdf-page-(\d+)\)（PDF页\s*(\d+)）", line)
        if not m:
            continue
        indent, title, anchor_page, printed_page = m.groups()
        item_id: str | None = None
        chapter_num: int | None = None
        if title.startswith("引言"):
            item_id = "intro"
        else:
            cm = re.match(r"第([0-9一二三四五六七八九十]+)章\s*(.+)", title)
            if cm:
                chapter_num = chinese_to_int(cm.group(1))
                item_id = f"ch{chapter_num:02d}"
            else:
                am = re.match(r"附录([0-9一二三四五六七八九十]+)\s*(.*)", title)
                if am:
                    chapter_num = chinese_to_int(am.group(1))
                    item_id = f"appendix_{chapter_num:02d}"
        if item_id:
            entries.append({
                "id": item_id,
                "chapter_num": chapter_num,
                "title": title,
                "anchor_page": int(anchor_page),
                "printed_page": int(printed_page),
                "toc_line": idx,
                "indent": len(indent),
            })
    # De-duplicate by ID while preserving first TOC entry.
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in sorted(entries, key=lambda x: x["anchor_page"]):
        if entry["id"] not in seen:
            out.append(entry)
            seen.add(entry["id"])
    return out


def find_anchor_line(lines: list[str], page: int) -> int:
    needle = f'<a id="pdf-page-{page}"></a>'
    for i, line in enumerate(lines, start=1):
        if line.strip() == needle:
            return i
    raise ValueError(f"Missing page anchor {page}")


def meta_for(year: int, item_id: str, title: str) -> dict[str, Any]:
    if item_id == "intro":
        key: Any = "intro"
    elif item_id.startswith("ch"):
        key = int(item_id[2:])
    else:
        return {"slug": item_id, "tags": ["appendix"], "summary": f"{title}。作为术语、伦理或经典文献补充材料使用。"}
    mapping = META_2018 if year == 2018 else META_2008
    return mapping.get(key, {"slug": item_id, "tags": ["empirical_methods"], "summary": f"{title}的本地章节。"})


def safe_slug(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")
    return text.lower() or "section"


def split_long_line(text: str, max_len: int = 680) -> list[str]:
    text = text.strip()
    if not text:
        return []
    # Preserve sentence punctuation in chunks.
    pieces = re.split(r"(?<=[。！？；!?])", text)
    out: list[str] = []
    buf = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if len(piece) > max_len:
            if buf:
                out.append(buf)
                buf = ""
            for start in range(0, len(piece), max_len):
                out.append(piece[start:start + max_len])
        elif len(buf) + len(piece) + 1 <= max_len:
            buf = f"{buf}{piece}" if buf else piece
        else:
            if buf:
                out.append(buf)
            buf = piece
    if buf:
        out.append(buf)
    return out


def build_chunks(
    resource_id: str,
    edition: int,
    entry: dict[str, Any],
    chapter_lines: list[tuple[int, str]],
    chapter_path: str,
    tags: list[str],
    priority: str,
    source_dir: Path,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current_page = entry["anchor_page"]
    current_section = entry["title"]
    image_pat = re.compile(r"!\[(.*?)\]\((.*?)\)")
    for line_no, raw in chapter_lines:
        stripped = raw.strip()
        am = re.match(r'<a id="pdf-page-(\d+)"></a>', stripped)
        if am:
            current_page = int(am.group(1))
            continue
        if stripped.startswith("<!-- PDF页") or not stripped:
            continue
        if stripped.startswith("#"):
            current_section = re.sub(r"^#+\s*", "", stripped).strip()
            continue
        im = image_pat.search(stripped)
        if im:
            image_path = source_dir / Path(im.group(2))
            image_available = image_path.is_file()
            blocks.append({
                "text": (
                    f"【图表资产已入库】{im.group(1)}；本地引用路径：{im.group(2)}。"
                    if image_available
                    else f"【图表资产未随Markdown上传】{im.group(1)}；原引用路径：{im.group(2)}。"
                ),
                "page": current_page,
                "line_start": line_no,
                "line_end": line_no,
                "section": current_section,
                "asset_missing": not image_available,
            })
            continue
        for piece in split_long_line(stripped):
            blocks.append({
                "text": piece,
                "page": current_page,
                "line_start": line_no,
                "line_end": line_no,
                "section": current_section,
                "asset_missing": False,
            })

    chunks: list[dict[str, Any]] = []
    target = 1150
    min_flush = 500
    buf: list[dict[str, Any]] = []
    size = 0

    def flush() -> None:
        nonlocal buf, size
        if not buf:
            return
        seq = len(chunks) + 1
        section = buf[0]["section"] if all(x["section"] == buf[0]["section"] for x in buf) else f"{buf[0]['section']} → {buf[-1]['section']}"
        content = "\n".join(x["text"] for x in buf)
        chunk_id = f"{resource_id}__{entry['id']}__{seq:04d}"
        chunks.append({
            "chunk_id": chunk_id,
            "resource_id": resource_id,
            "edition_year": edition,
            "source_priority": priority,
            "chapter_id": entry["id"],
            "chapter_title": entry["title"],
            "section": section,
            "pdf_page_start": min(x["page"] for x in buf),
            "pdf_page_end": max(x["page"] for x in buf),
            "source_line_start": min(x["line_start"] for x in buf),
            "source_line_end": max(x["line_end"] for x in buf),
            "local_path": chapter_path,
            "tags": tags,
            "asset_missing": any(x["asset_missing"] for x in buf),
            "char_count": len(content),
            "content_sha256": sha256_bytes(content.encode("utf-8")),
            "citation_anchor": f"{resource_id}#pdf-page-{min(x['page'] for x in buf)}",
            "content": content,
        })
        buf = []
        size = 0

    for block in blocks:
        section_changed = bool(buf) and block["section"] != buf[-1]["section"]
        if section_changed and size >= min_flush:
            flush()
        if buf and size + len(block["text"]) > target and size >= min_flush:
            flush()
        buf.append(block)
        size += len(block["text"])
    flush()
    return chunks


def build_sqlite(db_path: Path, chunks: list[dict[str, Any]]) -> None:
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA journal_mode=OFF")
        con.execute("PRAGMA synchronous=OFF")
        con.execute(
            """
            CREATE VIRTUAL TABLE chunks_fts USING fts5(
                chunk_id UNINDEXED,
                resource_id UNINDEXED,
                edition_year UNINDEXED,
                source_priority UNINDEXED,
                chapter_id UNINDEXED,
                pdf_page_start UNINDEXED,
                pdf_page_end UNINDEXED,
                local_path UNINDEXED,
                chapter_title,
                section,
                tags,
                content,
                tokenize='trigram'
            )
            """
        )
        rows = [(
            c["chunk_id"], c["resource_id"], str(c["edition_year"]), c["source_priority"], c["chapter_id"],
            str(c["pdf_page_start"]), str(c["pdf_page_end"]), c["local_path"], c["chapter_title"], c["section"],
            " ".join(c["tags"]), c["content"]
        ) for c in chunks]
        con.executemany("INSERT INTO chunks_fts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        con.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        con.executemany("INSERT INTO metadata(key,value) VALUES (?,?)", [
            ("generated_on", TODAY),
            ("chunk_count", str(len(chunks))),
            ("tokenizer", "fts5_trigram"),
            ("retrieval_policy", "local_first"),
        ])
        con.commit()
    finally:
        con.close()


def update_source_registry(root: Path, local_catalog_rel: str, local_db_rel: str) -> None:
    path = root / "03_sources/source_registry.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["version"] = data.get("version", "0.3.0")
    data["verified_on"] = TODAY
    data["rule"] = "运行时优先读取本地知识卡和本地全文索引；外部链接仅用于维护、版本核验或本地覆盖缺失时的显式兜底，不得在每次任务启动时自动抓取。"
    data.setdefault("runtime_policy", {}).update({
        "fetch_external_links_on_startup": False,
        "retrieval_order": ["local_topic_router", "local_cards", "local_fts", "structured_registry", "external_fallback"],
        "external_fallback_triggers": ["local_coverage_missing", "time_sensitive_rule_stale", "source_version_verification_required", "missing_image_or_formula_asset"],
        "local_catalog": local_catalog_rel,
        "local_fts": local_db_rel,
    })
    # Rebuild local book records deterministically on every run.
    data["resources"] = [r for r in data.get("resources", []) if r.get("id") not in BOOKS]
    # v0.3 external resources already have audited local cards. Preserve those
    # records instead of downgrading them during a local-book rebuild.

    new_resources = []
    for rid, book in BOOKS.items():
        base = f"03_sources/local_knowledge/books/{rid}"
        images_dir = root / base / "images"
        image_count = sum(1 for path in images_dir.glob("*") if path.is_file()) if images_dir.exists() else 0
        new_resources.append({
            "id": rid,
            "title": book["title"],
            "domain": ["research_design", "empirical_methods", "management", "IS", "IM"],
            "type": "book_user_supplied_local",
            "level": "foundational_local",
            "access": "private_user_supplied_copy",
            "url": None,
            "bibliographic": {
                "editors": book["editors"],
                "publisher": book["publisher"],
                "year": book["year"],
                "isbn": book["isbn"],
            },
            "use": ["研究问题与开题", "实证研究设计", "问卷/实验/案例/二手数据", "测量与统计方法", "论文写作与发表"],
            "extract": ["章节级知识", "方法路由", "设计检查项", "常见误用", "页码证据"],
            "local": {
                "status": "fulltext_chaptered_chunked_indexed",
                "runtime_fetch": "not_required",
                "rights": "user_supplied_private_research_copy",
                "fulltext_path": f"{base}/source.md",
                "metadata_path": f"{base}/metadata.yaml",
                "chapter_index_path": f"{base}/chapter_index.yaml",
                "chapters_path": f"{base}/chapters/",
                "portable_chunks": "03_sources/local_knowledge/index/chunks.jsonl",
                "fts_index": local_db_rel,
                "topic_router": "03_sources/local_knowledge/index/method_topic_router.yaml",
                "text_quality": "ocr_corrected_markdown_with_residual_noise",
                "image_assets": {
                    "status": "complete_private_local" if image_count else "not_included_in_upload",
                    "path": f"{base}/images/" if image_count else None,
                    "count": image_count,
                },
                "edition_priority": book["priority"],
            },
        })
    data["resources"].extend(new_resources)
    dump_yaml(path, data)


def update_text_files(root: Path) -> None:
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = text.replace("知识库启动包 v0.1", "知识库启动包 v0.2")
    text = text.replace("版本定位：**最小可用知识库（MVP）**。它已经能约束 Agent 的检索、验证、归纳与生成行为，但不包含受版权保护的书籍全文，也不包含预先抓取的论文全文库。",
                        "版本定位：**本地优先的最小可用知识库（MVP）**。它已加入两本由创建者提供的管理实证方法书，完成全文保留、章节拆分、结构化知识卡、JSONL切块和SQLite FTS索引。其他未本地化来源仍保持显式缺口状态。")
    text = text.replace("10. 写作指导必须引用 `04_paradigms/`、`05_methods/` 和 `03_sources/source_registry.yaml` 中已验证的资源。",
                        "10. 写作指导先读取 `03_sources/local_knowledge/index/method_topic_router.yaml` 与本地方法卡，再按需检索 `local_fts.sqlite`；只有本地覆盖缺失或规则过期时才使用外部来源。")
    insertion = """

## 4. 本地优先知识层（v0.2新增）

运行时不得遍历 `source_registry.yaml` 中的URL并逐个抓取。正确顺序是：

1. 精确读取 `03_sources/local_knowledge/index/method_topic_router.yaml`；
2. 读取匹配的 `cards/*.md`；
3. 需要细节时调用 `11_implementation/local_retrieval.py` 查询 SQLite FTS；
4. 只有 `local_coverage_missing`、时效规则过期或图表资产缺失时才进入外部检索；
5. 外部补充必须被缓存、登记和版本化，不能每次任务重复搜索。

两本书的本地全文属于创建者提供的私人研究副本。公开部署时，默认只向最终用户暴露结构化知识卡和短证据片段，不提供整章或整书下载。
"""
    marker = "## 4. 你需要自己补充的内容"
    if marker in text:
        text = text.replace(marker, insertion + "\n" + marker.replace("## 4.", "## 5."))
        text = text.replace("## 5. 文件说明", "## 6. 文件说明")
        text = text.replace("## 6. 当前覆盖边界", "## 7. 当前覆盖边界")
    write_text(readme, text)

    retrieval = root / "09_agent_contract/retrieval_rules.md"
    rtext = retrieval.read_text(encoding="utf-8")
    local_rules = """# 检索 Agent 规则

## 本地优先门禁

1. 启动任务时禁止自动访问 `03_sources/source_registry.yaml` 中的外部URL。
2. 先查 `local_source_catalog.yaml` 和 `method_topic_router.yaml`；匹配后先读本地知识卡。
3. 只有知识卡不足以回答具体设计问题时，才查询本地 SQLite FTS 原文块。
4. 2018第三版为首选；2008版用于版本对照及中国理论建构、组织社会资本、跨文化研究和发表历程等补充专题。
5. 本地覆盖状态为 `not_covered_by_books` 或 `pointer_only` 时，才能触发外部兜底；触发原因必须写入日志。
6. 期刊等级、投稿规则、API和软件版本属于时效内容，应由维护任务定期刷新缓存，而不是由每个用户任务现场搜索。
7. 若检索块标记 `asset_missing=true` 且判断依赖图表、公式或版式，停止该细节判断，不得自行重建缺失内容。

## 论文检索规则
"""
    if "## 本地优先门禁" not in rtext:
        # Replace the initial heading and preserve the prior rules under the new local section.
        old = rtext.split("\n", 1)[1] if "\n" in rtext else ""
        write_text(retrieval, local_rules + old.lstrip())

    contract = root / "09_agent_contract/system_contract.md"
    ctext = contract.read_text(encoding="utf-8")
    ctext = ctext.replace("- 知识库缺少研究范式时，明确告知并现场检索权威来源；",
                          "- 知识库缺少研究范式时，先确认本地路由、知识卡和全文索引均无覆盖，再明确告知并检索权威来源；")
    ctext = ctext.replace("- 新检索到的范式资料必须带来源、访问日期和状态，不能无痕写入；",
                          "- 新检索到的范式资料必须被缓存到本地、带来源、访问日期和状态，不能无痕写入，也不能在后续任务中重复现场搜索；")
    local_clause = """

## 本地知识运行约束

- 外部URL是维护指针，不是启动时读取清单；
- 稳定方法知识优先使用本地方法卡和本地原文索引；
- 查询详细方法时，必须返回 `resource_id/chapter_id/pdf_page`；
- 2018第三版优先，2008版为补充，不得把旧版软件或期刊信息当成当前规则；
- 若本地OCR文本存在歧义或缺失图表，降低结论强度并报告资产缺口。
"""
    if "## 本地知识运行约束" not in ctext:
        ctext += local_clause
    write_text(contract, ctext)

    ingestion = root / "11_implementation/ingestion_pipeline.md"
    itext = ingestion.read_text(encoding="utf-8")
    itext = itext.replace("2. 不复制全文，先建立章节目录和待抽取知识单元；",
                          "2. 对未授权商业材料不复制全文；对创建者合法提供的私人研究副本，可在私有知识库中保留全文并记录授权范围；")
    itext = itext.replace("3. 人工阅读后为每个独立概念生成理论卡/方法卡/写作卡；",
                          "3. 生成章节文件、页码/行号可追溯切块、本地检索索引，并为高频主题建立理论卡/方法卡/写作卡；")
    if "## E. 本地全文入库（创建者提供）" not in itext:
        itext += """

## E. 本地全文入库（创建者提供）

1. 原文文件只读保留，并计算SHA-256；
2. 以目录页的PDF页码锚点拆分章节；
3. 每个chunk记录来源、章节、PDF页、原始行号、标签、哈希和缺失资产状态；
4. 用SQLite FTS5 trigram建立中文/英文全文索引；
5. 先检索主题卡，再检索原文块，避免把整本书送入模型上下文；
6. 任何公开部署不得向最终用户批量导出受版权保护全文。
"""
    write_text(ingestion, itext)

    copyright_file = root / "00_governance/copyright_and_storage_policy.md"
    cptext = copyright_file.read_text(encoding="utf-8")
    if "## 5. 创建者提供的私人副本" not in cptext:
        cptext += """

## 5. 创建者提供的私人副本

本知识库可保存创建者主动提供、且其有权用于私人研究的全文材料。此类文件必须标记为 `user_supplied_private_research_copy`：

- 仅用于平台内部检索和生成结构化方法指导；
- 不向平台用户提供整章、整书或批量逐字导出；
- 对外部署前应确认许可范围；未获得再分发授权时，只部署自建知识卡、索引元数据和合理长度的证据片段；
- OCR文本或缺失图表不能被视为权威版式，涉及公式和图表细节时必须回到完整合法副本核验。
"""
    write_text(copyright_file, cptext)

    stop_path = root / "00_governance/scope_and_stop_rules.yaml"
    stop = yaml.safe_load(stop_path.read_text(encoding="utf-8"))
    if not any(r.get("code") == "LOCAL_SOURCE_ASSET_MISSING" for r in stop["rules"]):
        stop["rules"].insert(-1, {
            "code": "LOCAL_SOURCE_ASSET_MISSING",
            "severity": "pause_for_claim",
            "trigger": "本地OCR来源所需的图、表、公式或版式资产未随Markdown上传，且当前判断依赖该资产。",
            "required_action": "报告resource_id、章节和PDF页；不得依据文字占位符重建图表或公式。改用不依赖该资产的文字证据，或由创建者补充合法图像资产。",
            "resume_condition": "获得对应合法资产，或将判断限定为现有文字能够支持的范围。",
        })
    dump_yaml(stop_path, stop)


def update_manifest_and_coverage(root: Path, book_chunk_count: int, external_chunk_count: int) -> None:
    manifest_path = root / "kb_manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = manifest.get("version", "0.3.0")
    manifest["released_on"] = TODAY
    manifest.setdefault("local_first", {}).update({
        "enabled": True,
        "startup_external_fetch": False,
        "local_source_catalog": "03_sources/local_knowledge/index/local_source_catalog.yaml",
        "topic_router": "03_sources/local_knowledge/index/method_topic_router.yaml",
        "book_chunks": "03_sources/local_knowledge/index/chunks.jsonl",
        "fts_index": "03_sources/local_knowledge/index/local_fts.sqlite",
        "search_cli": "11_implementation/local_retrieval.py",
        "chunk_count": book_chunk_count + external_chunk_count,
        "book_chunk_count": book_chunk_count,
        "external_chunk_count": external_chunk_count,
    })
    manifest["entrypoints"]["local_sources"] = "03_sources/local_knowledge/index/local_source_catalog.yaml"
    manifest["entrypoints"]["local_method_router"] = "03_sources/local_knowledge/index/method_topic_router.yaml"
    dump_yaml(manifest_path, manifest)

    coverage_path = root / "coverage_status.yaml"
    coverage = yaml.safe_load(coverage_path.read_text(encoding="utf-8"))
    coverage["as_of"] = TODAY
    coverage["modules"] = [m for m in coverage["modules"] if m["module"] not in {"local_empirical_books", "local_fulltext_retrieval"}]
    coverage["modules"].extend([
        {"module": "local_empirical_books", "status": "complete", "notes": "2008版与2018第三版已保留全文、章节拆分、主题卡和页码/行号溯源；2018优先、2008补充。"},
        {"module": "local_fulltext_retrieval", "status": "complete", "notes": f"已建立JSONL与SQLite FTS5 trigram索引，共{book_chunk_count}个本地原文块。"},
    ])
    coverage["next_priority"] = [
        item for item in coverage.get("next_priority", [])
        if "missing figure assets" not in item.lower() and "images资产" not in item
    ]
    dump_yaml(coverage_path, coverage)


def write_local_retrieval_script(root: Path) -> None:
    script = r'''#!/usr/bin/env python3
"""Search the local empirical-methods FTS index without web access."""
from __future__ import annotations
import argparse
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "03_sources/local_knowledge/index/local_fts.sqlite"


def make_match(query: str) -> str:
    terms = re.findall(r"[\u4e00-\u9fff]{3,}|[A-Za-z0-9][A-Za-z0-9_+./-]{2,}", query)
    if not terms:
        return ""
    return " AND ".join('"' + t.replace('"', '""') + '"' for t in terms[:8])


def search(query: str, limit: int, resource_id: str | None, chapter_id: str | None):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        match = make_match(query)
        filters = []
        params = []
        if resource_id:
            filters.append("resource_id = ?")
            params.append(resource_id)
        if chapter_id:
            filters.append("chapter_id = ?")
            params.append(chapter_id)
        where_filters = (" AND " + " AND ".join(filters)) if filters else ""
        if match:
            sql = f"""
                SELECT chunk_id, resource_id, edition_year, source_priority, chapter_id,
                       pdf_page_start, pdf_page_end, local_path, chapter_title, section,
                       snippet(chunks_fts, 11, '【', '】', '…', 28) AS snippet,
                       bm25(chunks_fts, 0,0,0,0,0,0,0,0, 4.0,3.0,2.0,1.0) AS score
                FROM chunks_fts
                WHERE chunks_fts MATCH ? {where_filters}
                ORDER BY CASE source_priority WHEN 'primary' THEN 0 ELSE 1 END,
                         CASE WHEN chapter_id LIKE 'ch%' OR chapter_id = 'intro' THEN 0 ELSE 1 END,
                         score
                LIMIT ?
            """
            rows = con.execute(sql, [match, *params, limit]).fetchall()
        else:
            # FTS trigram requires 3-character tokens; use LIKE for very short queries.
            sql = f"""
                SELECT chunk_id, resource_id, edition_year, source_priority, chapter_id,
                       pdf_page_start, pdf_page_end, local_path, chapter_title, section,
                       substr(content, max(instr(content, ?)-80, 1), 320) AS snippet,
                       0.0 AS score
                FROM chunks_fts
                WHERE (content LIKE ? OR section LIKE ? OR chapter_title LIKE ?) {where_filters}
                ORDER BY CASE source_priority WHEN 'primary' THEN 0 ELSE 1 END,
                         CASE WHEN chapter_id LIKE 'ch%' OR chapter_id = 'intro' THEN 0 ELSE 1 END
                LIMIT ?
            """
            like = f"%{query}%"
            rows = con.execute(sql, [query, like, like, like, *params, limit]).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("query", nargs="?")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--resource-id")
    p.add_argument("--chapter-id")
    p.add_argument("--json", action="store_true")
    p.add_argument("--stats", action="store_true")
    args = p.parse_args()
    if args.stats:
        con = sqlite3.connect(DB)
        try:
            total = con.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
            resources = dict(con.execute("SELECT resource_id, COUNT(*) FROM chunks_fts GROUP BY resource_id"))
        finally:
            con.close()
        print(json.dumps({"chunks": total, "resources": resources}, ensure_ascii=False, indent=2))
        return
    if not args.query:
        p.error("query is required unless --stats is used")
    rows = search(args.query, args.limit, args.resource_id, args.chapter_id)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    for i, row in enumerate(rows, 1):
        print(f"[{i}] {row['chapter_title']} | {row['section']} | PDF {row['pdf_page_start']}-{row['pdf_page_end']}")
        print(f"    {row['resource_id']} / {row['chapter_id']} / {row['chunk_id']}")
        print(f"    {row['snippet']}\n")

if __name__ == "__main__":
    main()
'''
    path = root / "11_implementation/local_retrieval.py"
    write_text(path, script)
    path.chmod(0o755)


def build_checksums(root: Path) -> None:
    files = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "checksums.json"):
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        files[rel] = sha256_bytes(data)
    write_text(root / "checksums.json", json.dumps(files, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--input-dir", type=Path, required=True)
    args = ap.parse_args()
    root = args.root.resolve()
    input_dir = args.input_dir.resolve()
    local_root = root / "03_sources/local_knowledge"
    books_root = local_root / "books"
    index_root = local_root / "index"
    cards_root = local_root / "cards"
    for p in (books_root, index_root, cards_root):
        p.mkdir(parents=True, exist_ok=True)

    all_chunks: list[dict[str, Any]] = []
    catalog_resources: list[dict[str, Any]] = []
    chapter_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    missing_assets: list[dict[str, Any]] = []

    for rid, book in BOOKS.items():
        source_path = input_dir / book["input_name"]
        if not source_path.exists():
            fallback = books_root / rid / "source.md"
            if fallback.exists():
                source_path = fallback
            else:
                raise FileNotFoundError(source_path)
        raw = source_path.read_text(encoding="utf-8")
        lines = raw.splitlines()
        toc = parse_toc(lines)
        if not toc:
            raise ValueError(f"No TOC entries parsed: {source_path}")
        source_dir = books_root / rid
        chapters_dir = source_dir / "chapters"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        destination = source_dir / "source.md"
        if source_path.resolve() != destination.resolve():
            shutil.copy2(source_path, destination)

        image_refs = []
        for line_no, line in enumerate(lines, start=1):
            for m in re.finditer(r"!\[(.*?)\]\((.*?)\)", line):
                page_match = re.search(r"PDF第(\d+)页", m.group(1))
                asset_path = source_dir / Path(m.group(2))
                item = {
                    "resource_id": rid,
                    "source_line": line_no,
                    "pdf_page": int(page_match.group(1)) if page_match else None,
                    "alt": m.group(1),
                    "relative_path": m.group(2),
                    "status": "available_local" if asset_path.is_file() else "missing_from_upload",
                }
                image_refs.append(item)
                if not asset_path.is_file():
                    missing_assets.append(item)

        entries_out = []
        for i, entry in enumerate(toc):
            start_line = find_anchor_line(lines, entry["anchor_page"])
            end_line = (find_anchor_line(lines, toc[i + 1]["anchor_page"]) - 1) if i + 1 < len(toc) else len(lines)
            end_page = (toc[i + 1]["anchor_page"] - 1) if i + 1 < len(toc) else max([entry["anchor_page"]] + [x.get("pdf_page") or 0 for x in image_refs])
            meta = meta_for(book["year"], entry["id"], entry["title"])
            filename = f"{entry['id']}_{safe_slug(meta['slug'])}.md"
            rel_path = f"03_sources/local_knowledge/books/{rid}/chapters/{filename}"
            header = {
                "resource_id": rid,
                "edition_year": book["year"],
                "chapter_id": entry["id"],
                "title": entry["title"],
                "pdf_page_start": entry["anchor_page"],
                "pdf_page_end": end_page,
                "source_line_start": start_line,
                "source_line_end": end_line,
                "tags": meta["tags"],
                "status": "source_preserved_ocr_markdown",
                "rights": "user_supplied_private_research_copy",
            }
            body = "\n".join(lines[start_line - 1:end_line]) + "\n"
            # Chapter files live one directory below source.md, so preserve
            # renderable image references after splitting the book.
            body = re.sub(r"\]\(images/", "](../images/", body)
            chapter_text = "---\n" + yaml.safe_dump(header, allow_unicode=True, sort_keys=False).strip() + "\n---\n\n" + body
            write_text(chapters_dir / filename, chapter_text)
            chapter_lines = [(n, lines[n - 1]) for n in range(start_line, end_line + 1)]
            chunks = build_chunks(rid, book["year"], entry, chapter_lines, rel_path, meta["tags"], book["priority"], source_dir)
            all_chunks.extend(chunks)
            entry_out = {
                **entry,
                "pdf_page_end": end_page,
                "source_line_start": start_line,
                "source_line_end": end_line,
                "slug": meta["slug"],
                "tags": meta["tags"],
                "summary": meta["summary"],
                "local_path": rel_path,
                "chunk_count": len(chunks),
            }
            entries_out.append(entry_out)
            chapter_lookup[(rid, entry["id"])] = entry_out

        missing_image_refs = [item for item in image_refs if item["status"] != "available_local"]
        limitations = ["文本可能仍含OCR噪声"]
        if missing_image_refs:
            limitations.extend(["Markdown引用的部分images资产仍缺失", "涉及缺失公式、图表或版式时必须回到合法完整副本核验"])
        metadata = {
            "resource_id": rid,
            "title": book["title"],
            "editors": book["editors"],
            "publisher": book["publisher"],
            "year": book["year"],
            "isbn": book["isbn"],
            "source_file": book["input_name"],
            "source_sha256": sha256_bytes(source_path.read_bytes()),
            "source_bytes": source_path.stat().st_size,
            "source_lines": len(lines),
            "text_format": "OCR-corrected Markdown supplied by creator",
            "rights": "user_supplied_private_research_copy",
            "edition_priority": book["priority"],
            "edition_role": book["edition_role"],
            "fulltext_path": f"03_sources/local_knowledge/books/{rid}/source.md",
            "chapter_index_path": f"03_sources/local_knowledge/books/{rid}/chapter_index.yaml",
            "image_assets_status": "complete_local" if image_refs and not missing_image_refs else ("partially_missing" if image_refs else "none_referenced"),
            "image_asset_count": len(image_refs) - len(missing_image_refs),
            "missing_image_asset_count": len(missing_image_refs),
            "limitations": limitations,
            "ingested_on": TODAY,
        }
        dump_yaml(source_dir / "metadata.yaml", metadata)
        dump_yaml(source_dir / "chapter_index.yaml", {"resource_id": rid, "entries": entries_out})
        catalog_resources.append({
            "resource_id": rid,
            "title": book["title"],
            "edition_year": book["year"],
            "priority": book["priority"],
            "coverage": "fulltext_chaptered_chunked_indexed",
            "rights": "user_supplied_private_research_copy",
            "metadata_path": f"03_sources/local_knowledge/books/{rid}/metadata.yaml",
            "chapter_index_path": f"03_sources/local_knowledge/books/{rid}/chapter_index.yaml",
            "fulltext_path": f"03_sources/local_knowledge/books/{rid}/source.md",
            "image_asset_count": len(image_refs) - len(missing_image_refs),
            "missing_image_asset_count": len(missing_image_refs),
        })

    # Portable book chunks and the unified SQLite index.
    chunks_path = index_root / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    external_path = index_root / "external_chunks.jsonl"
    external_chunks = []
    if external_path.exists():
        external_chunks = [json.loads(line) for line in external_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    unified_chunks = all_chunks + external_chunks
    with (index_root / "all_chunks.jsonl").open("w", encoding="utf-8") as f:
        for chunk in unified_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    build_sqlite(index_root / "local_fts.sqlite", unified_chunks)
    dump_yaml(index_root / "chunks_manifest.yaml", {
        "generated_on": TODAY,
        "chunk_count": len(all_chunks),
        "resources": {rid: sum(1 for c in all_chunks if c["resource_id"] == rid) for rid in BOOKS},
        "chunk_policy": {"target_chars": 1150, "sentence_split_max_chars": 680, "overlap": 0, "tokenizer": "SQLite FTS5 trigram"},
        "provenance_fields": ["resource_id", "chapter_id", "pdf_page_start", "pdf_page_end", "source_line_start", "source_line_end", "content_sha256"],
    })
    with (index_root / "missing_assets.jsonl").open("w", encoding="utf-8") as f:
        for item in missing_assets:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # Local source catalog.
    dump_yaml(index_root / "local_source_catalog.yaml", {
        "version": "0.3.1",
        "generated_on": TODAY,
        "runtime_policy": {
            "external_fetch_on_startup": False,
            "primary_edition": "METHOD-IACMR-EMPIRICAL-2018",
            "supplementary_edition": "METHOD-IACMR-EMPIRICAL-2008",
            "retrieval_order": ["method_topic_router", "local_cards", "local_fts", "external_fallback"],
        },
        "resources": catalog_resources,
        "index": {
            "portable_chunks": "03_sources/local_knowledge/index/chunks.jsonl",
            "sqlite_fts": "03_sources/local_knowledge/index/local_fts.sqlite",
            "search_cli": "11_implementation/local_retrieval.py",
            "missing_assets": "03_sources/local_knowledge/index/missing_assets.jsonl",
        },
    })

    # Cards and topic router.
    router_topics = []
    quick_rows = []
    for card in TOPIC_CARDS:
        refs = []
        for rid, cid in card["sources"]:
            chapter = chapter_lookup.get((rid, cid))
            if not chapter:
                raise KeyError(f"Missing chapter reference: {rid}/{cid}")
            refs.append({
                "resource_id": rid,
                "chapter_id": cid,
                "chapter_title": chapter["title"],
                "pdf_pages": f"{chapter['anchor_page']}-{chapter['pdf_page_end']}",
                "local_path": chapter["local_path"],
            })
        card_filename = card["id"].lower().replace("local-method-", "") + ".md"
        card_rel = f"03_sources/local_knowledge/cards/{card_filename}"
        front = {
            "card_id": card["id"],
            "status": "source_mapped_local",
            "aliases": card["aliases"],
            "source_refs": [f"{r['resource_id']}:{r['chapter_id']}" for r in refs],
            "review_rule": "关键方法细节必须继续查询本地原文块并返回PDF页码",
        }
        md = ["---", yaml.safe_dump(front, allow_unicode=True, sort_keys=False).strip(), "---", "", f"# {card['title']}", "", "## 何时使用", "", card["use_when"], "", "## Agent执行要点", ""]
        md.extend(f"- {x}" for x in card["core_actions"])
        md.extend(["", "## 风险与停止信号", ""])
        md.extend(f"- {x}" for x in card["warnings"])
        md.extend(["", "## 本地证据入口", ""])
        for r in refs:
            md.append(f"- `{r['resource_id']}` / `{r['chapter_id']}` / PDF页 {r['pdf_pages']} / `{r['local_path']}`")
        md.extend(["", "## 检索策略", "", "先读取本卡；若需定义、假设、步骤、诊断或例证，使用 `local_retrieval.py` 在上述章节内检索。不得为节省上下文而跳过页码溯源。", ""])
        write_text(cards_root / card_filename, "\n".join(md))
        router_topics.append({
            "topic_id": card["id"],
            "title": card["title"],
            "aliases": card["aliases"],
            "card_path": card_rel,
            "source_refs": refs,
            "external_search_required": False,
            "fallback_condition": "本地章节无法支持所需细节、内容涉及2026年后的方法更新、或缺失图表资产",
        })
        quick_rows.append((card["title"], "、".join(card["aliases"][:4]), refs[0]["resource_id"] + ":" + refs[0]["chapter_id"], card_rel))
    dump_yaml(index_root / "method_topic_router.yaml", {
        "version": "0.2.0",
        "generated_on": TODAY,
        "match_policy": "先做别名/标签精确匹配，再做本地FTS；禁止启动时外部搜索",
        "topics": router_topics,
        "paradigm_coverage": PARADIGM_SOURCE_MAP,
    })

    quick = ["# 本地实证方法快速索引", "", "> 用途：Agent先通过本表定位知识卡与章节，再查询本地FTS。链接注册表不参与任务启动检索。", "", "| 方法主题 | 常见触发词 | 首选章节 | 本地卡 |", "|---|---|---|---|"]
    for title, aliases, primary, card_rel in quick_rows:
        quick.append(f"| {title} | {aliases} | `{primary}` | `{card_rel}` |")
    quick.extend(["", "## 版本优先级", "", "- 2018第三版：默认首选。", "- 2008版：用于版本对照及第三版未单列的中国理论建构、组织社会资本、跨文化研究和发表历程。", "- 涉及最新软件、统计发展、期刊规则或报告标准时，本地书籍只提供基础框架，必须调用版本化补充来源。", ""])
    write_text(index_root / "empirical_methods_quick_reference.md", "\n".join(quick))

    # Edition comparison.
    comparison = """# 两版《组织与管理研究的实证方法》使用规则

## 默认优先级

- **2018第三版为主来源**：结构更完整，新增元分析、质化分析、情境化、纵向、事件历史、事件研究、日记/体验抽样和复杂条件过程等专题。
- **2008版为补充来源**：保留中国管理理论建构、组织社会资本、跨文化研究、一篇论文的发表历程及中国管理研究发表挑战等独立章节。

## Agent选择规则

1. 两版均覆盖的主题，先读2018版；需要理解版本变化或补充早期表述时再读2008版。
2. 下列主题优先读2008版：`china_management_theory`、`organizational_social_capital_measurement`、`cross_cultural_research`、`paper_publication_journey`。
3. 下列主题仅2018版具有独立系统章节：`meta_analysis`、`qualitative_research_and_analysis`、`contextualized_research`、`longitudinal_panel_analysis`、`event_history_analysis`、`event_study`、`diary_and_experience_sampling`、`moderated_mediation_and_mediated_moderation`。
4. 任何软件、期刊、报告标准和统计前沿都可能在出版后更新；不得把书中版本信息当作当前规则。
5. OCR文字仍可能有识别噪声；现有图片可以回溯核验，但涉及公式、图表和版式的关键判断仍应结合图片而非只读OCR文字。
"""
    write_text(index_root / "edition_comparison.md", comparison)

    # Paradigm map and method index update.
    dump_yaml(root / "04_paradigms/local_source_map.yaml", {"version": "0.2.0", "generated_on": TODAY, "paradigms": PARADIGM_SOURCE_MAP})
    method_index = root / "05_methods/method_index.md"
    old_method = method_index.read_text(encoding="utf-8")
    local_section = """# 方法知识索引

## 本地已入库的管理实证方法

- 快速路由：`03_sources/local_knowledge/index/empirical_methods_quick_reference.md`
- 主题规则：`03_sources/local_knowledge/index/method_topic_router.yaml`
- 全文索引：`03_sources/local_knowledge/index/local_fts.sqlite`
- 查询脚本：`11_implementation/local_retrieval.py`
- 范式覆盖：`04_paradigms/local_source_map.yaml`

运行时先使用上述本地入口。下表中的外部资源只在本地覆盖不足时使用。

"""
    if "## 本地已入库的管理实证方法" not in old_method:
        old_body = old_method.split("\n", 1)[1] if "\n" in old_method else old_method
        write_text(method_index, local_section + old_body.lstrip())

    update_source_registry(root, "03_sources/local_knowledge/index/local_source_catalog.yaml", "03_sources/local_knowledge/index/local_fts.sqlite")
    update_text_files(root)
    update_manifest_and_coverage(root, len(all_chunks), len(external_chunks))
    write_local_retrieval_script(root)
    refresh = root / "11_implementation/refresh_localization_status.py"
    if refresh.exists():
        subprocess.run([sys.executable, str(refresh)], check=True)
    build_checksums(root)

    print(json.dumps({
        "root": str(root),
        "books": len(BOOKS),
        "chapters": len(chapter_lookup),
        "chunks": len(all_chunks),
        "cards": len(TOPIC_CARDS),
        "missing_assets": len(missing_assets),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
