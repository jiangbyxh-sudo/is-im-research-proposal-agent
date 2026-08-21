#!/usr/bin/env python3
from pathlib import Path
import json
import sqlite3
import yaml

ROOT = Path(__file__).resolve().parents[1]
registry = yaml.safe_load((ROOT / '03_sources/source_registry.yaml').read_text(encoding='utf-8'))
external = [r for r in registry['resources'] if r.get('url')]
assert len(external) == 44, len(external)
for r in external:
    local = r.get('local', {})
    assert local.get('status') not in {'pointer_only', 'summary_card_only', None}, r['id']
    assert local.get('fulltext_cached') is False, r['id']
    for rel in local.get('paths', []):
        assert (ROOT / rel).exists(), (r['id'], rel)
chunks = [json.loads(x) for x in (ROOT / '03_sources/local_knowledge/index/external_chunks.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
assert len({x['resource_id'] for x in chunks}) == 44
con = sqlite3.connect(ROOT / '03_sources/local_knowledge/index/local_fts.sqlite')
assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
fts_external = sum(n for priority, n in con.execute('SELECT source_priority, COUNT(*) FROM chunks_fts GROUP BY source_priority').fetchall() if str(priority).startswith('external_'))
assert fts_external == len(chunks), (fts_external, len(chunks))
print('external validation ok', len(external), len(chunks))
