from pathlib import Path
import openpyxl,json,re,hashlib,datetime
root=Path(__file__).resolve().parents[1];source=root/'archive/metadata/kma-grids-2026-09-30.xlsx'
rows=[r for r in list(openpyxl.load_workbook(source,read_only=True,data_only=True).active.values)[1:] if r[0]=='kor']
known={'서울특별시':'seoul','부산광역시':'busan','대구광역시':'daegu','인천광역시':'incheon','대전광역시':'daejeon','울산광역시':'ulsan','세종특별자치시':'sejong'}
regions=[];seen=set()
for r in rows:
 code,group,unit,dong=str(r[1]),r[2],r[3] or '',r[4] or ''
 if dong or group=='이어도':continue
 if group in known:
  if unit:continue
  name=group.replace('특별자치시','').replace('특별시','').replace('광역시','');rid=known[group];rep=group
 else:
  if not unit:continue
  city=re.match(r'^(.+?시)',unit)
  if city:name=city[1][:-1]
  elif unit.endswith('군'):name=unit
  elif group=='전남광주통합특별시' and unit=='동구':name='광주'
  else:continue
  rid='yeoju' if group=='경기도' and name=='여주' else 'gwangju' if name=='광주' and group=='전남광주통합특별시' else 'r'+code[:5]
  rep=unit
 key=(group,name)
 if key in seen:continue
 seen.add(key);nx,ny=int(r[5]),int(r[6]);dongs=[x[4] for x in rows if x[2]==group and x[4] and int(x[5])==nx and int(x[6])==ny and (not unit or x[3]==unit)]
 regions.append(dict(id=rid,name=name,group=group,nx=nx,ny=ny,administrativeCode=code,representative=rep,archiveDong=dongs[0] if dongs else None,source='KMA official grid workbook 2026-09-30',scope='representative-grid-not-city-average'))
# Stable existing selections and grid identities remain unchanged.
order={'yeoju':0,'seoul':1,'busan':2};regions.sort(key=lambda r:(order.get(r['id'],3),r['group'],r['name']))
meta={'schemaVersion':1,'sourceUrl':'https://data.kma.go.kr/community/board/detailBoard.do?bbrdTypeNo=4&bbrdNo=70342&pgmNo=92','sourceFile':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'policy':'One representative grid per city/county; metropolitan districts and townships are omitted. For subdivided cities, first official district row is the representative. No citywide average claim.','regions':regions}
(root/'dist/regions.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n');(root/'dist/regions.mjs').write_text('export const REGIONS='+json.dumps(regions,ensure_ascii=False,separators=(',',':'))+';\n')
print('Regions',len(regions),'unique grids',len(set((r['nx'],r['ny']) for r in regions)))
print([(r['name'],r['nx'],r['ny']) for r in regions[:12]])
