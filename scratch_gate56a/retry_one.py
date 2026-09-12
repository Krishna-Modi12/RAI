import hashlib
import json
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
url = (
    "https://oedi-data-lake.s3.amazonaws.com/pvdaq/parquet/pvdata/"
    "system_id=34/year=2019/month=7/day=30/system_34__date_2019_07_30.snappy.000.parquet"
)
local_path = (
    REPO_ROOT
    / "data/raw/pvdaq/pvdaq/parquet/pvdata/system_id=34/year=2019/month=7/day=30/"
    "system_34__date_2019_07_30.snappy.000.parquet"
)
local_path.parent.mkdir(parents=True, exist_ok=True)

resp = requests.get(url, timeout=60)
assert resp.status_code == 200, resp.status_code
local_path.write_bytes(resp.content)
sha256 = hashlib.sha256(resp.content).hexdigest()
rec = {
    "system_id": 34,
    "date": "2019-07-30",
    "source_url": url,
    "local_path": str(local_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    "retrieval_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "http_status": resp.status_code,
    "file_size": len(resp.content),
    "sha256": sha256,
    "status": "OK",
}
print(json.dumps(rec, indent=2))

records_path = REPO_ROOT / "scratch_gate56a" / "download_records.json"
with records_path.open() as f:
    recs = json.load(f)
for i, r in enumerate(recs):
    if r["system_id"] == 34 and r["date"] == "2019-07-30":
        recs[i] = rec
        break
with records_path.open("w") as f:
    json.dump(recs, f, indent=2)

ok = sum(1 for r in recs if r["status"] == "OK")
print(f"{ok}/{len(recs)} OK")
