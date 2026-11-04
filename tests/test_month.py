import datetime as dt,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"collector"))
import seoul_month as m
class MonthTests(unittest.TestCase):
    def tearDown(self):m.configure("2026-10")
    def test_calendar_and_rollover(self):
        for month,days in (("2026-03",31),("2026-04",30),("2026-05",31),("2026-06",30),("2026-07",31),("2026-08",31),("2026-02",28)):
            m.configure(month)
            rows=[r for d in range(1,m.DAYS+1) for r in m.requests_for_day(d)]
            self.assertEqual(len(rows),days*32)
            self.assertEqual(len({r[0] for r in rows}),days*8)
            self.assertTrue(all(v-i==dt.timedelta(hours=24) for v,i,*_ in rows))
            self.assertEqual(rows[0][0].strftime("%Y-%m"),month)
            self.assertNotEqual(rows[0][0].month,rows[0][1].month)
    def test_preserve_other_periods_and_reuse_cache(self):
        m.configure("2026-08")
        old=m.DIR
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m.DIR=root/"archive";dist=root/"dist"
            try:
                m.write(dist/"history-index.json",dict(schemaVersion=1,periods=[dict(id="2026-10-api",start="2026-10-01",files={"seoul":"existing"})]))
                with self.assertRaises(ValueError):m.build(dist)
                for day in range(1,m.DAYS+1):
                    responses={}
                    for valid,issued,kind,endpoint,params in m.requests_for_day(day):
                        responses[valid.strftime("%Y%m%d%H")+"-"+kind]=dict(value=18 if kind in ("TMP","T1H") else 0,sha256="a"*64,bytes=341297,endpoint=endpoint,parameters=params)
                    m.write(m.DIR/f"{day:02}.json",dict(complete=True,responses=responses,usage=dict(attempts=32,receivedBytes=32*341297,failedAttempts=0)))
                self.assertEqual(m.day_collect(1,"unused")[1]["usage"]["attempts"],32)
                self.assertEqual(m.build(dist)["responses"],992)
                self.assertEqual(len(m.read(dist/"history-index.json",{})["periods"]),2)
                d=m.read(dist/"history/2026-08-api/seoul.json",{})
                self.assertEqual(len(d["forecasts"]),248)
                self.assertEqual(d["period"]["end"],"2026-08-31T23:59:59+09:00")
            finally:m.DIR=old
if __name__=="__main__":unittest.main()
