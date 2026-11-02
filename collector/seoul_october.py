"""Resume Seoul October APIhub collection; four workers, day-level git checkpoints."""
import concurrent.futures as cf
import datetime as dt
import hashlib,json,math,os,subprocess,threading,time,urllib.parse,urllib.request
from pathlib import Path
from validate_seoul import ROOT,parse_grid,value_at
KST=dt.timezone(dt.timedelta(hours=9))
DIR=ROOT/"archive/hub/seoul/2026-10"
SLOTS=(2,5,8,11,14,17,20,23)
LOCK=threading.Lock()
attempts=0
received=0
deadline=0
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":")))
    temp.replace(path)
def read(path,default):
    return json.loads(path.read_text()) if path.exists() else default
def stamp(t):return t.isoformat(timespec="seconds")
def requests_for_day(day):
    rows=[]
    for hour in SLOTS:
        valid=dt.datetime(2026,10,day,hour,tzinfo=KST)
        issued=valid-dt.timedelta(hours=24)
        for kind in ("TMP","POP","T1H","RN1"):
            params=dict(vars=kind)
            if kind in ("TMP","POP"):
                endpoint="nph-dfs_shrt_grd"
                params.update(tmfc=issued.strftime("%Y%m%d%H"),tmef=valid.strftime("%Y%m%d%H"))
            else:
                endpoint="nph-dfs_odam_grd"
                params.update(tmfc=valid.strftime("%Y%m%d%H%M"))
            rows.append((valid,issued,kind,endpoint,params))
    return rows
def request(endpoint,params,key,usage):
    global attempts,received
    for retry in range(2):
        with LOCK:
            if attempts>=1200 or received>=500_000_000 or time.monotonic()>deadline:
                raise RuntimeError("RunBudget")
            attempts+=1
        usage["attempts"]+=1
        try:
            query=urllib.parse.urlencode(dict(params,authKey=key))
            with urllib.request.urlopen("https://apihub.kma.go.kr/api/typ01/cgi-bin/url/"+endpoint+"?"+query,timeout=20) as r:
                raw=r.read(1_000_001)
            with LOCK:received+=len(raw)
            usage["receivedBytes"]+=len(raw)
            if len(raw)>1_000_000:raise ValueError("Oversize")
            grid=parse_grid(raw)
            if any(not math.isfinite(v) for v in grid):raise ValueError("NonFinite")
            value=value_at(grid,60,127)
            kind=params["vars"]
            lo,hi=(-90,65) if kind in ("TMP","T1H") else ((0,100) if kind=="POP" else (0,1000))
            if value is not None and not lo<=value<=hi:raise ValueError("ValueRange")
            return dict(value=value,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                        endpoint=endpoint,parameters=params,
                        retrievedAt=stamp(dt.datetime.now(KST)))
        except Exception as exc:
            usage["failedAttempts"]+=1
            if retry==1:raise RuntimeError(type(exc).__name__) from None
def day_collect(day,key):
    path=DIR/f"{day:02}.json"
    data=read(path,dict(day=day,region="seoul",grid=[60,127],responses={},usage=dict(attempts=0,receivedBytes=0,failedAttempts=0)))
    errors=[]
    for valid,issued,kind,endpoint,params in requests_for_day(day):
        rid=valid.strftime("%Y%m%d%H")+"-"+kind
        if rid in data["responses"]:continue
        try:data["responses"][rid]=request(endpoint,params,key,data["usage"])
        except Exception as exc:
            errors.append(dict(requestId=rid,error=type(exc).__name__))
            if "RunBudget" in str(exc):break
    data["errors"]=errors
    data["complete"]=len(data["responses"])==32
    return day,data
