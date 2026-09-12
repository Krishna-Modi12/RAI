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

# Per-system acquisition windows. NOT chosen for model performance -- chosen because
# direct S3 prefix listing (real, verified via `curl` against oedi-data-lake.s3.amazonaws.com,
# not inferred from the systems_20250729.csv summary columns) confirmed these are the windows
# with actual daily pvdata parquet partitions present. Systems 1239/1283/34's pvdata partitions
# cover 2019 (matching their metadata table's first/last timestamps). Systems 1430 and 1433's
# metadata table claims coverage through 2024, but their real pvdata parquet partitions on S3
# stop at year=2017 and year=2018 respectively (metadata/data inconsistency in the archive --
# documented in candidate_systems.json / timestamp_quality.csv, not silently patched over).
# 2017-06-01..2017-08-29 was verified present (all 31/31/30 days) for both 1430 and 1433 before
# being selected here.
SYSTEM_WINDOWS = {
    1239: (date(2019, 6, 1), date(2019, 8, 29)),
    1283: (date(2019, 6, 1), date(2019, 8, 29)),
    34: (date(2019, 6, 1), date(2019, 8, 29)),
    1430: (date(2017, 6, 1), date(2017, 8, 29)),
    1433: (date(2017, 6, 1), date(2017, 8, 29)),
}

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
    tasks = [
        (sid, d)
        for sid in COHORT_SYSTEMS
        for d in daterange(*SYSTEM_WINDOWS[sid])
    ]
    print(f"Total files to fetch: {len(tasks)}")
    records = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(fetch_one, sid, d) for sid, d in tasks]
        for done, fut in enumerate(as_completed(futures), start=1):
            records.append(fut.result())
            if done % 50 == 0:
                print(f"  {done}/{len(tasks)} done")
    ok = sum(1 for r in records if r["status"] == "OK")
    print(f"Completed: {ok}/{len(records)} OK")
    out_path = REPO_ROOT / "scratch_gate56a" / "download_records.json"
    out_path.write_text(json.dumps(records, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
