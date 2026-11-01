"""Publish verified imports as small files per period and region, without network access."""
import argparse,calendar,datetime as dt,json,re
from pathlib import Path
from collect import KST,REGION_CATALOG,read,write

def publish(inputs,dist):
    allowed={r['id'] for r in REGION_CATALOG};buckets={};metadata={};sources={}
    for path in inputs:
        d=read(Path(path),{})
        if d.get('schemaVersion')!=1:raise ValueError('Unsupported import schema')
        fixed=d.get('period')
        for kind in ('forecasts','observations'):
            for row in d[kind]:
                rid=row['region']
                if rid not in allowed or not re.fullmatch('[a-z0-9-]+',rid):raise ValueError('Unknown region')
                t=dt.datetime.fromisoformat(row['validAt']).astimezone(KST)
                if kind=='forecasts' and dt.datetime.fromisoformat(row['validAt'])-dt.datetime.fromisoformat(row['issuedAt'])!=dt.timedelta(hours=24):continue
                if fixed:
                    period_id=fixed['start'][:7]+'-window';period=dict(fixed)
                    if not fixed['start']<=row['validAt']<=fixed['end']:continue
                else:
                    period_id=t.strftime('%Y-%m');days=calendar.monthrange(t.year,t.month)[1]
                    period={'start':t.replace(day=1,hour=0,minute=0,second=0).isoformat(timespec='seconds'),'end':t.replace(day=days,hour=23,minute=59,second=59).isoformat(timespec='seconds'),'days':days,'label':f'{t.year}년 {t.month}월'}
                metadata[period_id]=period;sources.setdefault(period_id,[]).extend(d.get('sourceFiles',[]))
                bucket=buckets.setdefault((period_id,rid),{'forecasts':{},'observations':{}})
                key=(row.get('issuedAt'),row['validAt'])
                prior=bucket[kind].get(key)
                fields=('temp','pop') if kind=='forecasts' else ('temp','rainMm')
                if prior and any(prior.get(k)!=row.get(k) for k in fields):raise ValueError('Conflicting historical values')
                bucket[kind].setdefault(key,row)
    previous={p['id']:p for p in read(dist/'history-index.json',{'periods':[]})['periods']}
    index={'schemaVersion':1,'periods':[]}
    for pid,period in sorted(metadata.items(),reverse=True):
        old=previous.pop(pid,{})
        if old and any(old[k]!=period[k] for k in ('start','end','days')):raise ValueError('Historical period boundaries changed')
        entry={'id':pid,**period,'files':dict(old.get('files',{})),'counts':dict(old.get('counts',{}))}
        for (period_id,rid),bucket in sorted(buckets.items()):
            if period_id!=pid:continue
            existing=read(dist/entry['files'][rid],{}) if rid in entry['files'] else {}
            for kind in ('forecasts','observations'):
                for prior in existing.get(kind,[]):
                    key=(prior.get('issuedAt'),prior['validAt']);current=bucket[kind].get(key)
                    fields=('temp','pop') if kind=='forecasts' else ('temp','rainMm')
                    if current and any(current.get(k)!=prior.get(k) for k in fields):raise ValueError('Conflict with previously published history')
                    bucket[kind][key]=prior
            fs=list(bucket['forecasts'].values());os=list(bucket['observations'].values())
            if not fs:continue
            obs={o['validAt']:o for o in os};pairs=[f for f in fs if f['validAt'] in obs]
            entry['counts'][rid]={'temperature':sum(obs[f['validAt']]['temp'] is not None for f in pairs),'rain':sum(obs[f['validAt']]['rainMm'] is not None for f in pairs),'maximum':int(period['days']*8)}
            file=f'history/{pid}/{rid}.json';entry['files'][rid]=file
            source_files={s['sha256']:s for s in existing.get('sourceFiles',[])+sources[pid]}
            write(dist/file,{'schemaVersion':1,'generatedAt':dt.datetime.now(KST).isoformat(timespec='seconds'),'source':'KMA historical CSV file sets','period':period,'sourceFiles':list(source_files.values()),'methodStatus':'experimental-unvalidated','forecasts':fs,'observations':os})
        index['periods'].append(entry)
    index['periods'].extend(previous.values());index['periods'].sort(key=lambda p:p['id'],reverse=True)
    write(dist/'history-index.json',index)
    return index

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',nargs='+',required=True);p.add_argument('--dist',type=Path,default=Path(__file__).resolve().parents[1]/'dist');args=p.parse_args();result=publish(args.input,args.dist);print('Published '+str(len(result['periods']))+' periods; files split by region.')
