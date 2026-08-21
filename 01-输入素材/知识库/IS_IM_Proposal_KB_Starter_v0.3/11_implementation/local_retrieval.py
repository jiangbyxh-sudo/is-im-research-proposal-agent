#!/usr/bin/env python3
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
