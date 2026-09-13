"""Pytest test isolation configuration for RAI.

Guarantees that test executions never mutate or pollute runtime production ledger files
such as ARTIFACTS / 'tickets.jsonl'.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from rai.config import ARTIFACTS


@pytest.fixture(autouse=True)
def isolate_tickets_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate tickets.jsonl to a temporary directory for each test run."""
    real_ledger = ARTIFACTS / "tickets.jsonl"
    temp_ledger = tmp_path / "isolated_tickets.jsonl"
    if real_ledger.exists():
        shutil.copyfile(real_ledger, temp_ledger)
    else:
        temp_ledger.write_text("", encoding="utf-8")
    monkeypatch.setenv("RAI_TICKET_LOG", str(temp_ledger))
    return temp_ledger
