"""SQLite FTS5 knowledge retrieval engine for domain manuals, SOPs, and incident logs."""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

from rai.rag.index import DB_PATH, build_index
from rai.schemas import KnowledgeCitation

log = logging.getLogger(__name__)


def _sanitize_fts_query(query: str) -> str:
    """Sanitize user query for SQLite FTS5 syntax."""
    # Extract alpha-numeric tokens
    tokens = re.findall(r"[A-Za-z0-9_-]+", query)
    if not tokens:
        return '""'
    # Format tokens with prefix wildcards for flexible matching: token*
    formatted = [f'"{t}"*' if len(t) > 3 else f'"{t}"' for t in tokens if len(t) >= 2]
    if not formatted:
        return f'"{tokens[0]}"'
    # Join with OR or NEAR for ranking
    return " OR ".join(formatted)


def search(
    query: str,
    k: int = 5,
    asset_type: str | None = None,
    component: str | None = None,
    db_path: Path = DB_PATH,
) -> list[KnowledgeCitation]:
    """Search knowledge corpus with BM25 ranking and optional asset/component filtering."""
    if not db_path.exists():
        log.info("Knowledge index %s does not exist. Building now...", db_path)
        build_index(db_path)

    sanitized = _sanitize_fts_query(query)
    if sanitized == '""':
        return []

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    sql = """
        SELECT
            doc_id,
            title,
            section,
            content,
            bm25(docs_fts) AS rank_score
        FROM docs_fts
        WHERE docs_fts MATCH ?
    """
    params: list[Any] = [sanitized]

    if asset_type:
        sql += " AND asset_type = ?"
        params.append(asset_type)
    if component:
        sql += " AND component = ?"
        params.append(component)

    sql += " ORDER BY rank_score ASC LIMIT ?"
    params.append(k)

    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
    except sqlite3.OperationalError as e:
        log.warning("FTS search error with query %r: %s. Falling back to plain terms.", query, e)
        # Fallback to simple phrase query
        simple_tokens = " ".join(re.findall(r"[A-Za-z0-9]+", query)[:4])
        try:
            cur.execute(
                """
                SELECT doc_id, title, section, content, bm25(docs_fts) as rank_score
                FROM docs_fts
                WHERE docs_fts MATCH ?
                ORDER BY rank_score ASC LIMIT ?
                """,
                [simple_tokens, k],
            )
            rows = cur.fetchall()
        except Exception:
            rows = []
    finally:
        conn.close()

    citations: list[KnowledgeCitation] = []
    for doc_id, title, section, content, rank_score in rows:
        # Convert BM25 negative score to a normalized positive similarity proxy [0..1]
        score = max(0.1, min(0.99, round(1.0 / (1.0 + abs(float(rank_score))), 3)))
        snippet = content[:320].strip() + ("..." if len(content) > 320 else "")
        citations.append(
            KnowledgeCitation(
                doc_id=doc_id,
                title=title,
                section=section,
                snippet=snippet,
                score=score,
                retrieval="fts5",
            )
        )

    return citations


def list_documents(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Return all catalogued documents with metadata."""
    if not db_path.exists():
        build_index(db_path)

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT doc_id, title, asset_type, component, kind, version FROM docs_meta ORDER BY title ASC")
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "doc_id": r[0],
            "title": r[1],
            "asset_type": r[2],
            "component": r[3],
            "kind": r[4],
            "version": r[5],
        }
        for r in rows
    ]


def get_document(doc_id: str, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    """Retrieve full text and metadata for a specific document."""
    if not db_path.exists():
        build_index(db_path)

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "SELECT doc_id, title, asset_type, component, kind, version, filepath FROM docs_meta WHERE doc_id = ?",
        (doc_id,),
    )
    meta = cur.fetchone()
    if not meta:
        conn.close()
        return None

    filepath = Path(meta[6])
    body = filepath.read_text(encoding="utf-8") if filepath.exists() else ""

    cur.execute(
        "SELECT section, content FROM docs_fts WHERE doc_id = ?",
        (doc_id,),
    )
    sections = [{"section": s[0], "content": s[1]} for s in cur.fetchall()]
    conn.close()

    return {
        "doc_id": meta[0],
        "title": meta[1],
        "asset_type": meta[2],
        "component": meta[3],
        "kind": meta[4],
        "version": meta[5],
        "sections": sections,
        "raw_text": body,
    }
