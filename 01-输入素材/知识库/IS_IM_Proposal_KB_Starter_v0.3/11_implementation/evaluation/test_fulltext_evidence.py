from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path


IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from claim_store import ClaimStore  # noqa: E402
from fulltext_evidence_provider import (  # noqa: E402
    FulltextExtractionRequest,
    FulltextExtractionResult,
    GrobidFulltextEvidenceProvider,
    GrobidHttpClient,
    UnconfiguredFulltextEvidenceProvider,
    parse_grobid_tei,
)
from research_skills.adapters import (  # noqa: E402
    P3FulltextEvidenceExtractionSkillAdapter,
    build_default_registry,
)
from research_skills.contracts import ResearchSkillContext, SkillRunStatus  # noqa: E402


TEI_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc><titleStmt><title>Calibrated Trust Study</title></titleStmt></fileDesc></teiHeader>
  <text><body>
    <div><head>Introduction</head><p>
      <s coords="1,10.0,20.0,100.0,12.0">Explanations can improve calibrated trust when users understand system limits.</s>
      <s coords="1,10.0,35.0,100.0,12.0">However, prior familiarity provides a plausible alternative explanation.</s>
    </p></div>
    <div><head>Method</head><p>
      <s coords="2,10.0,20.0,100.0,12.0">A factorial experiment compared explanation formats across expertise levels.</s>
    </p></div>
  </body></text>
