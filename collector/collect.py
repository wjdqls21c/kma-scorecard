"""KMA snapshots. Standard-library only. Never print HTTP URLs or secrets."""
import datetime as dt
import json
import math
import os
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
KST=dt.timezone(dt.timedelta(hours=9))
REGION_CATALOG=json.loads((ROOT/'dist/regions.json').read_text())['regions']
REGIONS=[(r['id'],r['nx'],r['ny']) for r in REGION_CATALOG]
REQUEST_LIMIT=1200
_request_count=0
_deadline=None
_request_cache={}
BASE='https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/'

def stamp(t): return t.astimezone(KST).isoformat(timespec='seconds')
def numeric(v,lo,hi):
    try:
        n=float(v)
        return n if math.isfinite(n) and lo<=n<=hi else None
    except (TypeError,ValueError): return None

def forecast_base(now):
    # Allow 40 minutes for publication. Delays become missing samples, never substitutes.
    candidate=(now-dt.timedelta(minutes=40)).replace(minute=0,second=0,microsecond=0)
    while candidate.hour not in (2,5,8,11,14,17,20,23): candidate-=dt.timedelta(hours=1)
    return candidate

def request_items(endpoint,params,key):
    global _request_count
    cache_key=(endpoint,tuple(sorted(params.items())))
    if cache_key in _request_cache:return _request_cache[cache_key]
    all_items=[]
    for page in range(1,11):
        q={**params,'serviceKey':urllib.parse.unquote(key),'dataType':'JSON','numOfRows':1000,'pageNo':page}
        url=BASE+endpoint+'?'+urllib.parse.urlencode(q)
        result=None
        for attempt in range(3):
            if _request_count>=REQUEST_LIMIT or (_deadline and time.monotonic()>_deadline):raise RuntimeError('Collection request/time budget reached')
            _request_count+=1
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'KMA-scorecard/0.1'})
                with urllib.request.urlopen(req,timeout=25) as res: result=json.load(res)['response']
                if str(result['header']['resultCode'])!='00': raise ValueError('API status')
                break
            except Exception:
                if attempt==2: raise RuntimeError('KMA request failed; check key approval, quota and availability') from None
                time.sleep(1+attempt)
        body=result['body'];items=body.get('items',{})
        rows=items.get('item',[]) if isinstance(items,dict) else []
        if isinstance(rows,dict): rows=[rows]
        all_items.extend(rows)
        if len(all_items)>=int(body.get('totalCount',0)):
            _request_cache[cache_key]=all_items
            return all_items
        if not rows: raise RuntimeError('KMA pagination incomplete')
    raise RuntimeError('KMA pagination exceeded safety limit')

def parse_forecast(items,region,base,retrieved,nx,ny,retrospective=False):
    grouped={}
    for row in items:
        if int(row['nx'])!=nx or int(row['ny'])!=ny: raise ValueError('Grid mismatch')
        if str(row['baseDate'])!=base.strftime('%Y%m%d') or str(row['baseTime']).zfill(4)!=base.strftime('%H%M'): raise ValueError('Issue time mismatch')
        valid=dt.datetime.strptime(str(row['fcstDate'])+str(row['fcstTime']).zfill(4),'%Y%m%d%H%M').replace(tzinfo=KST)
        grouped.setdefault(valid,{})[row['category']]=row['fcstValue']
    output=[]
    for valid,c in grouped.items():
        temp=numeric(c.get('TMP'),-90,65);pop=numeric(c.get('POP'),0,100)
        eligible=(valid-base==dt.timedelta(hours=24) and retrieved-dt.timedelta(days=1)<=valid<=retrieved) if retrospective else valid>retrieved
        if temp is not None and pop is not None and eligible and valid>base:
            output.append(dict(region=region,issuedAt=stamp(base),validAt=stamp(valid),temp=temp,pop=pop,retrievedAt=stamp(retrieved),nx=nx,ny=ny,retrievalMode='retrospective-api' if retrospective else 'live-snapshot'))
    if not output: raise ValueError('No usable forecast')
    return output

def parse_observation(items,region,valid,nx,ny):
    c={}
    for row in items:
        if int(row['nx'])!=nx or int(row['ny'])!=ny: raise ValueError('Grid mismatch')
        if str(row['baseDate'])!=valid.strftime('%Y%m%d') or str(row['baseTime']).zfill(4)!=valid.strftime('%H%M'): raise ValueError('Observation time mismatch')
        c[row['category']]=row['obsrValue']
    temp=numeric(c.get('T1H'),-90,65);rain=numeric(c.get('RN1'),0,1000)
    if temp is None and rain is None: raise ValueError('No usable observation')
    return dict(region=region,validAt=stamp(valid),temp=temp,rainMm=rain,nx=nx,ny=ny)

def read(path,default): return json.loads(path.read_text()) if path.exists() else default

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n');tmp.replace(path)

def compact_export(forecasts,observations,now):
    cutoff=now-dt.timedelta(days=30)
    unique={(f['region'],f['issuedAt'],f['validAt']):f for f in forecasts}
    issues={}
    for f in unique.values():issues.setdefault(f['region'],set()).add(f['issuedAt'])
    latest={r:set(sorted(v)[-2:]) for r,v in issues.items()}
    fs=[f for f in unique.values() if dt.datetime.fromisoformat(f['validAt'])>cutoff and (dt.datetime.fromisoformat(f['validAt'])-dt.datetime.fromisoformat(f['issuedAt'])==dt.timedelta(hours=24) or f['issuedAt'] in latest[f['region']])]
    os=[o for o in observations if dt.datetime.fromisoformat(o['validAt'])>cutoff]
    return fs,os

