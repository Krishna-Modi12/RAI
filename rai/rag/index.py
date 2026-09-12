"""SQLite FTS5 knowledge corpus indexing for domain manuals, SOPs, and incident logs."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from rai.config import ARTIFACTS, KNOWLEDGE

log = logging.getLogger(__name__)

DB_PATH = ARTIFACTS / "index" / "knowledge.db"


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Extract YAML frontmatter and body from markdown."""
    frontmatter: dict[str, str] = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2]
            for line in fm_text.strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    frontmatter[k.strip()] = v.strip().strip('"').strip("'")
    return frontmatter, body.strip()


def _split_into_sections(body: str) -> list[tuple[str, str]]:
    """Split markdown body by '## ' headings into (section_name, section_content)."""
    sections: list[tuple[str, str]] = []
    current_title = "Overview"
    current_lines: list[str] = []

    for line in body.splitlines():
        if line.startswith("## "):
            if current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    sections.append((current_title, text))
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        text = "\n".join(current_lines).strip()
        if text:
            sections.append((current_title, text))

    return sections


def build_index(db_path: Path = DB_PATH) -> int:
    """Build SQLite FTS5 database from all knowledge markdown documents."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Drop existing tables
    cur.execute("DROP TABLE IF EXISTS docs_fts")
    cur.execute("DROP TABLE IF EXISTS docs_meta")

    # Create FTS5 virtual table with porter stemmer
    cur.execute(
        """
        CREATE VIRTUAL TABLE docs_fts USING fts5(
            doc_id,
            title,
            section,
            content,
            asset_type UNINDEXED,
            component UNINDEXED,
            tokenize = 'porter unicode61'
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE docs_meta (
            doc_id TEXT PRIMARY KEY,
            title TEXT,
            asset_type TEXT,
            component TEXT,
            kind TEXT,
            version TEXT,
            filepath TEXT
        )
        """
    )

    count = 0
    doc_files = list(KNOWLEDGE.glob("**/*.md"))
    log.info("Found %d markdown documents in %s", len(doc_files), KNOWLEDGE)

    for path in doc_files:
        try:
            raw_text = path.read_text(encoding="utf-8")
        except Exception as e:
            log.warning("Could not read %s: %s", path, e)
            continue

        fm, body = _parse_frontmatter(raw_text)
        doc_id = fm.get("doc_id", path.stem)
        title = fm.get("title", path.stem.replace("-", " ").title())
        asset_type = fm.get("asset_type", "")
        component = fm.get("component", "")
        kind = fm.get("kind", path.parent.name)
        version = fm.get("version", "1.0")

        cur.execute(
            """
            INSERT OR REPLACE INTO docs_meta (doc_id, title, asset_type, component, kind, version, filepath)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, title, asset_type, component, kind, version, str(path)),
        )

        sections = _split_into_sections(body)
        for sec_title, sec_content in sections:
            cur.execute(
                """
                INSERT INTO docs_fts (doc_id, title, section, content, asset_type, component)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (doc_id, title, sec_title, sec_content, asset_type, component),
            )
            count += 1

    conn.commit()
    conn.close()
    log.info("Indexed %d sections across %d documents into %s", count, len(doc_files), db_path)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    n = build_index()
    print(f"Successfully indexed {n} sections into {DB_PATH}")
