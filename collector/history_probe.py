"""Test historical availability without exposing credentials or publishing scores."""
import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from collect import BASE,KST,stamp

def get(endpoint,params,key):
    q={**params,'serviceKey':urllib.parse.unquote(key),'dataType':'JSON','numOfRows':1000,'pageNo':1}
    try:
        req=urllib.request.Request(BASE+endpoint+'?'+urllib.parse.urlencode(q),headers={'User-Agent':'KMA-scorecard/0.1'})
        with urllib.request.urlopen(req,timeout=12) as response:body=json.load(response)['response']
        code=str(body.get('header',{}).get('resultCode',''))
        if code!='00':return {'status':'api-code-'+(code if code.isdigit() else 'unknown'),'rows':[]}
        content=body['body'];items=content.get('items',{})
        rows=items.get('item',[]) if isinstance(items,dict) else []
        if isinstance(rows,dict):rows=[rows]
        return {'status':'available','rows':rows,'totalCount':int(content.get('totalCount',0))}
    except urllib.error.HTTPError as error:return {'status':'http-'+str(error.code),'rows':[]}
    except Exception as error:return {'status':'transport-or-parse-'+type(error).__name__,'rows':[]}

def main():
    key=os.environ.get('KMA_SERVICE_KEY','').strip()
    if not key:print('Missing KMA_SERVICE_KEY');return 1
    now=dt.datetime.now(KST);results=[]
    for age in (1,2,7,30):
        base=(now-dt.timedelta(days=age)).replace(hour=5,minute=0,second=0,microsecond=0)
        valid=base+dt.timedelta(hours=24)
        common={'nx':71,'ny':121}
        forecast=get('getVilageFcst',{**common,'base_date':base.strftime('%Y%m%d'),'base_time':'0500'},key)
        observation=get('getUltraSrtNcst',{**common,'base_date':valid.strftime('%Y%m%d'),'base_time':'0500'},key)
        fs={}
        for row in forecast['rows']:
            if (str(row.get('baseDate'))==base.strftime('%Y%m%d') and str(row.get('baseTime')).zfill(4)=='0500' and str(row.get('fcstDate'))==valid.strftime('%Y%m%d') and str(row.get('fcstTime')).zfill(4)=='0500' and int(row.get('nx',-1))==71 and int(row.get('ny',-1))==121):
                if row.get('category') in ('TMP','POP'):fs[row['category']]=row['fcstValue']
        obs={}
        for row in observation['rows']:
            if str(row.get('baseDate'))==valid.strftime('%Y%m%d') and str(row.get('baseTime')).zfill(4)=='0500' and int(row.get('nx',-1))==71 and int(row.get('ny',-1))==121:
                if row.get('category') in ('T1H','RN1'):obs[row['category']]=row['obsrValue']
        result={'daysBefore':age,'issuedAt':stamp(base),'validAt':stamp(valid),'region':'yeoju','nx':71,'ny':121,'retrievedAt':stamp(now),'forecastStatus':forecast['status'],'observationStatus':observation['status'],'forecastRows':len(forecast['rows']),'forecastTotal':forecast.get('totalCount',0),'forecast24h':fs,'observation':obs,'note':'Availability test only; not merged into performance scores.'}
        results.append(result)
        print('History '+str(age)+' days: forecast='+forecast['status']+'; observation='+observation['status']+'; 24h variables='+str(len(fs)))
    print('HISTORY_RESULT: '+json.dumps({'schemaVersion':1,'generatedAt':stamp(now),'source':BASE,'tests':results},ensure_ascii=False))
    return 0
if __name__=='__main__':raise SystemExit(main())
