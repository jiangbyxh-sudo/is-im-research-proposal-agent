#!/usr/bin/env python3
"""Zero-dependency local server for the IS/IM proposal-assistant V0."""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import unquote, urlparse
from uuid import uuid4


APP_DIR = Path(__file__).resolve().parent
WORKSPACE = APP_DIR.parents[2]
KB_ROOT = WORKSPACE / "01-输入素材/知识库/IS_IM_Proposal_KB_Starter_v0.3"
CATALOG_PATH = KB_ROOT / "01_taxonomy/generated/research_direction_catalog.json"
DIRECTION_PROFILE_PATH = KB_ROOT / "01_taxonomy/generated/direction_profiles.json"
JOURNAL_REGISTRY_PATH = KB_ROOT / "02_journals/generated/journal_registry.json"
PROVIDER_DIR = KB_ROOT / "11_implementation"
STATIC_DIR = APP_DIR / "static"
KB_VERSION = "0.4.1"
SYNTHESIS_JOB_TTL_SECONDS = 30 * 60
SYNTHESIS_JOB_LIMIT = 20
SYNTHESIS_JOBS: dict[str, tuple[float, SynthesisRequest]] = {}
SYNTHESIS_JOBS_LOCK = Lock()
PROPOSAL_CONTEXT_TTL_SECONDS = 60 * 60
PROPOSAL_CONTEXT_LIMIT = 20
PROPOSAL_CONTEXTS: dict[str, tuple[float, SynthesisRequest, object]] = {}
PROPOSAL_CONTEXTS_LOCK = Lock()
_DYNAMIC_PROVIDER_INSTANCE = None
_DYNAMIC_PROVIDER_SIGNATURE = None
_DYNAMIC_PROVIDER_LOCK = Lock()

if str(PROVIDER_DIR) not in sys.path:
    sys.path.insert(0, str(PROVIDER_DIR))

from paper_discovery_provider import (  # noqa: E402
    CrossrefTransport,
    CrossrefPaperDiscoveryProvider,
    DiscoveryRequest,
    UnconfiguredPaperDiscoveryProvider,
)
from multi_source_discovery_provider import MultiSourcePaperDiscoveryProvider  # noqa: E402
from openalex_provider import OpenAlexPaperProvider, OpenAlexTransport  # noqa: E402
from research_synthesis_provider import (  # noqa: E402
    SynthesisRequest,
    build_research_synthesis_provider,
)
from proposal_generation_provider import (  # noqa: E402
    ProposalRequest,
    build_proposal_generation_provider,
)
from evaluation.p0_model_baseline import run_model_baseline  # noqa: E402


GROUP_POOL_ROUTES = {
    "is": ("IS_CORE", "DIGITAL_PLATFORM", "ORG_STRATEGY", "ECON_STRATEGY", "SECURITY", "ZH_IS_IM_CORE", "ZH_ORG_INNOVATION", "CSSCI_2025_2026_MANAGEMENT_IS_IM_RELEVANT", "PKU_CORE_2023_ORG_INNOVATION", "PKU_CORE_2023_MANAGEMENT_DIRECT", "PKU_CORE_2023_PUBLIC_DIGITAL_GOV"),
    "is_cs_hci": ("IS_CORE", "CS_AI", "HCI", "CS_IR", "CS_DATA", "ZH_IS_IM_CORE", "ZH_METHODS_ANALYTICS", "CSSCI_2025_2026_INFORMATION_RESOURCE_FULL", "CSSCI_2025_2026_PSYCHOLOGY_IS_RELEVANT", "PKU_CORE_2023_INFORMATION_RESOURCE", "PKU_CORE_2023_PSYCHOLOGY"),
    "is_psychology": ("IS_CORE", "PSYCHOLOGY", "HCI", "ZH_IS_IM_CORE", "ZH_PSYCHOLOGY", "CSSCI_2025_2026_PSYCHOLOGY_IS_RELEVANT", "PKU_CORE_2023_PSYCHOLOGY"),
    "is_communication_media": ("IS_CORE", "COMMUNICATION", "HCI", "ZH_IS_IM_CORE", "ZH_ORG_INNOVATION", "CSSCI_2025_2026_COMMUNICATION_IS_IM_RELEVANT", "PKU_CORE_2023_COMMUNICATION"),
    "im": ("IM_CORE", "SCIENTOMETRICS", "ZH_IS_IM_CORE", "ZH_METHODS_ANALYTICS", "CSSCI_2025_2026_INFORMATION_RESOURCE_FULL", "PKU_CORE_2023_INFORMATION_RESOURCE", "PKU_CORE_2023_SCIENCE_POLICY"),
    "im_data_ai_knowledge": ("IM_CORE", "CS_AI", "CS_IR", "CS_DATA", "IS_CORE", "ZH_IS_IM_CORE", "ZH_METHODS_ANALYTICS", "CSSCI_2025_2026_INFORMATION_RESOURCE_FULL", "PKU_CORE_2023_INFORMATION_RESOURCE", "PKU_CORE_2023_STATISTICS_METHODS"),
}