def save_daily(root,forecasts,observations):
    by_day={}
    for kind,rows in [('forecasts',forecasts),('observations',observations)]:
        for row in rows:
            if kind=='forecasts' and dt.datetime.fromisoformat(row['validAt'])-dt.datetime.fromisoformat(row['issuedAt'])!=dt.timedelta(hours=24):continue
            by_day.setdefault(row['validAt'][:10],{'forecasts':[],'observations':[]})[kind].append(row)
    for day,values in by_day.items():
        path=root/'daily'/(day+'.json');prior=read(path,{'schemaVersion':1,'forecasts':[],'observations':[]})
        for kind in ('forecasts','observations'):
            key=lambda r:(r['region'],r.get('issuedAt'),r['validAt'])
            rows={key(r):r for r in prior[kind]}
            for r in values[kind]:
                k=key(r)
                if k not in rows:rows[k]=r
                elif kind=='observations':
                    # Fill missing fields only. Preserve first observed valid values.
                    for field in ('temp','rainMm'):
                        if rows[k].get(field) is None and r.get(field) is not None:rows[k][field]=r[field]
            prior[kind]=sorted(rows.values(),key=key)
        write(path,prior)

def main():
    global _deadline
    key=os.environ.get('KMA_SERVICE_KEY','').strip()
    if not key:
        print('KMA_SERVICE_KEY is required. Add it as an Actions Secret; never put it in source.');return 1
    _deadline=time.monotonic()+14*60
    now=dt.datetime.now(KST);base=forecast_base(now);errors=0;archive=ROOT/'archive';cutoff=now-dt.timedelta(days=30)
    observations=read(archive/'observations.json',[])
    forecasts=[]
    # Existing immutable snapshots remain readable during migration.
    for path in sorted((archive/'forecasts').glob('*/*.json')):
        if path.parent.name>=(cutoff-dt.timedelta(days=5)).strftime('%Y-%m-%d'):forecasts.extend(read(path,{}).get('rows',[]))
    for path in sorted((archive/'daily').glob('*.json')):
        if path.stem>=(cutoff-dt.timedelta(days=2)).strftime('%Y-%m-%d'):
            prior=read(path,{});forecasts.extend(prior.get('forecasts',[]));observations.extend(prior.get('observations',[]))
    recent=read(archive/'recent-forecasts.json',[]);forecasts.extend(recent)
    obs={(o['region'],o['validAt']):o for o in observations}
    known_issues={(f['region'],f['issuedAt']) for f in forecasts}
    for index,(region,nx,ny) in enumerate(REGIONS):
        if errors>=20 or time.monotonic()>_deadline or _request_count>=REQUEST_LIMIT:
            errors+=1;print('Stopped within request/time/error budget; partial results retained.');break
        for issue,retro in [(base,False),(base-dt.timedelta(days=1),True)]:
            if (region,stamp(issue)) in known_issues:continue
            try:
                params=dict(base_date=issue.strftime('%Y%m%d'),base_time=issue.strftime('%H%M'),nx=nx,ny=ny)
                items=request_items('getVilageFcst',params,key)
                rows=parse_forecast(items,region,issue,now,nx,ny,retrospective=retro)
                forecasts.extend(rows)
                if not retro:recent.extend(rows)
            except Exception:
                errors+=1;print(region+': '+('historical' if retro else 'current')+' forecast unavailable (credential details suppressed)')
        # Only the eight daily evaluation slots need observations.
        for back in range(1,7):
            valid=(now-dt.timedelta(hours=back)).replace(minute=0,second=0,microsecond=0)
            if valid.hour not in (2,5,8,11,14,17,20,23):continue
            k=(region,stamp(valid))
            if k in obs and obs[k]['temp'] is not None and obs[k]['rainMm'] is not None:continue
            try:
                params=dict(base_date=valid.strftime('%Y%m%d'),base_time=valid.strftime('%H%M'),nx=nx,ny=ny)
                items=request_items('getUltraSrtNcst',params,key);row=parse_observation(items,region,valid,nx,ny)
                for field in ('temp','rainMm'):
                    if row[field] is None and obs.get(k,{}).get(field) is not None:row[field]=obs[k][field]
                row['retrievedAt']=stamp(now);obs[k]=row
            except Exception:
                errors+=1;print(region+': observation unavailable at '+valid.strftime('%m-%d %H:%M'))
        if index%10==9:
            save_daily(archive,forecasts,list(obs.values()))
            print('Progress: '+str(index+1)+'/'+str(len(REGIONS))+' regions; requests '+str(_request_count))
    save_daily(archive,forecasts,list(obs.values()))
    visible_fs,visible_obs=compact_export(forecasts,list(obs.values()),now)
    write(archive/'observations.json',visible_obs)
    recent_fs,_=compact_export(recent,[],now)
    recent_fs=[f for f in recent_fs if dt.datetime.fromisoformat(f['issuedAt'])>now-dt.timedelta(days=1)]
    # Latest two full issue versions; exact-24h rows remain in immutable daily files.
    latest={r:sorted({f['issuedAt'] for f in recent_fs if f['region']==r})[-2:] for r,_,_ in REGIONS}
    write(archive/'recent-forecasts.json',[f for f in recent_fs if f['issuedAt'] in latest[f['region']]])
    write(ROOT/'dist/data.json',dict(schemaVersion=1,generatedAt=stamp(now),source='KMA live snapshots + issue-time historical API queries',methodStatus='experimental-unvalidated',errors=errors,regionCount=len(REGIONS),requests=_request_count,forecasts=visible_fs,observations=visible_obs))
    print('Saved: '+str(len(visible_fs))+' forecast rows; '+str(len(visible_obs))+' observations; '+str(errors)+' request failures; '+str(_request_count)+' requests.')
    return 1 if errors else 0

if __name__=='__main__':sys.exit(main())
