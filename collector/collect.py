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
REGIONS=[('yeoju',71,121),('seoul',60,127),('busan',98,76)]
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
    all_items=[]
    for page in range(1,11):
        q={**params,'serviceKey':urllib.parse.unquote(key),'dataType':'JSON','numOfRows':1000,'pageNo':page}
        url=BASE+endpoint+'?'+urllib.parse.urlencode(q)
        result=None
        for attempt in range(3):
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
        if len(all_items)>=int(body.get('totalCount',0)): return all_items
        if not rows: raise RuntimeError('KMA pagination incomplete')
    raise RuntimeError('KMA pagination exceeded safety limit')

def parse_forecast(items,region,base,retrieved,nx,ny):
    grouped={}
    for row in items:
        if int(row['nx'])!=nx or int(row['ny'])!=ny: raise ValueError('Grid mismatch')
        if str(row['baseDate'])!=base.strftime('%Y%m%d') or str(row['baseTime']).zfill(4)!=base.strftime('%H%M'): raise ValueError('Issue time mismatch')
        valid=dt.datetime.strptime(str(row['fcstDate'])+str(row['fcstTime']).zfill(4),'%Y%m%d%H%M').replace(tzinfo=KST)
        grouped.setdefault(valid,{})[row['category']]=row['fcstValue']
    output=[]
    for valid,c in grouped.items():
        temp=numeric(c.get('TMP'),-90,65);pop=numeric(c.get('POP'),0,100)
        if temp is not None and pop is not None and valid>retrieved and valid>base:
            output.append(dict(region=region,issuedAt=stamp(base),validAt=stamp(valid),temp=temp,pop=pop,retrievedAt=stamp(retrieved),nx=nx,ny=ny))
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

def main():
    key=os.environ.get('KMA_SERVICE_KEY','').strip()
    if not key:
        print('KMA_SERVICE_KEY is required. Add it as an Actions Secret; never put it in source.')
        return 1
    now=dt.datetime.now(KST);base=forecast_base(now);errors=0;archive=ROOT/'archive';obs_path=archive/'observations.json'
    observations=read(obs_path,[]);obs={(o['region'],o['validAt']):o for o in observations}
    for region,nx,ny in REGIONS:
        path=archive/'forecasts'/base.strftime('%Y-%m-%d')/(base.strftime('%H%M')+'-'+region+'.json')
        if not path.exists():
            try:
                params=dict(base_date=base.strftime('%Y%m%d'),base_time=base.strftime('%H%M'),nx=nx,ny=ny)
                items=request_items('getVilageFcst',params,key)
                rows=parse_forecast(items,region,base,now,nx,ny)
                write(path,{'source':'KMA getVilageFcst','retrievedAt':stamp(now),'rows':rows})
            except Exception:
                errors+=1;print(region+': forecast unavailable (details suppressed to protect credentials)')
        # Poll 6 past hours so an interrupted run can recover observations.
        for back in range(1,7):
            valid=(now-dt.timedelta(hours=back)).replace(minute=0,second=0,microsecond=0)
            k=(region,stamp(valid))
            if k in obs and obs[k]['temp'] is not None and obs[k]['rainMm'] is not None: continue
            try:
                params=dict(base_date=valid.strftime('%Y%m%d'),base_time=valid.strftime('%H%M'),nx=nx,ny=ny)
                items=request_items('getUltraSrtNcst',params,key)
                row=parse_observation(items,region,valid,nx,ny)
                prior=obs.get(k,{})
                # A missing field in a retry must not erase an earlier measurement.
                for field in ('temp','rainMm'):
                    if row[field] is None and prior.get(field) is not None: row[field]=prior[field]
                row['retrievedAt']=stamp(now);obs[k]=row
            except Exception:
                errors+=1;print(region+': observation unavailable at '+valid.strftime('%m-%d %H:%M'))
    write(obs_path,list(obs.values()))
    cutoff=now-dt.timedelta(days=30);forecasts=[]
    for path in sorted((archive/'forecasts').glob('*/*.json')):
        # Old raw snapshots remain immutable for future annual reports.
        if path.parent.name<(cutoff-dt.timedelta(days=5)).strftime('%Y-%m-%d'): continue
        forecasts.extend(f for f in read(path,{})['rows'] if dt.datetime.fromisoformat(f['validAt'])>cutoff and (dt.datetime.fromisoformat(f['validAt'])-dt.datetime.fromisoformat(f['issuedAt'])==dt.timedelta(hours=24) or dt.datetime.fromisoformat(f['issuedAt'])>now-dt.timedelta(days=3)))
    visible_obs=[o for o in obs.values() if dt.datetime.fromisoformat(o['validAt'])>cutoff]
    write(ROOT/'dist/data.json',dict(schemaVersion=1,generatedAt=stamp(now),source='KMA getVilageFcst + getUltraSrtNcst',methodStatus='experimental-unvalidated',errors=errors,forecasts=forecasts,observations=visible_obs))
    print('Saved: '+str(len(forecasts))+' forecast rows; '+str(len(visible_obs))+' observations; '+str(errors)+' request failures.')
    # A non-zero exit warns Actions; workflow persists partial successes regardless.
    return 1 if errors else 0

if __name__=='__main__': sys.exit(main())