class RequestError(ValueError):
    pass


def load_catalog() -> dict:
    if not CATALOG_PATH.is_file():
        raise FileNotFoundError(f"Direction catalog missing: {CATALOG_PATH}")
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def public_catalog() -> dict:
    catalog = load_catalog()
    directions = {item["direction_id"]: item for item in catalog["directions"]}
    return {
        "version": catalog["version"],
        "direction_count": catalog["direction_count"],
        "raw_topic_count": catalog["raw_topic_count"],
        "groups": [
            {
                "group_id": group["group_id"],
                "label": group["label"],
                "directions": [directions[item_id] for item_id in group["direction_ids"]],
            }
            for group in catalog["groups"]
        ],
    }


def positive_count(payload: dict, key: str, default: int) -> int:
    value = payload.get(key, default)
    if isinstance(value, bool):
        raise RequestError(f"{key} must be a positive integer")
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise RequestError(f"{key} must be a positive integer") from exc
    if value < 1:
        raise RequestError(f"{key} must be a positive integer")
    return value


def provider_name() -> str:
    return os.getenv("PROPOSAL_DYNAMIC_PROVIDER", "multi_source").strip().lower()


def openalex_transport_settings() -> dict[str, int]:
    return {
        "timeout": int(os.getenv("PROPOSAL_RETRIEVAL_TIMEOUT", "45")),
        "retries": int(os.getenv("PROPOSAL_RETRIEVAL_RETRIES", "5")),
    }


def dynamic_provider_signature() -> tuple[int, int]:
    return (
        DIRECTION_PROFILE_PATH.stat().st_mtime_ns,
        JOURNAL_REGISTRY_PATH.stat().st_mtime_ns,
    )


def build_dynamic_provider():
    global _DYNAMIC_PROVIDER_INSTANCE, _DYNAMIC_PROVIDER_SIGNATURE
    if provider_name() in {"disabled", "off", "unconfigured"}:
        return UnconfiguredPaperDiscoveryProvider()
    signature = dynamic_provider_signature()
    with _DYNAMIC_PROVIDER_LOCK:
        if _DYNAMIC_PROVIDER_INSTANCE is not None and _DYNAMIC_PROVIDER_SIGNATURE == signature:
            return _DYNAMIC_PROVIDER_INSTANCE
    enable_chinese = os.getenv("PROPOSAL_ENABLE_CHINESE_RETRIEVAL", "1").strip().lower() in {"1", "true", "yes", "on"}
    if provider_name() in {"multi_source", "p1", "openalex"}:
        crossref = CrossrefPaperDiscoveryProvider(
            JOURNAL_REGISTRY_PATH,
            transport=CrossrefTransport(
                mailto=os.getenv("PROPOSAL_CROSSREF_MAILTO") or None,
                timeout=int(os.getenv("PROPOSAL_CROSSREF_FALLBACK_TIMEOUT", "6")),
                retries=0,
            ),
            enable_chinese=enable_chinese,
            max_journals_per_language=int(os.getenv("PROPOSAL_CROSSREF_FALLBACK_JOURNALS", "3")),
            rows_per_journal=int(os.getenv("PROPOSAL_CROSSREF_FALLBACK_ROWS", "10")),
        )
        openalex = OpenAlexPaperProvider(OpenAlexTransport(**openalex_transport_settings()))
        instance = MultiSourcePaperDiscoveryProvider(DIRECTION_PROFILE_PATH, JOURNAL_REGISTRY_PATH, openalex=openalex, crossref=crossref)
    else:
        instance = CrossrefPaperDiscoveryProvider(JOURNAL_REGISTRY_PATH, enable_chinese=enable_chinese)
    with _DYNAMIC_PROVIDER_LOCK:
        if _DYNAMIC_PROVIDER_INSTANCE is None or _DYNAMIC_PROVIDER_SIGNATURE != signature:
            _DYNAMIC_PROVIDER_INSTANCE = instance
            _DYNAMIC_PROVIDER_SIGNATURE = signature
        return _DYNAMIC_PROVIDER_INSTANCE


