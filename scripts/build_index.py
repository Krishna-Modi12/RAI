"""Script to build or update the SQLite FTS5 knowledge index."""

from __future__ import annotations

import logging
import sys

from rai.rag.index import DB_PATH, build_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

if __name__ == "__main__":
    n = build_index()
    print(f"Knowledge FTS5 index ready: {n} sections indexed into {DB_PATH}")
    sys.exit(0 if n > 0 else 1)
