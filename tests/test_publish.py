import importlib.util,sys,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'collector'))
spec=importlib.util.spec_from_file_location('publish',ROOT/'collector/publish_history.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class PublishTests(unittest.TestCase):
 def test_existing_history_split_without_losing_240_pairs(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d);index=p.publish([ROOT/'dist/history-2026-09.json'],out);period=index['periods'][0]
   self.assertEqual(set(period['files']),{'seoul','busan','yeoju'})
   self.assertNotIn('daegu',period['files'])
   for rid in period['files']:
    self.assertEqual(period['counts'][rid],{'temperature':240,'rain':240,'maximum':240})
    data=json.loads((out/period['files'][rid]).read_text());self.assertEqual({f['region'] for f in data['forecasts']},{rid})
 def test_calendar_month_split_and_missing_rain(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);source={'schemaVersion':1,'forecasts':[],'observations':[]}
   for month in ['01','02']:
    valid=f'2026-{month}-15T08:00:00+09:00';source['forecasts'].append({'region':'seoul','issuedAt':f'2026-{month}-14T08:00:00+09:00','validAt':valid,'temp':10,'pop':0});source['observations'].append({'region':'seoul','validAt':valid,'temp':9,'rainMm':None})
   path=folder/'input.json';path.write_text(json.dumps(source));index=p.publish([path],folder/'out');self.assertEqual(len(index['periods']),2)
   periods={r['id']:r for r in index['periods']};self.assertEqual(periods['2026-01']['counts']['seoul'],{'temperature':1,'rain':0,'maximum':248});self.assertEqual(periods['2026-02']['days'],28)
 def test_incremental_import_keeps_prior_periods_and_regions(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);out=folder/'out';p.publish([ROOT/'dist/history-2026-09.json'],out)
   source={'schemaVersion':1,'forecasts':[{'region':'seoul','issuedAt':'2026-08-14T08:00:00+09:00','validAt':'2026-08-15T08:00:00+09:00','temp':10,'pop':0}],'observations':[{'region':'seoul','validAt':'2026-08-15T08:00:00+09:00','temp':9,'rainMm':None}]}
   file=folder/'more.json';file.write_text(json.dumps(source));index=p.publish([file],out);self.assertEqual(len(index['periods']),2);old=next(r for r in index['periods'] if r['id']=='2026-09-window');self.assertEqual(old['counts']['busan']['temperature'],240)
if __name__=='__main__':unittest.main()
