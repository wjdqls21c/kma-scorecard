"""Bounded APIhub archive probe. Never print request URLs or authentication."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request
import urllib.parse
import urllib.error

BASE = "https://apihub.kma.go.kr/api/typ01/cgi-bin/url/"
def main():
    key = os.environ.get("KMA_HUB_AUTH_KEY", "").strip()
    if not key:
        raise SystemExit("KMA_HUB_AUTH_KEY secret is missing")
    out = Path("hub-probe")
    out.mkdir(exist_ok=True)
    cases = [
        ("forecast-TMP", "nph-dfs_shrt_grd", dict(tmfc="2026080902", tmef="2026081002", vars="TMP")),
        ("forecast-POP", "nph-dfs_shrt_grd", dict(tmfc="2026080902", tmef="2026081002", vars="POP")),
        ("observation-T1H", "nph-dfs_odam_grd", dict(tmfc="202608100200", vars="T1H")),
        ("observation-RN1", "nph-dfs_odam_grd", dict(tmfc="202608100200", vars="RN1")),
    ]
    report = []
    for label, endpoint, params in cases:
        try:
            query = urllib.parse.urlencode(dict(params, authKey=key))
            req = urllib.request.Request(BASE + endpoint + "?" + query)
            with urllib.request.urlopen(req, timeout=45) as response:
                raw = response.read(8_000_001)
                status = response.status
            if len(raw) > 8_000_000:
                report.append(dict(case=label, status="oversized"))
                continue
            body = raw.decode("utf-8", errors="replace")
            # Only accept a grid-shaped numeric response. Never persist an error page.
            numbers = re.findall(r"(?<![A-Za-z0-9])[-+]?\d+(?:\.\d+)?", body)
            rows = [line for line in body.splitlines() if re.fullmatch(r"[\s,0-9.eE+\-]+", line) and re.search(r"\d", line)]
            accepted = len(numbers) >= 149*253 and len(rows) > 0 and key not in body and "<html" not in body.lower()
            item = dict(case=label, http=status, bytes=len(raw), numericTokens=len(numbers),
                        numericRows=len(rows), gridCandidate=accepted)
            if accepted:
                (out / (label + ".txt")).write_bytes(raw)
                item["sha256"] = hashlib.sha256(raw).hexdigest()
                item["numericSample"] = rows[0][:100]
            else:
                # Expose only a fixed allowlist of error categories.
                item["category"] = next((s for s in ("AUTH", "LIMIT", "ERROR", "NO DATA", "NODATA")
                                         if s in body.upper()), "unexpected-response")
            report.append(item)
        except urllib.error.HTTPError as exc:
            report.append(dict(case=label, http=exc.code, category="http-error"))
        except Exception as exc:
            report.append(dict(case=label, category=type(exc).__name__))
        print(json.dumps(report[-1], ensure_ascii=False), flush=True)
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    if not all(item.get("gridCandidate") for item in report):
        raise SystemExit("Archive probe incomplete; inspect safe report")
if __name__ == "__main__":
    main()
