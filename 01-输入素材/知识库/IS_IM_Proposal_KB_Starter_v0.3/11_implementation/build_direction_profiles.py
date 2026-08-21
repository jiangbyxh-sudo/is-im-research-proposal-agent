#!/usr/bin/env python3
"""Build the versioned P1 retrieval profiles from the canonical 61-direction catalog."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path


KB_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = KB_ROOT / "01_taxonomy/generated/research_direction_catalog.json"
OUTPUT_PATH = KB_ROOT / "01_taxonomy/generated/direction_profiles.json"

PROFILE_VERSION = "1.0.0-p1"

# A stable bilingual label is retrieval configuration, not UI copy.  Keep changes
# reviewable here and regenerate the derived JSON with this script.
LABELS = {
    "technology_adoption": ("技术与AI采纳", "technology and AI adoption"),
    "human_ai_interaction": ("人机交互", "human-AI interaction"),
    "platform_governance": ("平台治理", "platform governance"),
    "topic_digital_transformation": ("数字化转型", "digital transformation"),
    "topic_algorithmic_management": ("算法管理", "algorithmic management"),
    "social_media": ("社交媒体", "social media"),
    "topic_digital_markets": ("数字市场", "digital markets"),
    "topic_privacy_security": ("隐私与安全", "privacy and security"),
    "topic_it_governance": ("IT治理", "IT governance"),
    "topic_digital_innovation": ("数字创新", "digital innovation"),
    "topic_technology_use": ("技术使用", "technology use"),
    "topic_digital_strategy": ("数字战略", "digital strategy"),
    "topic_平台经济": ("平台经济", "platform economy"),
    "recommender_systems": ("推荐系统与推荐算法", "recommender systems and algorithms"),
    "topic_电商": ("电子商务", "electronic commerce"),
    "topic_数字广告": ("数字广告", "digital advertising"),
    "topic_在线行为": ("在线行为", "online behavior"),
    "topic_算法机制": ("算法机制", "algorithmic mechanisms"),
    "topic_hci": ("人机交互研究", "human-computer interaction"),
    "information_retrieval": ("信息检索", "information retrieval"),
    "topic_machine_learning": ("机器学习", "machine learning"),
    "topic_data_mining": ("数据挖掘", "data mining"),
    "topic_software_system_design": ("软件与系统设计", "software and system design"),
    "topic_knowledge_discovery": ("知识发现", "knowledge discovery"),
    "topic_ai_enabled_information_systems": ("AI赋能信息系统", "AI-enabled information systems"),
    "topic_digital_artifact_design": ("数字人工物设计", "digital artifact design"),
    "topic_ai_trust": ("AI信任", "trust in AI"),
    "topic_algorithm_aversion_appreciation": ("算法厌恶与算法欣赏", "algorithm aversion and appreciation"),
    "topic_anthropomorphism": ("拟人化", "anthropomorphism"),
    "topic_cognitive_load": ("认知负荷", "cognitive load"),
    "topic_information_overload": ("信息过载", "information overload"),
    "topic_social_influence": ("社会影响", "social influence"),
    "topic_privacy_concern": ("隐私关注", "privacy concern"),
    "topic_technostress": ("技术压力", "technostress"),
    "topic_human_ai_teams": ("人机团队", "human-AI teams"),
    "topic_identity": ("身份认同", "identity"),
    "topic_emotion": ("情绪", "emotion"),
    "topic_attention": ("注意力", "attention"),
    "topic_judgment_decision_making": ("判断与决策", "judgment and decision making"),
    "topic_misinformation": ("错误信息", "misinformation"),
    "topic_news_consumption": ("新闻消费", "news consumption"),
    "topic_content_moderation": ("内容审核", "content moderation"),
    "topic_influencers": ("社交媒体影响者", "social media influencers"),
    "topic_generative_ai": ("生成式AI", "generative AI"),
    "topic_human_ai_communication": ("人机传播", "human-AI communication"),
    "topic_political_communication": ("政治传播", "political communication"),
    "topic_algorithmic_news": ("算法新闻", "algorithmic news"),
    "topic_information_science": ("信息科学", "information science"),
    "information_behavior": ("信息行为", "information behavior"),
    "knowledge_management": ("知识管理", "knowledge management"),
    "topic_data_management": ("数据管理", "data management"),
    "topic_data_governance": ("数据治理", "data governance"),
    "scientometrics": ("科学计量与文献计量", "scientometrics and bibliometrics"),
    "topic_knowledge_graph": ("知识图谱", "knowledge graphs"),
    "topic_decision_support": ("决策支持", "decision support systems"),
    "ai_nlp_information_processing": ("AI与NLP信息处理", "AI and NLP for information processing"),
    "topic_scholarly_communication": ("学术传播", "scholarly communication"),
    "topic_data_knowledge": ("数据与知识", "data and knowledge"),
    "topic_decision_intelligence": ("决策智能", "decision intelligence"),
    "topic_organizational_information": ("组织信息", "organizational information"),
    "topic_digital_information_environment": ("数字信息环境", "digital information environment"),
}

GROUP_CONTEXT = {
    "is": ("information systems", "digital organizations"),
    "is_cs_hci": ("human-computer interaction", "computing"),
    "is_psychology": ("user behavior", "behavioral research"),
    "is_communication_media": ("digital media", "online communication"),
    "im": ("information management", "information science"),
    "im_data_ai_knowledge": ("knowledge and data systems", "organizational information"),
}

GROUP_POOLS = {
    "is": ["IS_CORE", "DIGITAL_PLATFORM", "ORG_STRATEGY", "ECON_STRATEGY", "SECURITY", "ZH_IS_IM_CORE", "ZH_ORG_INNOVATION", "CSSCI_2025_2026_MANAGEMENT_IS_IM_RELEVANT", "PKU_CORE_2023_ORG_INNOVATION", "PKU_CORE_2023_MANAGEMENT_DIRECT", "PKU_CORE_2023_PUBLIC_DIGITAL_GOV"],
    "is_cs_hci": ["IS_CORE", "CS_AI", "HCI", "CS_IR", "CS_DATA", "ZH_IS_IM_CORE", "ZH_METHODS_ANALYTICS", "CSSCI_2025_2026_INFORMATION_RESOURCE_FULL", "CSSCI_2025_2026_PSYCHOLOGY_IS_RELEVANT", "PKU_CORE_2023_INFORMATION_RESOURCE", "PKU_CORE_2023_PSYCHOLOGY"],
    "is_psychology": ["IS_CORE", "PSYCHOLOGY", "HCI", "ZH_IS_IM_CORE", "ZH_PSYCHOLOGY", "CSSCI_2025_2026_PSYCHOLOGY_IS_RELEVANT", "PKU_CORE_2023_PSYCHOLOGY"],
    "is_communication_media": ["IS_CORE", "COMMUNICATION", "HCI", "ZH_IS_IM_CORE", "ZH_ORG_INNOVATION", "CSSCI_2025_2026_COMMUNICATION_IS_IM_RELEVANT", "PKU_CORE_2023_COMMUNICATION"],
    "im": ["IM_CORE", "SCIENTOMETRICS", "ZH_IS_IM_CORE", "ZH_METHODS_ANALYTICS", "CSSCI_2025_2026_INFORMATION_RESOURCE_FULL", "PKU_CORE_2023_INFORMATION_RESOURCE", "PKU_CORE_2023_SCIENCE_POLICY"],
    "im_data_ai_knowledge": ["IM_CORE", "CS_AI", "CS_IR", "CS_DATA", "IS_CORE", "ZH_IS_IM_CORE", "ZH_METHODS_ANALYTICS", "CSSCI_2025_2026_INFORMATION_RESOURCE_FULL", "PKU_CORE_2023_INFORMATION_RESOURCE", "PKU_CORE_2023_STATISTICS_METHODS"],
}


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = value.strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def build_profile(direction: dict) -> dict:
    direction_id = direction["direction_id"]
    zh, en = LABELS[direction_id]
    group_ids = direction["group_ids"]
    contexts = unique([term for group_id in group_ids for term in GROUP_CONTEXT[group_id]])
    context_primary = contexts[0]
    synonyms = unique([zh, en, *direction.get("aliases", []), f"{en} in {context_primary}"])
    pools = unique([pool for group_id in group_ids for pool in GROUP_POOLS[group_id]])
    computing_route = any(group_id in {"is_cs_hci", "im_data_ai_knowledge"} for group_id in group_ids)
    return {
        "profile_version": PROFILE_VERSION,
        "direction_id": direction_id,
        "labels": {"zh": zh, "en": en},
        "group_ids": group_ids,
        "synonyms": synonyms,
        "boundaries": {
            "include": [en, context_primary, "empirical or theoretical research within IS/IM scope"],
            "exclude": ["clinical or biomedical-only research", "pure hardware engineering without IS/IM phenomena"],
        },
        "provider_queries": {
            "openalex": [en, f'"{en}" AND "{context_primary}"'],
            "semantic_scholar": [en, f"{en} {context_primary}"],
            "crossref": [en, zh],
            "dblp": [f"{en} {contexts[1] if len(contexts) > 1 else 'computing'}"],
        },
        "topic_routes": {
            "strategy": "search_then_topic_evidence",
            "topic_search_terms": [en, *contexts[:2]],
            "openalex_topic_ids": [],
            "status": "text_route_active; topic_ids_require_calibration",
        },
        "source_routes": {
            "required": ["openalex", "crossref"],
            "optional": ["semantic_scholar", *( ["dblp"] if computing_route else []), "core", "unpaywall"],
            "licensed_optional": ["scopus", "web_of_science", "cnki", "wanfang"],
        },
        "journal_pool_ids": pools,
        "document_types": ["journal-article", *( ["proceedings-article"] if computing_route else [])],
        "fallback_queries": [
            f"{en} {context_primary}",
            f"({en}) OR ({synonyms[-1]})",
        ],
        "coverage_targets": {"raw_min": 20, "eligible_min": 10, "precision_at_20_min": 0.80},
        "source_refs": direction.get("source_refs", []),
    }


def main() -> int:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    catalog_ids = {item["direction_id"] for item in catalog["directions"]}
    if catalog_ids != set(LABELS):
        missing = sorted(catalog_ids - set(LABELS))
        extra = sorted(set(LABELS) - catalog_ids)
        raise SystemExit(f"Bilingual label coverage mismatch; missing={missing}; extra={extra}")
    profiles = [build_profile(item) for item in catalog["directions"]]
    payload = {
        "version": PROFILE_VERSION,
        "generated_on": date.today().isoformat(),
        "generated_from": str(CATALOG_PATH.relative_to(KB_ROOT)).replace("\\", "/"),
        "direction_count": len(profiles),
        "policy": {
            "local_profile_first": True,
            "provider_queries_are_versioned": True,
            "topic_ids_calibrated": False,
            "score_thresholds_calibrated": False,
        },
        "profiles": profiles,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(profiles)} direction profiles to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
