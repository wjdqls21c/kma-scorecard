"""Compare Seoul CSV observations with API at fixed 00/50-minute offsets.
Diagnostic only: neither offset is adopted as a scoring correction.
"""
import datetime as dt,json,os,urllib.request,urllib.parse
from validate_seoul import parse_grid,value_at,ROOT

def select_samples(data):
    obs=data["observations"]
    wet=[o for o in obs if o["rainMm"] is not None and o["rainMm"]>=0.1]
    dry=[next(o for o in obs if o["validAt"]==t) for t in
         ("2026-09-10T02:00:00+09:00","2026-09-20T14:00:00+09:00")]
    return wet[:6]+dry

def main():
    key=os.environ.get("KMA_HUB_AUTH_KEY","").strip()
    if not key:raise SystemExit("Missing hub secret")
    data=json.loads((ROOT/"dist/history/2026-09-window/seoul.json").read_text())
    rows=[]
    for observation in select_samples(data):
        target=observation["validAt"]
        for offset in (0,50):
            moment=dt.datetime.fromisoformat(target)+dt.timedelta(minutes=offset)
            for kind,field in (("T1H","temp"),("RN1","rainMm")):
                expected=observation[field]
                try:
                    params=dict(tmfc=moment.strftime("%Y%m%d%H%M"),vars=kind,authKey=key)
                    url="https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-dfs_odam_grd?"+urllib.parse.urlencode(params)
                    with urllib.request.urlopen(url,timeout=30) as response:raw=response.read(1000000)
                    actual=value_at(parse_grid(raw),60,127)
                    row=dict(target=target,kind=kind,offsetMinutes=offset,expected=expected,actual=actual,
                             match=actual is not None and expected is not None and abs(actual-expected)<0.001)
                except Exception as exc:row=dict(target=target,kind=kind,offsetMinutes=offset,error=type(exc).__name__)
                rows.append(row);print(json.dumps(row),flush=True)
    summary=[dict(kind=k,offsetMinutes=o,n=sum(r.get("kind")==k and r["offsetMinutes"]==o for r in rows),
                  matches=sum(r.get("kind")==k and r["offsetMinutes"]==o and r.get("match",False) for r in rows))
             for k in ("T1H","RN1") for o in (0,50)]
    print("SUMMARY "+json.dumps(summary),flush=True)
    out=ROOT/"seoul-timing";out.mkdir(exist_ok=True)
    (out/"report.json").write_text(json.dumps(dict(status="diagnostic-only",checks=rows,summary=summary),indent=2))
    if any("error" in r for r in rows):raise SystemExit("Incomplete diagnostic")
if __name__=="__main__":main()
