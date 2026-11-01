import importlib.util
from pathlib import Path
import tempfile,unittest,datetime as dt
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('storage',ROOT/'collector/collect.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class StorageTests(unittest.TestCase):
 def test_daily_forecast_immutable_and_missing_observation_filled(self):
  f={'region':'yeoju','issuedAt':'2026-10-30T08:00:00+09:00','validAt':'2026-10-31T08:00:00+09:00','temp':10,'pop':30}
  o={'region':'yeoju','validAt':f['validAt'],'temp':None,'rainMm':0}
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);c.save_daily(p,[f],[o]);c.save_daily(p,[{**f,'temp':99}],[{**o,'temp':11,'rainMm':9}]);saved=c.read(p/'daily/2026-10-31.json',{})
   self.assertEqual(saved['forecasts'][0]['temp'],10);self.assertEqual(saved['observations'][0]['temp'],11);self.assertEqual(saved['observations'][0]['rainMm'],0)
 def test_compact_export_retains_old_24h_and_latest_two_versions(self):
  now=dt.datetime(2026,11,1,12,tzinfo=c.KST);fs=[]
  for back in [1,4,7,10]:
   issue=now-dt.timedelta(hours=back);valid=issue+dt.timedelta(hours=30)
   fs.append({'region':'seoul','issuedAt':c.stamp(issue),'validAt':c.stamp(valid),'temp':10,'pop':0})
  older={'region':'seoul','issuedAt':'2026-10-10T08:00:00+09:00','validAt':'2026-10-11T08:00:00+09:00','temp':10,'pop':0};fs.append(older)
  visible,_=c.compact_export(fs,[],now);self.assertEqual(len(visible),3);self.assertIn(older,visible)
 def test_retrospective_parser_requires_original_issue_and_exact_lead(self):
  base=dt.datetime(2026,10,31,8,tzinfo=c.KST);now=base+dt.timedelta(hours=26)
  items=[dict(nx=71,ny=121,baseDate='20261031',baseTime='0800',fcstDate='20261101',fcstTime='0800',category=k,fcstValue=v) for k,v in [('TMP',5),('POP',30)]]
  rows=c.parse_forecast(items,'yeoju',base,now,71,121,retrospective=True)
  self.assertEqual(rows[0]['retrievalMode'],'retrospective-api')
  with self.assertRaises(ValueError):c.parse_forecast(items,'yeoju',base-dt.timedelta(hours=3),now,71,121,retrospective=True)
 def test_current_observation_waits_for_publication_margin(self):
  early=dt.datetime(2026,11,1,14,30,tzinfo=c.KST);late=early.replace(minute=50)
  self.assertEqual([t.hour for t in c.observation_slots(early)],[11,8])
  self.assertEqual([t.hour for t in c.observation_slots(late)],[14,11,8])
if __name__=='__main__':unittest.main()