def load_direction_profiles() -> dict[str, dict]:
    if not DIRECTION_PROFILE_PATH.is_file():
        return {}
    payload = json.loads(DIRECTION_PROFILE_PATH.read_text(encoding="utf-8"))
    return {item["direction_id"]: item for item in payload.get("profiles", [])}


def synthesis_provider_name() -> str:
    return "deepseek" if os.getenv("DEEPSEEK_API_KEY") else "unconfigured"


def configure_synthesis(payload: dict) -> dict:
    api_key = str(payload.get("api_key") or "").strip()
    if len(api_key) < 20 or not api_key.startswith("sk-"):
        raise RequestError("请输入有效的DeepSeek API密钥")
    base_url = str(payload.get("base_url") or "https://api.deepseek.com").rstrip("/")
    model = str(payload.get("model") or "deepseek-v4-pro").strip()
    if base_url != "https://api.deepseek.com":
        raise RequestError("当前只允许官方DeepSeek API地址")
    if model != "deepseek-v4-pro":
        raise RequestError("当前综合模型固定为deepseek-v4-pro")
    os.environ["DEEPSEEK_API_KEY"] = api_key
    os.environ["DEEPSEEK_BASE_URL"] = base_url
    os.environ["DEEPSEEK_MODEL"] = model
    return {
        "configured": True,
        "provider": "deepseek",
        "base_url": base_url,
        "model": model,
        "persistence": "process_memory_only",
        "message_to_user": "DeepSeek已在当前服务进程中启用；密钥未写入文件且不会回显。",
    }


def configure_retrieval(payload: dict) -> dict:
    api_key = str(payload.get("openalex_api_key") or "").strip()
    if len(api_key) < 8:
        raise RequestError("请输入有效的OpenAlex API密钥")
    os.environ["OPENALEX_API_KEY"] = api_key
    return {
        "configured": True,
        "provider": "openalex",
        "persistence": "process_memory_only",
        "message_to_user": "OpenAlex已在当前服务进程中启用认证额度；密钥未写入文件且不会回显。",
    }


def journal_pools_for(direction: dict) -> tuple[str, ...]:
    pools = []
    for group_id in direction.get("group_ids", []):
        for pool_id in GROUP_POOL_ROUTES.get(group_id, ()):
            if pool_id not in pools:
                pools.append(pool_id)
    return tuple(pools)


def store_synthesis_job(request: SynthesisRequest) -> str:
    """Keep the verified corpus server-side so discovery can return immediately."""
    now = time.monotonic()
    with SYNTHESIS_JOBS_LOCK:
        expired = [
            job_id for job_id, (created_at, _) in SYNTHESIS_JOBS.items()
            if now - created_at > SYNTHESIS_JOB_TTL_SECONDS
        ]
        for job_id in expired:
            SYNTHESIS_JOBS.pop(job_id, None)
        while len(SYNTHESIS_JOBS) >= SYNTHESIS_JOB_LIMIT:
            oldest = min(SYNTHESIS_JOBS, key=lambda item: SYNTHESIS_JOBS[item][0])
            SYNTHESIS_JOBS.pop(oldest, None)
        job_id = uuid4().hex
        SYNTHESIS_JOBS[job_id] = (now, request)
    return job_id


def run_synthesis_job(job_id: str, synthesis_provider=None) -> dict:
    job_id = str(job_id or "").strip()
    with SYNTHESIS_JOBS_LOCK:
        stored = SYNTHESIS_JOBS.get(job_id)
    if not stored:
        raise RequestError("综合任务已失效，请重新运行论文检索")
    created_at, request = stored
    if time.monotonic() - created_at > SYNTHESIS_JOB_TTL_SECONDS:
        with SYNTHESIS_JOBS_LOCK:
            SYNTHESIS_JOBS.pop(job_id, None)
        raise RequestError("综合任务已超过30分钟，请重新运行论文检索")

    synthesis = (synthesis_provider or build_research_synthesis_provider()).synthesize(request)
    synthesis_complete = synthesis.status in {"SYNTHESIS_COMPLETE", "SYNTHESIS_PARTIAL"}
    proposal_context_id = None
    if synthesis_complete:
        with SYNTHESIS_JOBS_LOCK:
            SYNTHESIS_JOBS.pop(job_id, None)
        proposal_context_id = store_proposal_context(request, synthesis)
    return {
        "state": "GAP_CANDIDATES_READY" if synthesis_complete else "PAPERS_DISCOVERED",
        "synthesis_status": synthesis.status,
        "synthesis_message": synthesis.message_to_user,
        "top_subdirections": synthesis.top_subdirections,
        "gap_candidates": synthesis.gap_candidates,
        "synthesis_limitations": synthesis.limitations,
        "synthesis_audit": synthesis.audit,
        "proposal_context_id": proposal_context_id,
    }


