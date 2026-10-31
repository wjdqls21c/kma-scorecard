"""Import official KMA forecast/observation CSV or ZIP files. No network or keys.
CSV times are UTC. Only exact 24-hour lead forecasts enter the score dataset.
Example: python collector/import_archives.py --forecast fcst.zip --observed obs.zip --output imported.json
"""
import argparse
import csv
import datetime as dt
import hashlib
from pathlib import Path
import re
import zipfile
from collect import KST,numeric,stamp,write
UTC=dt.timezone.utc
GRIDS={(71,121):'yeoju',(60,127):'seoul',(98,76):'busan'}

def decode(raw):
    for encoding in ('utf-8-sig','cp949'):
        try:return raw.decode(encoding)
        except UnicodeDecodeError:pass
    raise ValueError('CSV encoding must be UTF-8 or CP949')

def kind_for(name,group):
    if group=='forecast':
        if '1시간기온' in name:return 'TMP'
        if '강수확률' in name:return 'POP'
    else:
        if '기온' in name:return 'T1H'
        if ('강수량' in name or '강수' in name) and '형태' not in name and '확률' not in name:return 'RN1'
    return None

def parse_csv(raw,kind):
    text=decode(raw);lines=text.splitlines()
    if not lines:raise ValueError('Empty CSV')
    header=lines[0]
    grid=re.search(r'location\s*:\s*(\d+)\s*_\s*(\d+)',header,re.I)
    start=re.search(r'Start\s*:\s*(\d{8})',header,re.I)
    if not grid or not start:raise ValueError('Missing KMA location/Start header')
    nx,ny=map(int,grid.groups())
    if (nx,ny) not in GRIDS:raise ValueError('CSV grid is outside the configured study locations')
    first=dt.datetime.strptime(start.group(1),'%Y%m%d');year,month=first.year,first.month;previous=None;out=[]
    forecast=kind in ('TMP','POP')
    for cells in csv.reader(lines[1:]):
        if not cells or not any(c.strip() for c in cells):continue
        cells=[c.strip() for c in cells]
        if len(cells)==1 and re.fullmatch(r'Start\s*:\s*\d{8}',cells[0],re.I):
            segment=dt.datetime.strptime(cells[0].split(':')[1].strip(),'%Y%m%d')
            year,month,previous=segment.year,segment.month,None
            continue
        expected=4 if forecast else 3
        if len(cells) not in (expected,expected+2):raise ValueError('Unexpected CSV columns')
        day=int(cells[0]);clock=cells[1].zfill(4)
        if len(clock)!=4 or not clock.isdigit():raise ValueError('Invalid clock')
        if previous is not None and day<previous:
            month+=1
            if month==13:year+=1;month=1
        previous=day
        hour,minute=int(clock[:2]),int(clock[2:])
        if not 0<=hour<=23 or not 0<=minute<60:raise ValueError('Invalid UTC time')
        moment=dt.datetime(year,month,day,hour,minute,tzinfo=UTC)
        if len(cells)==expected+2:
            local=moment.astimezone(KST)
            # Official exports sometimes print day+1 as 31/32 at month end.
            # Build the calendar date from UTC, and verify this unrolled day too.
            if int(cells[-2]) not in (local.day,day+(hour>=15)) or cells[-1].zfill(4)!=local.strftime('%H%M'):
                raise ValueError('UTC and KST source columns disagree')
        if minute!=0:continue
        if forecast:
            lead=int(cells[2])
            if lead!=24:continue
            issued=moment;valid=moment+dt.timedelta(hours=lead)
            if issued.astimezone(KST).hour not in (2,5,8,11,14,17,20,23):raise ValueError('Unexpected issue hour after UTC conversion')
            value=numeric(cells[3],0,100) if kind=='POP' else numeric(cells[3],-90,65)
            if value is None:continue
            out.append((GRIDS[(nx,ny)],stamp(issued),stamp(valid),value))
        else:
            value=numeric(cells[2],0,1000) if kind=='RN1' else numeric(cells[2],-90,65)
            # Invalid values are omitted, never converted into zero rain.
            if value is None:continue
            out.append((GRIDS[(nx,ny)],stamp(moment),value))
    return out

def files(path):
    p=Path(path)
    if p.suffix.lower()=='.csv':yield p.name,p.read_bytes();return
    if p.suffix.lower()!='.zip':raise ValueError('Expected CSV or ZIP')
    with zipfile.ZipFile(p) as z:
        members=[m for m in z.infolist() if m.filename.lower().endswith('.csv')]
        if len(members)>500:raise ValueError('Too many CSV files')
        for member in members:
            if member.file_size>32000000:raise ValueError('CSV is larger than the 32MB safety limit')
            name=member.filename
            if not member.flag_bits&0x800:
                try:name=name.encode('cp437').decode('cp949')
                except (UnicodeError,LookupError):pass
            yield name,z.read(member)

def insert(values,key,value):
    if key in values and values[key]!=value:raise ValueError('Conflicting duplicate source rows')
    values[key]=value

def build(forecast_files,observation_files):
    columns={k:{} for k in ('TMP','POP','T1H','RN1')};sources=[]
    for group,paths in (('forecast',forecast_files),('observation',observation_files)):
        for path in paths:
            for name,raw in files(path):
                kind=kind_for(name,group)
                if not kind:continue
                rows=parse_csv(raw,kind)
                sources.append({'file':name,'category':kind,'sha256':hashlib.sha256(raw).hexdigest(),'usableRows':len(rows)})
                for row in rows:insert(columns[kind],tuple(row[:-1]),row[-1])
    now=stamp(dt.datetime.now(KST));forecasts=[]
    for key,temp in columns['TMP'].items():
        if key not in columns['POP']:continue
        region,issued,valid=key
        forecasts.append({'region':region,'issuedAt':issued,'validAt':valid,'temp':temp,'pop':columns['POP'][key],'retrievedAt':now,'retrievalMode':'retrospective-file'})
    observations=[]
    targets={(f['region'],f['validAt']) for f in forecasts}
    for key in sorted(targets):
        temp=columns['T1H'].get(key);rain=columns['RN1'].get(key)
        if temp is None and rain is None:continue
        observations.append({'region':key[0],'validAt':key[1],'temp':temp,'rainMm':rain,'retrievedAt':now,'retrievalMode':'retrospective-file'})
    if not forecasts or not observations:raise ValueError('No matched forecast/observation sources; check grid, categories and periods')
    return {'schemaVersion':1,'generatedAt':now,'source':'KMA historical CSV file sets','methodStatus':'experimental-unvalidated','sourceFiles':sources,'forecasts':sorted(forecasts,key=lambda f:(f['region'],f['validAt'])),'observations':observations}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forecast',nargs='+',required=True);parser.add_argument('--observed',nargs='+',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();data=build(args.forecast,args.observed);write(Path(args.output),data)
    print(str(len(data['forecasts']))+' archived forecasts and '+str(len(data['observations']))+' matched observations imported; method verification remains required.')
if __name__=='__main__':main()
