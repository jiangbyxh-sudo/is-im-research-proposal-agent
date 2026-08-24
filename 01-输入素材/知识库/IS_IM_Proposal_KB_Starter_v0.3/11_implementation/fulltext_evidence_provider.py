"""Optional GROBID sidecar client and TEI-to-Evidence-Matrix conversion."""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4
from xml.etree import ElementTree as ET


GROBID_EVIDENCE_VERSION = "grobid-fulltext-evidence-1.0.0"
MAX_TEI_CHARACTERS = 50 * 1024 * 1024
TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NAMESPACE}


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _page_from_coords(coords: str | None) -> int | None:
    first = str(coords or "").split(";", 1)[0].split(",", 1)[0].strip()
    try:
        return int(first) if first else None
    except ValueError:
        return None


def _element_text(element: ET.Element | None) -> str:
    return _clean(" ".join(element.itertext())) if element is not None else ""


def _sentences_from_paragraph(paragraph: ET.Element) -> list[tuple[str, str | None, str]]:
    sentences = paragraph.findall(".//tei:s", NS)
    if sentences:
        return [(_element_text(item), item.get("coords"), "s") for item in sentences if _element_text(item)]
    text = _element_text(paragraph)
    return [(text, paragraph.get("coords"), "p")] if len(text) >= 20 else []


def parse_grobid_tei(tei_xml: str, paper_id: str, source_sha256: str, fallback_title: str = "") -> dict:
    """Parse in-memory TEI; raw TEI is deliberately not returned or persisted."""
    if not isinstance(tei_xml, str) or not tei_xml.strip():
        raise ValueError("empty_tei_response")
    if len(tei_xml) > MAX_TEI_CHARACTERS:
        raise ValueError("tei_response_too_large")
    upper_prefix = tei_xml[:4096].upper()
    if "<!DOCTYPE" in upper_prefix or "<!ENTITY" in upper_prefix:
        raise ValueError("unsafe_tei_declaration")
    root = ET.fromstring(tei_xml)
    title = _element_text(root.find(".//tei:titleStmt/tei:title", NS)) or _clean(fallback_title)
    body = root.find(".//tei:text/tei:body", NS)
    collected: list[tuple[str, str, str | None, str]] = []

    def visit_div(div: ET.Element, inherited_section: str) -> None:
        section = _element_text(div.find("./tei:head", NS)) or inherited_section or "Body"
        for child in list(div):
            local = child.tag.rsplit("}", 1)[-1]
            if local == "p":
                for text, coords, element_type in _sentences_from_paragraph(child):
                    collected.append((section, text, coords, element_type))
            elif local == "div":
                visit_div(child, section)

    if body is not None:
        for child in list(body):
            local = child.tag.rsplit("}", 1)[-1]
            if local == "div":
                visit_div(child, "Body")
            elif local == "p":
                for text, coords, element_type in _sentences_from_paragraph(child):
                    collected.append(("Body", text, coords, element_type))

    spans = []
    cursor = 0
    for index, (section, text, coords, element_type) in enumerate(collected, start=1):
        if len(text) < 20:
            continue
        start, end = cursor, cursor + len(text)
        cursor = end + 1
        span_seed = f"{paper_id}|{source_sha256}|{section}|{index}|{text}"
        spans.append({
            "span_id": "span_" + hashlib.sha256(span_seed.encode("utf-8")).hexdigest()[:20],
            "paper_id": paper_id,
            "evidence_level": "fulltext",
            "source_field": "fulltext",
            "start_char": start,
            "end_char": end,
            "text": text,
            "section": section,
            "page": _page_from_coords(coords),
            "coords": coords,
            "tei_element": element_type,
        })
    source_text = "\n".join(item["text"] for item in spans)
    source_text_hash = _sha256(source_text.encode("utf-8")) if source_text else None
    matrix_hash = hashlib.sha256(
        "|".join(f"{item['span_id']}:{item['paper_id']}" for item in spans).encode("utf-8")
    ).hexdigest()
    return {
        "version": GROBID_EVIDENCE_VERSION,
        "paper_count": 1,
        "formal_evidence_paper_count": 1 if spans else 0,
        "span_count": len(spans),
        "matrix_hash": matrix_hash,
        "papers": [{
            "paper_id": paper_id,
            "title": title,
            "evidence_level": "fulltext" if spans else "unavailable",
            "formal_evidence_eligible": bool(spans),
            "span_ids": [item["span_id"] for item in spans],
            "source_text_hash": source_text_hash,
            "source_document_hash": source_sha256,
        }],
        "spans": spans,
        "parser_audit": {
            "provider": "grobid",
            "source_document_hash": source_sha256,
            "raw_tei_persisted": False,
            "title_level_fallback_allowed": False,
            "section_anchor_count": len({item["section"] for item in spans}),
            "page_anchor_count": sum(item["page"] is not None for item in spans),
        },
    }


class GrobidClientProtocol(Protocol):
    def health(self) -> dict: ...
    def version(self) -> str: ...
    def process_fulltext(self, pdf_bytes: bytes, filename: str) -> str: ...


