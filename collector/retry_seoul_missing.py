"""Retry only missing Seoul diagnostic requests; never logs credentials/URLs."""
import json,os,urllib.request,urllib.parse
from validate_seoul import ROOT,parse_grid,value_at
def main():
    key=os.environ.get("KMA_HUB_AUTH_KEY","").strip()
    if not key:raise SystemExit("Missing hub secret")
    report=json.loads((ROOT/"archive/validation/seoul-wet-timing.json").read_text())
    for row in report["checks"]:
        if "error" not in row:continue
        assert row["target"]=="2026-09-01T11:00:00+09:00" and row["offsetMinutes"]==0
        kind=row["kind"]
        for attempt in range(3):
            try:
                query=urllib.parse.urlencode(dict(tmfc="202609011100",vars=kind,authKey=key))
                with urllib.request.urlopen("https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-dfs_odam_grd?"+query,timeout=30) as r:raw=r.read(1000000)
                actual=value_at(parse_grid(raw),60,127)
                fixture=json.loads((ROOT/"dist/history/2026-09-window/seoul.json").read_text())
                obs=next(o for o in fixture["observations"] if o["validAt"]==row["target"])
                expected=obs["temp" if kind=="T1H" else "rainMm"]
                row.update(expected=expected,actual=actual,match=actual is not None and abs(actual-expected)<0.001)
                del row["error"]
                break
            except Exception as exc:row["error"]=type(exc).__name__
        print("RESULT "+json.dumps(row),flush=True)
    failures=sum("error" in r for r in report["checks"])
    print("REMAINING_ERRORS "+str(failures),flush=True)
    out=ROOT/"seoul-retry";out.mkdir(exist_ok=True)
    (out/"report.json").write_text(json.dumps(report,indent=2))
    if failures:raise SystemExit("Requests still incomplete")
if __name__=="__main__":main()
