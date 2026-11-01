"""Cross-check Seoul APIhub grid values against existing official CSV import."""
import hashlib,json,os,re,urllib.request,urllib.parse,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def parse_grid(raw):
    values=[float(s) for s in re.split(r"[\s,]+",raw.decode("utf-8").strip()) if s]
    if len(values)!=149*253:raise ValueError("Unexpected grid length")
    return values
def value_at(values,x,y):
    if not (1<=x<=149 and 1<=y<=253):raise ValueError("Invalid coordinate")
    v=values[(y-1)*149+x-1]
    return None if v==-99 else v
def main():
    key=os.environ.get("KMA_HUB_AUTH_KEY","").strip()
    if not key:raise SystemExit("Missing hub secret")
    fixture=json.loads((ROOT/"dist/history/2026-09-window/seoul.json").read_text())
    rows=[]
    for valid in ("2026-09-10T02:00:00+09:00","2026-09-20T14:00:00+09:00"):
        fc=next(f for f in fixture["forecasts"] if f["validAt"]==valid)
        ob=next(o for o in fixture["observations"] if o["validAt"]==valid)
        clean=lambda s:s[:13].replace("-","").replace("T","")
        cases=[("TMP","nph-dfs_shrt_grd",dict(tmfc=clean(fc["issuedAt"]),tmef=clean(valid),vars="TMP"),fc["temp"]),
               ("POP","nph-dfs_shrt_grd",dict(tmfc=clean(fc["issuedAt"]),tmef=clean(valid),vars="POP"),fc["pop"]),
               ("T1H","nph-dfs_odam_grd",dict(tmfc=clean(valid)+"00",vars="T1H"),ob["temp"]),
               ("RN1","nph-dfs_odam_grd",dict(tmfc=clean(valid)+"00",vars="RN1"),ob["rainMm"])]
        for kind,endpoint,params,expected in cases:
            try:
                url="https://apihub.kma.go.kr/api/typ01/cgi-bin/url/"+endpoint+"?"+urllib.parse.urlencode(dict(params,authKey=key))
                with urllib.request.urlopen(url,timeout=45) as r:raw=r.read(1000000)
                actual=value_at(parse_grid(raw),60,127)
                match=actual==expected if actual is None or expected is None else abs(actual-expected)<0.001
                rows.append(dict(validAt=valid,kind=kind,expected=expected,actual=actual,match=match,sha256=hashlib.sha256(raw).hexdigest()))
            except Exception as exc:
                rows.append(dict(validAt=valid,kind=kind,match=False,error=type(exc).__name__))
            print(json.dumps(rows[-1]),flush=True)
    report=dict(region="seoul",grid=[60,127],status="matched" if all(r["match"] for r in rows) else "needs-investigation",checks=rows,
                limitation="Two timestamps only; rain interval meaning and full month coverage remain unvalidated.",
                gridReference="https://apihub.kma.go.kr/apiList.do?seqApi=10")
    p=ROOT/"seoul-validation";p.mkdir(exist_ok=True)
    (p/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if report["status"]!="matched":raise SystemExit("Cross-check mismatch; do not publish scores")
if __name__=="__main__":main()
