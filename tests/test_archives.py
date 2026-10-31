import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'collector'))
spec=importlib.util.spec_from_file_location('archives',ROOT/'collector/import_archives.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class ArchiveTests(unittest.TestCase):
    def test_downloaded_format_kst_columns(self):
        raw=b'format: day(UTC),hour(UTC),forecast,value,day(KST),hour(KST) location:71_121 Start:20260831\n31,2000,+24,10,1,0500\n1,0200,+24,11,1,1100\n'
        rows=a.parse_csv(raw,'TMP');self.assertEqual(rows[0][1],'2026-09-01T05:00:00+09:00');self.assertEqual(rows[1][2],'2026-09-02T11:00:00+09:00')
        with self.assertRaises(ValueError):a.parse_csv(raw.replace(b'1,0500',b'31,0500'),'TMP')
        self.assertEqual(a.parse_csv(raw.replace(b'1,0500',b'32,0500'),'TMP')[0],rows[0])
    def test_empty_download_not_observation(self):
        with self.assertRaises(ValueError):a.parse_csv(b'format: day(UTC),hour(UTC),value,day(KST),hour(KST) location:60_127\n','T1H')
    def test_daily_segment_resets_month(self):
        raw=b'format: location:71_121 Start:20260831\n31,2000,+24,10\n Start : 20260901\n1,2000,+24,11\n'
        self.assertEqual(a.parse_csv(raw,'TMP')[1][1],'2026-09-02T05:00:00+09:00')
    def test_published_history_reproduces_official_csv(self):
        folder=ROOT/'archive/history/2026-09'
        rebuilt=a.build([folder/'forecasts.zip'],[folder/'observations.zip'])
        published=json.loads((ROOT/'dist/history-2026-09.json').read_text())
        end=published['period']['end']
        self.assertEqual(rebuilt['sourceFiles'],published['sourceFiles'])
        for kind,fields in [('forecasts',('region','issuedAt','validAt','temp','pop')),('observations',('region','validAt','temp','rainMm'))]:
            rows=lambda data:sorted(tuple(r[k] for k in fields) for r in data[kind] if r['validAt']<=end)
            self.assertEqual(rows(rebuilt),rows(published))
    def test_utc_and_24hour_lead(self):
        raw=b'format: day,hour,forecast,value location:71_121 Start : 20261031\n31,2000,+24,5\n31,2000,+23,7\n'
        rows=a.parse_csv(raw,'TMP');self.assertEqual(len(rows),1);self.assertEqual(rows[0][1],'2026-11-01T05:00:00+09:00');self.assertEqual(rows[0][2],'2026-11-02T05:00:00+09:00')
    def test_missing_rain_is_not_dry(self):
        raw=b'format: day,hour,value location:71_121 Start:20261001\n1,2000,-999\n2,2000,0\n'
        rows=a.parse_csv(raw,'RN1');self.assertEqual(len(rows),1);self.assertEqual(rows[0][-1],0)
    def test_wrong_grid_and_conflicts_rejected(self):
        with self.assertRaises(ValueError):a.parse_csv(b'format: location:1_2 Start:20261001\n1,2000,2','T1H')
        values={};a.insert(values,('r','t'),1)
        with self.assertRaises(ValueError):a.insert(values,('r','t'),2)
    def test_documented_format_join(self):
        with tempfile.TemporaryDirectory() as folder:
            paths={}
            for name,header,line in [('1시간기온','day,hour,forecast,value','1,2000,+24,10'),('강수확률','day,hour,forecast,value','1,2000,+24,60'),('기온','day,hour,value','2,2000,8'),('강수량','day,hour,value','2,2000,1')]:
                p=Path(folder)/(name+'.csv');p.write_text('format: '+header+' location:71_121 Start:20261001\n'+line+'\n');paths[name]=str(p)
            data=a.build([paths['1시간기온'],paths['강수확률']],[paths['기온'],paths['강수량']]);self.assertEqual(len(data['observations']),1);self.assertEqual(data['forecasts'][0]['pop'],60);self.assertEqual(data['observations'][0]['rainMm'],1);self.assertEqual(len(data['sourceFiles']),4)
if __name__=='__main__':unittest.main()