def store_proposal_context(request: SynthesisRequest, synthesis) -> str:
    now = time.monotonic()
    with PROPOSAL_CONTEXTS_LOCK:
        expired = [
            context_id for context_id, (created_at, _, _) in PROPOSAL_CONTEXTS.items()
            if now - created_at > PROPOSAL_CONTEXT_TTL_SECONDS
        ]
        for context_id in expired:
            PROPOSAL_CONTEXTS.pop(context_id, None)
        while len(PROPOSAL_CONTEXTS) >= PROPOSAL_CONTEXT_LIMIT:
            oldest = min(PROPOSAL_CONTEXTS, key=lambda item: PROPOSAL_CONTEXTS[item][0])
            PROPOSAL_CONTEXTS.pop(oldest, None)
        context_id = uuid4().hex
        PROPOSAL_CONTEXTS[context_id] = (now, request, synthesis)
    return context_id


def generate_proposal(payload: dict, proposal_provider=None) -> dict:
    context_id = str(payload.get("proposal_context_id") or "").strip()
    selected_gap_id = str(payload.get("selected_gap_id") or "").strip()
    selected_innovation_id = str(payload.get("selected_innovation_id") or "").strip()
    if not context_id or not selected_gap_id or not selected_innovation_id:
        raise RequestError("必须明确选择一个研究空白和一个创新点")
    with PROPOSAL_CONTEXTS_LOCK:
        stored = PROPOSAL_CONTEXTS.get(context_id)
    if not stored:
        raise RequestError("开题上下文已失效，请重新运行论文检索与方向综合")
    created_at, synthesis_request, synthesis = stored
    if time.monotonic() - created_at > PROPOSAL_CONTEXT_TTL_SECONDS:
        with PROPOSAL_CONTEXTS_LOCK:
            PROPOSAL_CONTEXTS.pop(context_id, None)
        raise RequestError("开题上下文已超过60分钟，请重新运行论文检索与方向综合")
    gap = next((item for item in synthesis.gap_candidates if item.get("gap_id") == selected_gap_id), None)
    if not gap:
        raise RequestError("选择的研究空白不属于本次核验结果")
    innovation_map = {
        f"{selected_gap_id}_innovation_{index + 1}": str(value)
        for index, value in enumerate(gap.get("innovation_candidates", []))
    }
    if selected_innovation_id not in innovation_map:
        raise RequestError("选择的创新点不属于该研究空白")
    result = (proposal_provider or build_proposal_generation_provider(KB_ROOT)).generate(
        ProposalRequest(
            research_direction=synthesis_request.research_direction,
            fine_grained_question=synthesis_request.fine_grained_question,
            selected_gap=gap,
            selected_innovation_id=selected_innovation_id,
            selected_innovation=innovation_map[selected_innovation_id],
            papers=synthesis_request.papers,
        )
    )
    result.proposal_context["session_id"] = context_id
    return {
        "state": "PROPOSAL_READY" if result.status in {"PROPOSAL_DRAFT_READY", "PROPOSAL_DRAFT_PARTIAL"} else "GAP_SELECTED",
        "proposal_status": result.status,
        "proposal_message": result.message_to_user,
        "proposal": result.proposal,
        "writing_guidance": result.writing_guidance,
        "proposal_context": result.proposal_context,
        "proposal_limitations": result.limitations,
        "proposal_audit": result.audit,
    }