class GrobidHttpClient:
    def __init__(self, base_url: str, timeout: int = 120) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("invalid_grobid_base_url")
        self.base_url = base_url.rstrip("/")
        self.timeout = max(1, timeout)

    def _get(self, path: str, accept: str) -> bytes:
        with urlopen(Request(f"{self.base_url}{path}", headers={"Accept": accept}), timeout=self.timeout) as response:
            return response.read()

    def health(self) -> dict:
        payload = self._get("/api/health", "application/json")
        return json.loads(payload.decode("utf-8"))

    def version(self) -> str:
        raw = self._get("/api/version", "application/json").decode("utf-8").strip()
        payload = json.loads(raw)
        if not isinstance(payload, dict) or not _clean(payload.get("version")):
            raise ValueError("invalid_grobid_version_response")
        return _clean(payload["version"])

    @staticmethod
    def multipart_payload(pdf_bytes: bytes, filename: str) -> tuple[bytes, str]:
        boundary = f"----ProposalCompass{uuid4().hex}"
        chunks: list[bytes] = []

        def field(name: str, value: str) -> None:
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode(),
            ])

        for name, value in (
            ("consolidateHeader", "0"), ("consolidateCitations", "0"),
            ("includeRawCitations", "1"), ("segmentSentences", "1"),
            ("teiCoordinates", "s"),
        ):
            field(name, value)
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name) or "paper.pdf"
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="input"; filename="{safe_name}"\r\n'.encode(),
            b"Content-Type: application/pdf\r\n\r\n",
            pdf_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        return b"".join(chunks), f"multipart/form-data; boundary={boundary}"

    def process_fulltext(self, pdf_bytes: bytes, filename: str) -> str:
        body, content_type = self.multipart_payload(pdf_bytes, filename)
        request = Request(
            f"{self.base_url}/api/processFulltextDocument",
            data=body,
            method="POST",
            headers={"Accept": "application/xml", "Content-Type": content_type},
        )
        with urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8")


@dataclass(frozen=True)
class FulltextExtractionRequest:
    pdf_path: Path
    paper_id: str
    title: str = ""
    max_pdf_bytes: int = 50 * 1024 * 1024


@dataclass
class FulltextExtractionResult:
    status: str
    evidence_matrix: dict = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    audit: dict = field(default_factory=dict)
    message_to_user: str = ""


class UnconfiguredFulltextEvidenceProvider:
    def extract(self, request: FulltextExtractionRequest) -> FulltextExtractionResult:
        return FulltextExtractionResult(
            status="FULLTEXT_SERVICE_NOT_CONFIGURED",
            limitations=["GROBID sidecar未配置。"],
            message_to_user="全文解析服务尚未配置；未把题名或PDF文件名作为正式证据。",
            audit={"title_level_fallback_used": False},
        )


class GrobidFulltextEvidenceProvider:
    def __init__(self, client: GrobidClientProtocol) -> None:
        self.client = client

    @staticmethod
    def _ready(health: dict) -> bool:
        if health.get("status") in {"up", "healthy", "ready", "UP", "READY"}:
            return True
        return bool(health.get("initialized") is True or health.get("ready") is True)

    def extract(self, request: FulltextExtractionRequest) -> FulltextExtractionResult:
        try:
            path = request.pdf_path.resolve()
            if not request.paper_id.strip():
                raise ValueError("paper_id_required")
            if not path.is_file() or path.suffix.casefold() != ".pdf":
                raise ValueError("valid_pdf_path_required")
            size = path.stat().st_size
            if size <= 4 or size > request.max_pdf_bytes:
                raise ValueError("pdf_size_out_of_bounds")
            pdf_bytes = path.read_bytes()
            if not pdf_bytes.startswith(b"%PDF-"):
                raise ValueError("invalid_pdf_signature")
            health = self.client.health()
            if not isinstance(health, dict):
                raise ValueError("invalid_grobid_health_response")
            if not self._ready(health):
                return FulltextExtractionResult(
                    status="FULLTEXT_SERVICE_UNAVAILABLE",
                    limitations=["GROBID readiness check failed."],
                    audit={"health": health, "title_level_fallback_used": False},
                )
            version = self.client.version()
            tei = self.client.process_fulltext(pdf_bytes, path.name)
            source_hash = _sha256(pdf_bytes)
            matrix = parse_grobid_tei(tei, request.paper_id.strip(), source_hash, request.title)
            if not matrix["span_count"]:
                return FulltextExtractionResult(
                    status="FULLTEXT_EXTRACTION_EMPTY",
                    evidence_matrix=matrix,
                    limitations=["GROBID未提取到可用正文句。"],
                    audit={"grobid_version": version, "source_sha256": source_hash, "pdf_byte_count": size, "title_level_fallback_used": False},
                )
            return FulltextExtractionResult(
                status="FULLTEXT_EVIDENCE_READY",
                evidence_matrix=matrix,
                audit={
                    "version": GROBID_EVIDENCE_VERSION,
                    "grobid_version": version,
                    "source_sha256": source_hash,
                    "pdf_byte_count": size,
                    "raw_pdf_persisted_by_provider": False,
                    "raw_tei_persisted": False,
                    "title_level_fallback_used": False,
                },
                message_to_user=f"已提取{matrix['span_count']}条全文证据句，等待Claim绑定。",
            )
        except (
            OSError, ValueError, ET.ParseError, HTTPError, URLError,
            TimeoutError, UnicodeDecodeError, json.JSONDecodeError,
        ) as exc:
            return FulltextExtractionResult(
                status="FULLTEXT_EXTRACTION_FAILED",
                limitations=[str(exc) if isinstance(exc, ValueError) else type(exc).__name__],
                audit={"title_level_fallback_used": False, "error_type": type(exc).__name__},
                message_to_user="全文解析失败；未降级为题名级正式证据。",
            )


def build_fulltext_evidence_provider():
    enabled = os.getenv("PROPOSAL_ENABLE_GROBID", "0").strip().casefold() in {"1", "true", "yes", "on"}
    if not enabled:
        return UnconfiguredFulltextEvidenceProvider()
    client = GrobidHttpClient(
        os.getenv("GROBID_BASE_URL", "http://127.0.0.1:8070"),
        timeout=int(os.getenv("GROBID_TIMEOUT", "120")),
    )
    return GrobidFulltextEvidenceProvider(client)
