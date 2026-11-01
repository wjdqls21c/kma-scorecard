"""Bounded Seoul observation timing diagnosis; no automatic score publication."""
import datetime as dt,json,os,urllib.request,urllib.parse
from pathlib import Path
from validate_seoul import parse_grid,value_at,ROOT
def main():
    key=os.environ.get("KMA_HUB_AUTH_KEY","").strip()
    if not key:raise SystemExit("Missing hub secret")
    data=json.loads((ROOT/"dist/history/2026-09-window/seoul.json").read_text())
    rows=[]
    for target in ("2026-09-10T02:00:00+09:00","2026-09-20T14:00:00+09:00"):
        expected=next(o["temp"] for o in data["observations"] if o["validAt"]==target)
        for offset in (-10,0,10,20,30,40,50,60):
            moment=dt.datetime.fromisoformat(target)+dt.timedelta(minutes=offset)
            try:
                params=dict(tmfc=moment.strftime("%Y%m%d%H%M"),vars="T1H",authKey=key)
                url="https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-dfs_odam_grd?"+urllib.parse.urlencode(params)
                with urllib.request.urlopen(url,timeout=30) as response:raw=response.read(1000000)
                actual=value_at(parse_grid(raw),60,127)
                row=dict(target=target,offsetMinutes=offset,expected=expected,actual=actual,
                         match=actual is not None and abs(actual-expected)<0.001)
            except Exception as exc:row=dict(target=target,offsetMinutes=offset,error=type(exc).__name__)
            rows.append(row);print(json.dumps(row),flush=True)
    out=ROOT/"seoul-timing";out.mkdir(exist_ok=True)
    (out/"report.json").write_text(json.dumps(dict(status="diagnostic-only",checks=rows),indent=2))
if __name__=="__main__":main()