def build_research_response(payload: dict, provider=None, synthesis_provider=None) -> dict:
    catalog = load_catalog()
    directions = {item["direction_id"]: item for item in catalog["directions"]}
    groups = {item["group_id"]: item["label"] for item in catalog["groups"]}

    selected_id = str(payload.get("selected_direction_id", "")).strip()
    if selected_id not in directions:
        raise RequestError("请选择知识库中的有效研究方向")
    direction = directions[selected_id]
    direction_profile = load_direction_profiles().get(selected_id)
    fine_question = str(payload.get("fine_grained_question") or "").strip() or None
    zh_count = positive_count(payload, "chinese_count", 10)
    en_count = positive_count(payload, "english_count", 20)
    derived_path = "focused_question" if fine_question else "top_five_subdirections"

    routed_pools = tuple(direction_profile["journal_pool_ids"]) if direction_profile else journal_pools_for(direction)
    discovery = (provider or build_dynamic_provider()).discover(
        DiscoveryRequest(
            selected_direction_id=selected_id,
            research_direction=direction["label"],
            fine_grained_question=fine_question,
            chinese_count=zh_count,
            english_count=en_count,
            journal_pool_ids=routed_pools,
        )
    )

    retrieval_complete = discovery.status in {"RETRIEVAL_COMPLETE", "RETRIEVAL_PARTIAL"}
    run_synthesis = payload.get("run_synthesis", True) is not False
    synthesis = None
    synthesis_job_id = None
    if retrieval_complete:
        corpus = getattr(discovery, "analysis_papers", None) or discovery.papers
        synthesis_request = SynthesisRequest(
            research_direction=direction["label"],
            fine_grained_question=fine_question,
            derived_path=derived_path,
            papers=tuple(corpus),
        )
        if run_synthesis:
            synthesis = (synthesis_provider or build_research_synthesis_provider()).synthesize(synthesis_request)
        else:
            synthesis_job_id = store_synthesis_job(synthesis_request)
    synthesis_complete = bool(synthesis and synthesis.status in {"SYNTHESIS_COMPLETE", "SYNTHESIS_PARTIAL"})

    path_label = "围绕细分问题定向检索" if fine_question else "发现最近五年研究最多的五个小方向"
    return {
        "state": "GAP_CANDIDATES_READY" if synthesis_complete else "PAPERS_DISCOVERED" if retrieval_complete else "QUERY_PLAN",
        "status_code": discovery.status,
        "message_to_user": discovery.message_to_user,
        "request": {
            "selected_direction_id": selected_id,
            "research_direction": direction["label"],
            "fine_grained_question": fine_question,
            "chinese_count": zh_count,
            "english_count": en_count,
            "derived_path": derived_path,
            "derived_path_label": path_label,
            "popularity_window_years": 5,
            "journal_pool_ids": list(routed_pools),
        },
        "local_match": {
            "label": direction["label"],
            "aliases": direction["aliases"],
            "groups": [groups[group_id] for group_id in direction["group_ids"]],
            "source_refs": direction["source_refs"],
            "knowledge_policy": "本地规则与写作范式优先精确匹配",
            "direction_profile": direction_profile,
        },
        "stages": [
            {"id": "catalog", "label": "方向目录匹配", "status": "complete"},
            {"id": "scope", "label": "IS/IM范围确认", "status": "complete"},
            {"id": "plan", "label": "检索路径确定", "status": "complete"},
            {"id": "discovery", "label": "动态论文检索", "status": "complete" if retrieval_complete else "blocked"},
            {"id": "synthesis", "label": "五方向与研究空白", "status": "complete" if synthesis_complete else "pending"},
        ],
        "next_allowed_actions": (["select_gap", "reset_request"] if synthesis_complete else ["run_synthesis", "reset_request"] if retrieval_complete else ["configure_dynamic_provider", "reset_request"]),
        "papers": discovery.papers,
        "search_log": discovery.search_log,
        "exclusion_log": discovery.exclusion_log,
        "shortages": discovery.shortages,
        "coverage_audit": getattr(discovery, "coverage_audit", {}),
        "provider_statuses": getattr(discovery, "provider_statuses", []),
        "expansion_log": getattr(discovery, "expansion_log", []),
        "dedupe_log": getattr(discovery, "dedupe_log", []),
        "candidate_traces": getattr(discovery, "candidate_traces", []),
        "lane_funnels": getattr(discovery, "lane_funnels", []),
        "chinese_coverage": getattr(discovery, "chinese_coverage", {}),
        "zero_result_diagnosis": getattr(discovery, "zero_result_diagnosis", {}),
        "score_config_version": getattr(discovery, "score_config_version", ""),
        "synthesis_job_id": synthesis_job_id,
        "synthesis_status": synthesis.status if synthesis else "SYNTHESIS_QUEUED" if synthesis_job_id else "SYNTHESIS_NOT_RUN",
        "synthesis_message": synthesis.message_to_user if synthesis else "论文已返回，五方向与研究空白将在下一阶段单独综合。" if synthesis_job_id else "论文发现未完成，未运行综合。",
        "top_subdirections": synthesis.top_subdirections if synthesis else [],
        "gap_candidates": synthesis.gap_candidates if synthesis else [],
        "synthesis_limitations": synthesis.limitations if synthesis else [],
        "synthesis_audit": synthesis.audit if synthesis else {},
    }