def git_save(day):
    if not os.environ.get("GITHUB_ACTIONS"):return
    for command in (["git","add",str(DIR.relative_to(ROOT))],
                    ["git","commit","-m",f"Checkpoint Seoul October day {day:02}"],
                    ["git","push","origin","HEAD:seoul-october-2026-data"]):
        subprocess.run(command,cwd=ROOT,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def summary():
    ds=[read(DIR/f"{d:02}.json",{}) for d in range(1,32)]
    return dict(region="seoul",month="2026-10",expectedDates=31,
                completeDates=sum(d.get("complete",False) for d in ds),
                responses=sum(len(d.get("responses",{})) for d in ds),
                attempts=sum(d.get("usage",{}).get("attempts",0) for d in ds),
                receivedBytes=sum(d.get("usage",{}).get("receivedBytes",0) for d in ds),
                failedAttempts=sum(d.get("usage",{}).get("failedAttempts",0) for d in ds),
                grid=[60,127],observationOffsetMinutes=0,
                methodStatus="experimental-api-publication-time",
                limitations=["API tmfc publication timestamp used as requested; no +50 minute adjustment.",
                             "RN1 accumulation alignment remains experimental.",
                             "Received bytes measure HTTP response bodies, not provider billing counters."])
def build(dist):
    report=summary()
    if report["completeDates"]!=31 or report["responses"]!=992:raise ValueError("Incomplete month")
    forecasts=[];observations=[];provenance=[]
    for day in range(1,32):
        data=read(DIR/f"{day:02}.json",{})
        for valid,issued,kind,endpoint,params in requests_for_day(day):
            rid=valid.strftime("%Y%m%d%H")+"-"+kind
            response=data["responses"][rid]
            if response["parameters"]!=params or response["endpoint"]!=endpoint:raise ValueError("Request provenance mismatch")
            if len(response["sha256"])!=64:raise ValueError("Missing hash")
            provenance.append(dict(requestId=rid,**response))
        for hour in SLOTS:
            valid=dt.datetime(2026,10,day,hour,tzinfo=KST);issued=valid-dt.timedelta(hours=24)
            get=lambda k:data["responses"][valid.strftime("%Y%m%d%H")+"-"+k]["value"]
            if get("TMP") is None or get("POP") is None:raise ValueError("Missing forecast values")
            forecasts.append(dict(region="seoul",issuedAt=stamp(issued),validAt=stamp(valid),temp=get("TMP"),pop=get("POP")))
            observations.append(dict(region="seoul",validAt=stamp(valid),temp=get("T1H"),rainMm=get("RN1")))
    if len(forecasts)!=248 or len({f["validAt"] for f in forecasts})!=248:raise ValueError("Coverage")
    if any(o["temp"] is None for o in observations):raise ValueError("Missing temperatures")
    period=dict(start="2026-10-01T00:00:00+09:00",end="2026-10-31T23:59:59+09:00",days=31,label="2026년 10월 · API 정각 기준")
    payload=dict(schemaVersion=1,source="KMA APIhub original historical grids",methodStatus=report["methodStatus"],
                 generatedAt=stamp(dt.datetime.now(KST)),period=period,forecasts=forecasts,observations=observations,
                 observationReference=dict(requestMinutes=0,offsetMinutes=0,meaning="API tmfc publication time; experimental reference"),
                 usage=report)
    file="history/2026-10-api/seoul.json"
    write(dist/file,payload)
    index=read(dist/"history-index.json",dict(schemaVersion=1,periods=[]))
    if any(p["id"]=="2026-10-api" for p in index["periods"]):index["periods"]=[p for p in index["periods"] if p["id"]!="2026-10-api"]
    index["periods"].append(dict(id="2026-10-api",**period,files=dict(seoul=file),
                                counts=dict(seoul=dict(temperature=248,rain=sum(o["rainMm"] is not None for o in observations),maximum=248))))
    index["periods"].sort(key=lambda p:p["start"],reverse=True)
    write(dist/"history-index.json",index);write(dist/"usage-seoul-2026-10.json",report)
    write(DIR/"summary.json",report)
    return report
def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--publish",action="store_true")
    args=parser.parse_args()
    if args.publish:
        report=build(ROOT/"dist")
        with (ROOT/"PROGRESS.md").open("a") as f:
            f.write("\n## 서울 2026년10월 API 자료 수집 완료\n"+json.dumps(report,ensure_ascii=False)+"\n248개 시각의24시간전 예보, 실황은 API요청 정각기준 독립 자료셋. 시각 의미 및 강수 구간 한계는 실험 상태.\n")
        print("SUMMARY "+json.dumps(report),flush=True);return
    global deadline
    key=os.environ.get("KMA_HUB_AUTH_KEY","").strip()
    if not key:raise SystemExit("Missing APIhub secret")
    deadline=time.monotonic()+25*60
    pending=[d for d in range(1,32) if not read(DIR/f"{d:02}.json",{}).get("complete")]
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(day_collect,d,key) for d in pending]
        for future in cf.as_completed(futures):
            day,data=future.result();write(DIR/f"{day:02}.json",data)
            write(DIR/"summary.json",summary());git_save(day)
            print("DAY "+json.dumps(dict(day=day,complete=data["complete"],responses=len(data["responses"]),usage=data["usage"])),flush=True)
    report=summary();print("SUMMARY "+json.dumps(report),flush=True)
    if report["completeDates"]!=31:raise SystemExit("Partial month saved; resume missing requests")
if __name__=="__main__":main()
