#!/usr/bin/env python3
from __future__ import annotations
from collections import Counter
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/'03_sources/source_registry.yaml'
data=yaml.safe_load(REG.read_text(encoding='utf-8'))
rows=[]
for r in data['resources']:
    local=r.get('local') or {'status':'pointer_only','runtime_fetch':'fallback_only','paths':[]}
    paths=[]
    for key in ('paths','fulltext_path','metadata_path','chapter_index_path','fts_index','topic_router'):
        value=local.get(key)
        if isinstance(value,list): paths.extend(value)
        elif value: paths.append(value)
    rows.append({
        'resource_id':r['id'], 'title':r['title'], 'type':r.get('type'),
        'local_status':local.get('status','pointer_only'),
        'runtime_fetch':local.get('runtime_fetch','fallback_only'),
        'local_paths':paths,
        'next_action': (
            'none_runtime_ready' if local.get('status')=='fulltext_chaptered_chunked_indexed' else
            'periodic_snapshot_refresh' if local.get('status')=='structured_snapshot' else
            'ingest_full_or_authorized_excerpt' if local.get('status')=='summary_card_only' else
            'localize_or_keep_explicit_gap'
        )
    })
counts=Counter(x['local_status'] for x in rows)
out={'version':'0.2.0','generated_on':'2026-08-21','startup_external_fetch':False,'counts':dict(counts),'resources':rows}
(ROOT/'03_sources/localization_status.yaml').write_text(yaml.safe_dump(out,allow_unicode=True,sort_keys=False,width=1000),encoding='utf-8')
md=['# 来源本地化状态','', '> 该文件区分“本地可直接检索”与“仅有外部指针”。Agent启动时不得遍历外部指针。','', '## 汇总','']
for k,v in sorted(counts.items()): md.append(f'- `{k}`：{v}')
md += ['', '| Source ID | 本地状态 | 运行时外部访问 | 下一步 |', '|---|---|---|---|']
for x in rows:
    md.append(f"| `{x['resource_id']}` | `{x['local_status']}` | `{x['runtime_fetch']}` | `{x['next_action']}` |")
(ROOT/'03_sources/localization_status.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(dict(counts))