class AppHandler(BaseHTTPRequestHandler):
    server_version = "ProposalCompass/0.5"

    def log_message(self, format: str, *args) -> None:
        return

    def send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        mime, _ = mimetypes.guess_type(path.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{mime or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route == "/api/health":
            catalog = load_catalog()
            self.send_json({
                "status": "ok",
                "kb_version": KB_VERSION,
                "directions": catalog["direction_count"],
                "dynamic_provider": provider_name(),
                "chinese_retrieval": "enabled" if os.getenv("PROPOSAL_ENABLE_CHINESE_RETRIEVAL", "1").strip().lower() in {"1", "true", "yes", "on"} else "disabled",
                "synthesis_provider": synthesis_provider_name(),
                "journal_registry_ready": JOURNAL_REGISTRY_PATH.is_file(),
                "direction_profiles_ready": DIRECTION_PROFILE_PATH.is_file(),
                "openalex_authenticated": bool(os.getenv("OPENALEX_API_KEY")),
            })
            return
        if route == "/api/directions":
            self.send_json(public_catalog())
            return
        if route in {"/", "/index.html"}:
            self.send_file(STATIC_DIR / "index.html")
            return
        if route.startswith("/static/"):
            relative = Path(unquote(route.removeprefix("/static/")))
            target = (STATIC_DIR / relative).resolve()
            if STATIC_DIR.resolve() not in target.parents:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            self.send_file(target)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route not in {"/api/research", "/api/synthesize", "/api/proposal", "/api/configure/synthesis", "/api/configure/synthesis/clear", "/api/configure/retrieval", "/api/configure/retrieval/clear", "/api/evaluation/p0-model-baseline"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            if route == "/api/configure/synthesis/clear":
                for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"):
                    os.environ.pop(key, None)
                self.send_json({"configured": False, "provider": "unconfigured", "message_to_user": "当前进程中的DeepSeek配置已清除。"})
                return
            if route == "/api/configure/retrieval/clear":
                os.environ.pop("OPENALEX_API_KEY", None)
                self.send_json({"configured": False, "provider": "openalex_anonymous", "message_to_user": "当前进程中的OpenAlex密钥已清除；可继续使用受限匿名额度。"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 1_000_000:
                raise RequestError("请求内容为空或过大")
            if route in {"/api/configure/synthesis", "/api/configure/retrieval"} and not self.headers.get("Content-Type", "").lower().startswith("application/json"):
                raise RequestError("配置请求必须使用JSON")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise RequestError("请求必须是JSON对象")
            if route == "/api/configure/synthesis":
                self.send_json(configure_synthesis(payload))
            elif route == "/api/configure/retrieval":
                self.send_json(configure_retrieval(payload))
            elif route == "/api/evaluation/p0-model-baseline":
                if synthesis_provider_name() == "unconfigured":
                    raise RequestError("请先在检索设置中配置DeepSeek，再运行P0模型基线")
                self.send_json(run_model_baseline(
                    build_research_synthesis_provider(),
                    build_proposal_generation_provider(KB_ROOT),
                ))
            elif route == "/api/synthesize":
                self.send_json(run_synthesis_job(payload.get("job_id")))
            elif route == "/api/proposal":
                self.send_json(generate_proposal(payload))
            else:
                self.send_json(build_research_response(payload))
        except (json.JSONDecodeError, UnicodeDecodeError, RequestError) as exc:
            self.send_json({"status_code": "INVALID_REQUEST", "message_to_user": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception:
            self.send_json({"status_code": "INTERNAL_ERROR", "message_to_user": "本地服务出现错误，请检查知识库完整性。"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"Proposal Compass V0: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