</TEI>"""


class FakeGrobidClient:
    def __init__(self, *, health=None, tei=TEI_FIXTURE):
        self.health_payload = {"ready": True} if health is None else health
        self.tei = tei
        self.process_calls = 0

    def health(self):
        return self.health_payload

    def version(self):
        return "fixture-0.9.0"

    def process_fulltext(self, pdf_bytes, filename):
        self.process_calls += 1
        self.last_pdf = pdf_bytes
        self.last_filename = filename
        return self.tei


class FakeReadyProvider:
    def extract(self, request):
        matrix = parse_grobid_tei(TEI_FIXTURE, request.paper_id, "a" * 64, request.title)
        return FulltextExtractionResult(
            status="FULLTEXT_EVIDENCE_READY",
            evidence_matrix=matrix,
            audit={"raw_tei_persisted": False},
        )


class JsonVersionClient(GrobidHttpClient):
    def __init__(self):
        super().__init__("http://127.0.0.1:8070")
        self.accept = ""

    def _get(self, path, accept):
        self.accept = accept
        self.path = path
        return b'{"version":"0.9.0","revision":"0.9.0"}'


class FulltextEvidenceTests(unittest.TestCase):
    def test_tei_sentences_become_fulltext_spans_with_anchors(self):
        matrix = parse_grobid_tei(TEI_FIXTURE, "P1", "a" * 64)
        self.assertEqual(3, matrix["span_count"])
        self.assertEqual(["Introduction", "Introduction", "Method"], [item["section"] for item in matrix["spans"]])
        self.assertEqual([1, 1, 2], [item["page"] for item in matrix["spans"]])
        self.assertTrue(all(item["evidence_level"] == "fulltext" for item in matrix["spans"]))
        self.assertEqual("a" * 64, matrix["papers"][0]["source_document_hash"])
        self.assertNotEqual("a" * 64, matrix["papers"][0]["source_text_hash"])
        self.assertNotIn("<TEI", json.dumps(matrix))

    def test_parsed_matrix_is_accepted_by_claim_store(self):
        matrix = parse_grobid_tei(TEI_FIXTURE, "P1", "b" * 64)
        store = ClaimStore(matrix)
        claim = store.add_formal_claim(
            "Explanations may improve calibrated trust under bounded conditions.",
            [{"paper_id": "P1", "evidence_span_id": matrix["spans"][0]["span_id"]}],
        )
        self.assertTrue(store.audit()["valid"])
        self.assertEqual("fulltext", claim["bindings"][0]["evidence_span"]["evidence_level"])

    def test_tei_parser_rejects_entity_declarations(self):
        malicious = """<?xml version="1.0"?><!DOCTYPE TEI [<!ENTITY x "unsafe">]><TEI>&x;</TEI>"""
        with self.assertRaisesRegex(ValueError, "unsafe_tei_declaration"):
            parse_grobid_tei(malicious, "P1", "b" * 64)

    def test_provider_validates_pdf_and_returns_evidence_without_source_path(self):
        client = FakeGrobidClient()
        provider = GrobidFulltextEvidenceProvider(client)
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "fixture.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nfixture")
            result = provider.extract(FulltextExtractionRequest(pdf_path, "P1"))
            serialized = json.dumps(asdict(result), ensure_ascii=False)
        self.assertEqual("FULLTEXT_EVIDENCE_READY", result.status)
        self.assertEqual(1, client.process_calls)
        self.assertEqual(3, result.evidence_matrix["span_count"])
        self.assertNotIn(str(pdf_path), serialized)
        self.assertFalse(result.audit["raw_pdf_persisted_by_provider"])

    def test_unready_service_blocks_without_processing_or_title_fallback(self):
        client = FakeGrobidClient(health={"ready": False})
        provider = GrobidFulltextEvidenceProvider(client)
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "fixture.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nfixture")
            result = provider.extract(FulltextExtractionRequest(pdf_path, "P1", "A title"))
        self.assertEqual("FULLTEXT_SERVICE_UNAVAILABLE", result.status)
        self.assertEqual(0, client.process_calls)
        self.assertFalse(result.audit["title_level_fallback_used"])

    def test_invalid_pdf_signature_fails_before_network(self):
        client = FakeGrobidClient()
        provider = GrobidFulltextEvidenceProvider(client)
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "fixture.pdf"
            pdf_path.write_bytes(b"not-a-pdf")
            result = provider.extract(FulltextExtractionRequest(pdf_path, "P1"))
        self.assertEqual("FULLTEXT_EXTRACTION_FAILED", result.status)
        self.assertEqual(["invalid_pdf_signature"], result.limitations)
        self.assertEqual(0, client.process_calls)

    def test_unconfigured_provider_never_falls_back_to_title(self):
        result = UnconfiguredFulltextEvidenceProvider().extract(
            FulltextExtractionRequest(Path("missing.pdf"), "P1", "Only a title")
        )
        self.assertEqual("FULLTEXT_SERVICE_NOT_CONFIGURED", result.status)
        self.assertFalse(result.audit["title_level_fallback_used"])

    def test_multipart_contract_contains_sentence_and_coordinate_options(self):
        body, content_type = GrobidHttpClient.multipart_payload(b"%PDF-fixture", "paper name.pdf")
        self.assertIn("multipart/form-data; boundary=", content_type)
        self.assertIn(b'name="segmentSentences"\r\n\r\n1', body)
        self.assertIn(b'name="teiCoordinates"\r\n\r\ns', body)
        self.assertIn(b'name="input"; filename="paper_name.pdf"', body)
        self.assertIn(b"%PDF-fixture", body)

    def test_version_endpoint_uses_json_contract(self):
        client = JsonVersionClient()
        self.assertEqual("0.9.0", client.version())
        self.assertEqual("/api/version", client.path)
        self.assertEqual("application/json", client.accept)

    def test_compose_file_pins_digest_and_loopback_port(self):
        compose = (
            IMPLEMENTATION / "research_skills/sidecars/grobid/compose.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("lfoppiano/grobid@sha256:24ba90eb1c959f65d812bcdb2cf79c677fa5fd7b95235de616b8bc9fa1317849", compose)
        self.assertIn('127.0.0.1:8070:8070', compose)
        self.assertNotIn(":latest", compose)

    def test_registry_maps_fulltext_status_without_emitting_path(self):
        registry = build_default_registry(fulltext_provider=FakeReadyProvider())
        result = registry.run(
            "p3.fulltext_evidence_extraction",
            {"pdf_path": "C:/private/paper.pdf", "paper_id": "P1"},
            ResearchSkillContext(stage="P3"),
        )
        self.assertEqual(SkillRunStatus.COMPLETE, result.status)
        self.assertEqual("FULLTEXT_EVIDENCE_READY", result.upstream_status)
        self.assertNotIn("C:/private/paper.pdf", json.dumps(result.as_dict()))
        self.assertFalse(result.audit["source_path_emitted"])

    def test_adapter_maps_unconfigured_status_to_blocked(self):
        adapter = P3FulltextEvidenceExtractionSkillAdapter(UnconfiguredFulltextEvidenceProvider())
        execution = adapter.execute(
            {"pdf_path": "missing.pdf", "paper_id": "P1"},
            ResearchSkillContext(stage="P3"),
        )
        self.assertEqual(SkillRunStatus.BLOCKED, execution.result_status)
        self.assertEqual("FULLTEXT_SERVICE_NOT_CONFIGURED", execution.upstream_status)


if __name__ == "__main__":
    unittest.main()
