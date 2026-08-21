#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import sqlite3
import yaml

ROOT = Path(__file__).resolve().parents[1]
for path in ROOT.rglob('*.yaml'):
    yaml.safe_load(path.read_text(encoding='utf-8'))
for path in ROOT.rglob('*.json'):
    if path.name == 'checksums.json':
        continue
    json.loads(path.read_text(encoding='utf-8'))
all_path = ROOT / '03_sources/local_knowledge/index/all_chunks.jsonl'
chunks = [json.loads(x) for x in all_path.read_text(encoding='utf-8').splitlines() if x.strip()]
ids = set()
for row in chunks:
    assert row['chunk_id'] not in ids, row['chunk_id']
    ids.add(row['chunk_id'])
    assert (ROOT / row['local_path']).exists(), row['local_path']
    assert hashlib.sha256(row['content'].encode('utf-8')).hexdigest() == row['content_sha256'], row['chunk_id']
con = sqlite3.connect(ROOT / '03_sources/local_knowledge/index/local_fts.sqlite')
assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
assert con.execute('SELECT COUNT(*) FROM chunks_fts').fetchone()[0] == len(chunks)
checks = json.loads((ROOT / 'checksums.json').read_text(encoding='utf-8'))
if isinstance(checks, dict):
    for rel, digest in checks.items():
        path = ROOT / rel
        assert path.exists(), rel
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, rel
print('local validation ok', len(chunks), len(checks))
