"""Regenerate the consolidated task log in CHECKPOINT.md from docs/checkpoints/*.md.

Each task writes its own record file, so parallel agents never contend for CHECKPOINT.md.
This script merges those records into the section below the CONSOLIDATED marker, leaving
everything above it (contracts, environment, task board) hand-maintained.

Usage:  python scripts/update_checkpoint.py
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = ROOT / "CHECKPOINT.md"
RECORDS = ROOT / "docs" / "checkpoints"
MARKER = "<!-- CONSOLIDATED:BEGIN -->"

FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_record(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {"task": path.stem, "phase": "?", "status": "unknown"}
    if m := FRONTMATTER.match(text):
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
        body = text[m.end() :]
    else:
        body = text
    meta["body"] = body.strip()
    return meta


def section(record: dict[str, str], heading: str) -> str:
    """Pull one '## <heading>' block out of a record body."""
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", re.DOTALL | re.MULTILINE)
    if m := pattern.search(record["body"]):
        return m.group(1).strip()
    return ""


STATUS_ICON = {"complete": "✅", "partial": "🟡", "blocked": "🔴", "unknown": "⬜"}


def main() -> int:
    if not CHECKPOINT.exists():
        print("CHECKPOINT.md missing", file=sys.stderr)
        return 1

    records = [
        parse_record(p)
        for p in sorted(RECORDS.glob("*.md"))
        if p.name != "TEMPLATE.md"
    ]

    lines: list[str] = [
        MARKER,
        "",
        "## Consolidated task log",
        "",
        (
            f"_Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC from "
            f"{len(records)} task record(s) in `docs/checkpoints/`._"
        ),
        "",
    ]

    if not records:
        lines += ["No task records yet.", ""]
    else:
        done = sum(1 for r in records if r.get("status") == "complete")
        lines += [
            f"**{done}/{len(records)} task records complete.**",
            "",
            "| | Task | Phase | Status |",
            "|---|---|---|---|",
        ]
        for r in records:
            icon = STATUS_ICON.get(r.get("status", "unknown"), "⬜")
            lines.append(f"| {icon} | {r['task']} | {r.get('phase','?')} | {r.get('status')} |")
        lines.append("")

        for r in records:
            icon = STATUS_ICON.get(r.get("status", "unknown"), "⬜")
            lines += [f"### {icon} {r['task']}", ""]
            for heading in ("What was built", "How it was verified", "Measured results", "Limitations"):
                if content := section(r, heading):
                    lines += [f"**{heading}**", "", content, ""]

    existing = CHECKPOINT.read_text(encoding="utf-8")
    head = existing.split(MARKER)[0].rstrip()
    CHECKPOINT.write_text(head + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"CHECKPOINT.md updated from {len(records)} record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
