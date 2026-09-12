"""Gate 5.6A real acquisition script. Downloads real OEDI PVDAQ daily parquet files
for the frozen cohort, preserving the exact S3 key layout under data/raw/pvdaq/.
Computes SHA-256 for every file. No fabrication, no synthetic fallback: a missing
or failed file is recorded as MISSING in the download manifest, not silently skipped.
"""
from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_ROOT = REPO_ROOT / "data" / "raw" / "pvdaq"
BASE_URL = "https://oedi-data-lake.s3.amazonaws.com/"

WINDOW_START = date(2019, 6, 1)
WINDOW_END = date(2019, 8, 29)  # inclusive, 90 days total

COHORT_SYSTEMS = [1239, 1283, 34, 1430, 1433]


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def s3_key(system_id: int, d: date) -> str:
    return (
        f"pvdaq/parquet/pvdata/system_id={system_id}/year={d.year}/"
        f"month={d.month}/day={d.day}/system_{system_id}__date_{d.year:04d}_{d.month:02d}_{d.day:02d}.snappy.000.parquet"
    )


def fetch_one(system_id: int, d: date) -> dict:
    key = s3_key(system_id, d)
    url = BASE_URL + key
    local_path = RAW_ROOT / key
    local_path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "system_id": system_id,
        "date": d.isoformat(),
        "source_url": url,
        "local_path": str(local_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "retrieval_time_utc": None,
        "http_status": None,
        "file_size": None,
        "sha256": None,
        "status": None,
    }
    try:
        resp = requests.get(url, timeout=30)
        rec["http_status"] = resp.status_code
        rec["retrieval_time_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if resp.status_code == 200 and len(resp.content) > 0:
            local_path.write_bytes(resp.content)
            rec["file_size"] = len(resp.content)
            rec["sha256"] = hashlib.sha256(resp.content).hexdigest()
            rec["status"] = "OK"
        else:
            rec["status"] = "MISSING_OR_ERROR"
    except Exception as exc:  # noqa: BLE001
        rec["status"] = f"EXCEPTION: {exc}"
        rec["retrieval_time_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return rec


def main() -> None:
    tasks = [(sid, d) for sid in COHORT_SYSTEMS for d in daterange(WINDOW_START, WINDOW_END)]
    print(f"Total files to fetch: {len(tasks)}")
    records = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(fetch_one, sid, d) for sid, d in tasks]
        done = 0
        for fut in as_completed(futures):
            records.append(fut.result())
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(tasks)} done")
    ok = sum(1 for r in records if r["status"] == "OK")
    print(f"Completed: {ok}/{len(records)} OK")
    out_path = REPO_ROOT / "scratch_gate56a" / "download_records.json"
    out_path.write_text(json.dumps(records, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
